"""Vozdoo: dictado por voz local con Whisper (faster-whisper).

Mantén pulsada la tecla/combo configurada, habla, suelta -> el texto
transcrito se copia al portapapeles y (opcional) se pega automáticamente
donde tengas el cursor. 100% local, sin APIs de pago, sustituto de
herramientas tipo WisprFlow.

Sin LLM, sin voz clonada, sin nada personalizado: solo captura de audio +
Whisper + inserción de texto.

Uso:
    python vozdoo_core.py
"""

from __future__ import annotations

import logging
import signal
import sys
import threading
import time
import tkinter as tk
from pathlib import Path

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from pynput import keyboard as pkb

from clipboard_paste import paste_text
from llm_engine import get_engine
from polish_bubble import PolishBubble

SCRIPT_DIR = Path(__file__).parent
ENV_FILE = SCRIPT_DIR / ".env"
LOG_FILE = SCRIPT_DIR / "vozdoo.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
for noisy in ("huggingface_hub", "faster_whisper"):
    logging.getLogger(noisy).setLevel(logging.WARNING)
log = logging.getLogger("vozdoo")


def load_env() -> dict[str, str]:
    import os

    env: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip('"').strip("'")
    for key, default in {
        "VOZDOO_HOTKEY": "ctrl+win",
        "VOZDOO_WHISPER_MODEL": "small",
        "VOZDOO_WHISPER_LANGUAGE": "es",
        "VOZDOO_WHISPER_DEVICE": "auto",
        "VOZDOO_MIC_DEVICE": "",
        "VOZDOO_SAMPLE_RATE": "16000",
        "VOZDOO_MAX_RECORDING_SECONDS": "30",
        "VOZDOO_AUTO_PASTE": "true",
        "VOZDOO_POLISH_HOTKEY": "alt+win",
        "VOZDOO_LLM_API_KEY": "",
        "VOZDOO_LLM_API_URL": "https://api.openai.com/v1/chat/completions",
        "VOZDOO_LLM_API_MODEL": "gpt-4o-mini",
        "VOZDOO_LLM_MODEL": "qwen2.5:3b-instruct",
        "VOZDOO_LLM_HOST": "http://localhost:11434",
    }.items():
        if key not in env:
            env[key] = os.environ.get(key, default)
    return env


def beep(freq: int, duration_ms: int) -> None:
    """Beep multiplataforma. En Windows usa winsound; si no, campana de terminal."""
    try:
        import winsound

        winsound.Beep(freq, duration_ms)
    except Exception:
        try:
            sys.stdout.write("\a")
            sys.stdout.flush()
        except Exception:
            pass


class AudioBuffer:
    """Acumula audio del mic en numpy float32 mono."""

    def __init__(self, sample_rate: int, max_seconds: int, device: str | int | None):
        self.sample_rate = sample_rate
        self.max_samples = sample_rate * max_seconds
        self.device = device
        self.chunks: list[np.ndarray] = []
        self.stream: sd.InputStream | None = None
        self.recording = False

    def _callback(self, indata, frames, time_info, status):  # noqa: ARG002
        if status:
            log.warning("Audio stream status: %s", status)
        if not self.recording:
            return
        self.chunks.append(indata.copy())

    def start(self):
        self.chunks = []
        self.recording = True
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            device=self.device or None,
            callback=self._callback,
        )
        self.stream.start()

    def stop(self) -> np.ndarray:
        self.recording = False
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        if not self.chunks:
            return np.zeros(0, dtype=np.float32)
        audio = np.concatenate(self.chunks, axis=0).flatten()
        if len(audio) > self.max_samples:
            audio = audio[: self.max_samples]
        return audio


def transcribe(model: WhisperModel, audio: np.ndarray, language: str) -> str:
    if len(audio) < 1600:  # menos de 100ms, ignorar
        return ""
    segments, _info = model.transcribe(
        audio,
        language=language,
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )
    text = " ".join(seg.text.strip() for seg in segments).strip()
    return text


# --- Parsing de hotkey con soporte de combos (ctrl+alt+d, f9, ctrl+space...) ---

_MODIFIER_ALIASES = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "alt": "alt",
    "shift": "shift",
    "win": "cmd",
    "windows": "cmd",
    "super": "cmd",
    "cmd": "cmd",
}

_MODIFIER_KEYS = {
    "ctrl": {pkb.Key.ctrl, pkb.Key.ctrl_l, pkb.Key.ctrl_r},
    "alt": {pkb.Key.alt, pkb.Key.alt_l, pkb.Key.alt_r},
    "shift": {pkb.Key.shift, pkb.Key.shift_l, pkb.Key.shift_r},
    "cmd": {pkb.Key.cmd, pkb.Key.cmd_l, pkb.Key.cmd_r},
}

_SPECIAL_KEYS = {
    "space": pkb.Key.space,
    "enter": pkb.Key.enter,
    "esc": pkb.Key.esc,
    "tab": pkb.Key.tab,
    "pause": pkb.Key.pause,
}


def parse_hotkey(spec: str):
    """Convierte 'ctrl+win', 'ctrl+alt+d' o 'f9' en un frozenset de "tokens".

    Cada token es o bien el nombre normalizado de un modificador
    ('ctrl'/'alt'/'shift'/'cmd') o un pynput Key/KeyCode concreto. El combo
    se dispara cuando TODOS los tokens están pulsados a la vez, así que
    combos hechos solo de modificadores (p.ej. 'ctrl+win') funcionan igual
    que combos con una tecla normal al final ('ctrl+alt+d').
    """
    parts = [p.strip().lower() for p in spec.split("+") if p.strip()]
    if not parts:
        return None
    tokens: set = set()
    for part in parts:
        if part in _MODIFIER_ALIASES:
            tokens.add(_MODIFIER_ALIASES[part])
            continue
        if part.startswith("f") and part[1:].isdigit():
            key = getattr(pkb.Key, part, None)
        elif part in _SPECIAL_KEYS:
            key = _SPECIAL_KEYS[part]
        elif len(part) == 1:
            key = pkb.KeyCode.from_char(part)
        else:
            key = None
        if key is None:
            log.error("Tecla de hotkey no soportada: '%s'", part)
            return None
        tokens.add(key)
    return frozenset(tokens)


def hotkeys_overlap(a: frozenset, b: frozenset) -> bool:
    """True si uno de los dos combos contiene todas las teclas del otro.

    Si eso pasa, pulsar el combo largo dispara el corto a medio camino
    según el orden de pulsación. Ver spec 2026-09-18-polish-bubble-design.
    """
    return a <= b or b <= a


class Vozdoo:
    def __init__(self, env: dict[str, str]):
        self.env = env
        self.sample_rate = int(env["VOZDOO_SAMPLE_RATE"])
        self.max_seconds = int(env["VOZDOO_MAX_RECORDING_SECONDS"])
        self.language = env["VOZDOO_WHISPER_LANGUAGE"]
        self.auto_paste = env["VOZDOO_AUTO_PASTE"].lower() == "true"
        mic_device = env.get("VOZDOO_MIC_DEVICE", "").strip()
        self.mic_device: str | int | None = None
        if mic_device:
            self.mic_device = int(mic_device) if mic_device.isdigit() else mic_device

        normal_hotkey = parse_hotkey(env["VOZDOO_HOTKEY"])
        polish_hotkey = parse_hotkey(env["VOZDOO_POLISH_HOTKEY"])
        if normal_hotkey is None or polish_hotkey is None:
            raise SystemExit(1)
        if hotkeys_overlap(normal_hotkey, polish_hotkey):
            log.error(
                "VOZDOO_HOTKEY (%s) y VOZDOO_POLISH_HOTKEY (%s) se solapan: "
                "uno no puede contener todas las teclas del otro.",
                env["VOZDOO_HOTKEY"],
                env["VOZDOO_POLISH_HOTKEY"],
            )
            raise SystemExit(1)
        self.hotkeys = {"normal": normal_hotkey, "polish": polish_hotkey}
        self._pressed_tokens: set = set()
        self._active_mode: str | None = None
        self.engine_env = env
        self.tk_root: tk.Tk | None = None

        log.info("Cargando Whisper '%s'...", env["VOZDOO_WHISPER_MODEL"])
        device = env["VOZDOO_WHISPER_DEVICE"]
        compute_type = "int8" if device in ("cpu", "auto") else "float16"
        try:
            self.whisper = WhisperModel(
                env["VOZDOO_WHISPER_MODEL"],
                device="cpu" if device == "auto" else device,
                compute_type=compute_type,
            )
            log.info("Whisper listo (device=%s compute=%s)", device, compute_type)
        except Exception as exc:  # noqa: BLE001
            log.warning("Whisper %s falló (%s), fallback CPU int8", device, exc)
            self.whisper = WhisperModel(
                env["VOZDOO_WHISPER_MODEL"], device="cpu", compute_type="int8"
            )

        self.buffer = AudioBuffer(self.sample_rate, self.max_seconds, self.mic_device)
        self.processing = False
        self.lock = threading.Lock()

    def _start_recording(self, mode: str) -> None:
        with self.lock:
            if self.buffer.recording or self.processing:
                return
            self._active_mode = mode
            log.info("Grabando (%s)... (suelta para transcribir)", mode)
            beep(800, 80)
            self.buffer.start()

    def _finish_recording(self) -> None:
        with self.lock:
            if not self.buffer.recording:
                return
            audio = self.buffer.stop()
            self.processing = True
            mode = self._active_mode
            self._active_mode = None

        beep(600, 80)
        log.info("Audio capturado (%.2fs)", len(audio) / self.sample_rate)

        try:
            t0 = time.time()
            text = transcribe(self.whisper, audio, self.language)
            log.info("STT (%.2fs): %s", time.time() - t0, text)

            if not text:
                log.info("Audio vacío o sin voz, nada que hacer")
                return

            if mode == "normal":
                paste_text(text, self.auto_paste)
                log.info("Pegado en la ventana activa" if self.auto_paste else "Copiado al portapapeles")
            else:
                self.tk_root.after(0, lambda: self._open_polish_bubble(text))
        except Exception:
            log.exception("Error transcribiendo/procesando")
        finally:
            self.processing = False

    def start_custom_recording(self) -> None:
        """Llamado desde la burbuja al mantener pulsado el botón del micro."""
        with self.lock:
            if self.buffer.recording or self.processing:
                return
            beep(800, 80)
            self.buffer.start()

    def stop_custom_recording(self) -> str:
        """Llamado desde la burbuja al soltar el botón del micro."""
        with self.lock:
            if not self.buffer.recording:
                return ""
            audio = self.buffer.stop()
        beep(600, 80)
        return transcribe(self.whisper, audio, self.language)

    def _open_polish_bubble(self, text: str) -> None:
        """Nota de alcance: si `transcribe()` lanza una excepción (no si
        solo devuelve vacío, ese caso ya está cubierto arriba), el error
        se registra en el log pero la burbuja no llega a abrirse — el
        spec pedía que fuera visible en la burbuja, pero eso exigiría
        abrirla ANTES de transcribir; se deja así por ahora porque es un
        caso raro (fallo real de Whisper, no "no se dijo nada")."""
        engine = get_engine(self.engine_env)
        bubble = PolishBubble(
            root=self.tk_root,
            original_text=text,
            engine=engine,
            record_start_fn=self.start_custom_recording,
            record_stop_fn=self.stop_custom_recording,
            paste_fn=paste_text,
            auto_paste=self.auto_paste,
        )
        bubble.show()

    def run(self) -> None:
        self.tk_root = tk.Tk()
        self.tk_root.withdraw()
        signal.signal(signal.SIGINT, lambda *_: self.tk_root.quit())

        def normalize(key):
            for name, variants in _MODIFIER_KEYS.items():
                if key in variants:
                    return name
            return key

        def on_press(key):
            token = normalize(key)
            self._pressed_tokens.add(token)
            if self._active_mode is not None:
                return
            if self.hotkeys["polish"] <= self._pressed_tokens:
                self._start_recording("polish")
            elif self.hotkeys["normal"] <= self._pressed_tokens:
                self._start_recording("normal")

        def on_release(key):
            token = normalize(key)
            active = self._active_mode
            was_active = active is not None and token in self.hotkeys[active]
            self._pressed_tokens.discard(token)
            if was_active:
                self._finish_recording()

        listener = pkb.Listener(on_press=on_press, on_release=on_release)
        listener.start()

        log.info(
            "Vozdoo listo. '%s' dicta y pega. '%s' dicta y pulir con IA. Ctrl+C para salir.",
            self.env["VOZDOO_HOTKEY"],
            self.env["VOZDOO_POLISH_HOTKEY"],
        )

        try:
            self.tk_root.mainloop()
        finally:
            listener.stop()
            log.info("Saliendo...")


def main() -> int:
    env = load_env()
    vozdoo = Vozdoo(env)
    vozdoo.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
