"""Pega el orbe con el nucleo: microfono, Whisper, motor de IA y pegado.

El orbe solo emite señales ("he empezado a hablar", "he elegido esta
accion"); aqui se decide que hacer con ellas. Todo lo que tarda —
transcribir y llamar al modelo — corre en un hilo aparte para que el
orbe siga animandose."""

from __future__ import annotations

import logging
import sys
import threading
import time

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication

import pyperclip

import ollama_setup
from action_bubbles import ActionBubbles
from clipboard_paste import paste_text
from llm_engine import OllamaEngine, get_engine
from ollama_panel import OllamaPanel
from orb_widget import OrbWidget
from polish_actions import ACTIONS, ACTIONS_BY_LABEL, MENU_ACTIONS, free_action
from result_panel import ResultPanel
from voice_commands import parse_command
from x11_focus import FocusKeeper

log = logging.getLogger("vozdoo")

PASTE_DELAY_MS = 180   # que el foco vuelva a la ventana de trabajo antes de pegar


def _close_safely(widget) -> None:
    """Cierra un widget de Qt que puede estar ya destruido."""
    if widget is None:
        return
    try:
        widget.close()
    except RuntimeError:
        pass


class Bridge(QObject):
    """Puente entre los hilos de trabajo y el hilo de la interfaz: Qt solo
    deja tocar widgets desde el principal."""

    transcribed = pyqtSignal(str, str)   # texto, error
    polished = pyqtSignal(str, str)      # texto, error
    install_status = pyqtSignal(str)     # paso de la instalacion de Ollama
    install_fraction = pyqtSignal(float)
    install_done = pyqtSignal(str)
    hotkey_start = pyqtSignal()          # emitidas desde el hilo del listener
    hotkey_stop = pyqtSignal()
    dictated = pyqtSignal(str)           # dictado por la tecla normal


class OrbApp:
    def __init__(self, core) -> None:
        self.core = core
        self.app = QApplication.instance() or QApplication([])
        self.app.setQuitOnLastWindowClosed(False)

        self.orb = OrbWidget()
        self.bridge = Bridge()
        self.pending_text = ""
        self.bubbles: ActionBubbles | None = None
        self.panel: ResultPanel | None = None
        self.ollama_panel: OllamaPanel | None = None
        self.polish_serial = 0        # para descartar respuestas canceladas
        self.assistant_listening = False   # la grabacion en curso es una orden

        self.level_timer = QTimer()
        self.level_timer.setInterval(50)
        self.level_timer.timeout.connect(self._poll_level)

        # Vigila en segundo plano cual es la ventana donde el usuario esta
        # escribiendo, para devolverle el foco antes de pegar.
        self.focus = FocusKeeper()
        self.focus_timer = QTimer()
        self.focus_timer.setInterval(400)
        self.focus_timer.timeout.connect(self._remember_focus)
        self.focus_timer.start()

        self.orb.dictation_started.connect(self._on_start)
        self.orb.dictation_stopped.connect(self._on_stop)
        self.orb.dictation_cancelled.connect(self._on_cancel)
        self.orb.menu_requested.connect(self._on_menu)
        self.orb.quit_requested.connect(self.quit)
        self.bridge.transcribed.connect(self._on_transcribed)
        self.bridge.polished.connect(self._on_polished)
        self.bridge.hotkey_start.connect(self.start_dictation_from_hotkey)
        self.bridge.hotkey_stop.connect(self.stop_dictation_from_hotkey)
        self.bridge.dictated.connect(self._on_dictated)
        self.bridge.install_status.connect(self._on_install_status)
        self.bridge.install_fraction.connect(self._on_install_fraction)
        self.bridge.install_done.connect(self._on_install_done)

        self._log_engine()

    def _log_engine(self) -> None:
        """Decir al arrancar si la IA esta lista evita la duda de "¿esto
        tiene Ollama o no?" cuando una accion no responde."""
        engine = get_engine(self.core.engine_env)
        model = getattr(engine, "model", "?")
        kind = "Ollama local" if hasattr(engine, "host") else "API propia"
        try:
            available = engine.is_available()
        except Exception:
            available = False
        if available:
            log.info("IA lista: %s, modelo %s", kind, model)
            if hasattr(engine, "warm_up"):
                threading.Thread(target=self._warm_up, args=(engine,), daemon=True).start()
        else:
            log.warning(
                "IA no disponible (%s, modelo %s). Las acciones de pulido "
                "fallaran hasta que arranque.", kind, model
            )

    def _warm_up(self, engine) -> None:
        try:
            engine.warm_up()
            log.info("Modelo cargado en memoria: la primera orden ya va rápida")
        except Exception:  # noqa: BLE001
            log.debug("No se pudo precargar el modelo", exc_info=True)

    # ------------------------------------------------------------------
    # Dictado
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        self.core.start_custom_recording()
        self.level_timer.start()

    def _remember_focus(self) -> None:
        own = {int(self.orb.winId())}
        for widget in (self.bubbles, self.panel):
            try:
                if widget is not None:
                    own.add(int(widget.winId()))
            except RuntimeError:
                pass
        self.focus.remember(own)

    def _poll_level(self) -> None:
        self.orb.set_level(self.core.mic_level())

    def _on_cancel(self) -> None:
        self.assistant_listening = False
        self.level_timer.stop()
        self.orb.set_level(0.0)
        self.core.cancel_custom_recording()

    def _on_stop(self) -> None:
        self.level_timer.stop()
        self.orb.set_level(0.0)
        self.orb.set_busy(True)

        def work():
            try:
                text = self.core.stop_custom_recording()
                self.bridge.transcribed.emit(text, "")
            except Exception as exc:  # noqa: BLE001
                log.exception("Error transcribiendo")
                self.bridge.transcribed.emit("", str(exc))

        threading.Thread(target=work, daemon=True).start()

    def _on_transcribed(self, text: str, error: str) -> None:
        self.orb.set_busy(False)
        assistant = self.assistant_listening
        self.assistant_listening = False
        if error:
            log.error("Transcripcion fallida: %s", error)
            return
        if not text:
            log.info("Audio vacio o sin voz, nada que hacer")
            return
        log.info("%s: %s", "Orden" if assistant else "Dictado", text)
        if assistant:
            # La tecla del asistente: todo lo que digas es una orden.
            self._run_command(parse_command(text, strict=False), text)
            return
        self._on_dictated(text)

    def _on_dictated(self, text: str) -> None:
        """Dictado normal. Si empieza como una orden clara ("optimiza
        prompt profesional...", "pasa esto a legal") la resuelve el
        asistente; si no, se escribe tal cual donde estabas."""
        command = parse_command(text, strict=True)
        if command is not None:
            self._run_command(command, text)
            return
        # Las acciones de IA viven en el boton derecho, que sigue teniendo
        # este texto a mano por si lo quieres pulir despues.
        self.pending_text = text
        self._paste(text, remember=True)

    # ------------------------------------------------------------------
    # Ordenes por voz
    # ------------------------------------------------------------------

    def _source_text(self) -> tuple[str, str]:
        """Sobre qué texto actúa una orden sin contenido ("pasa esto a
        legal"): lo que haya en la mesa de trabajo; si no, lo que hayas
        copiado despues de dictar; si no, lo ultimo que dictaste."""
        if self.panel is not None:
            try:
                text = self.panel.text().strip()
                if text:
                    return text, "la mesa de trabajo"
            except RuntimeError:
                self.panel = None
        try:
            clip = (pyperclip.paste() or "").strip()
        except Exception:
            clip = ""
        if len(clip) > 8000:
            clip = ""
        last = self.core.last_dictation or self.pending_text
        copied_after = clip and clip != (self.core.clipboard_at_dictation or "").strip()
        if clip and (copied_after or not last):
            return clip, "lo que has copiado"
        if last:
            return last, "lo último que dictaste"
        return "", ""

    def _run_command(self, command, spoken: str) -> None:
        if command is None:
            return
        action = command.action
        content = command.content.strip()
        origin = "lo que has dicho"
        if len(content.split()) < 3:
            source, origin = self._source_text()
            if source:
                content = source
        if not content:
            if not action.keywords:
                # Orden libre sin texto al que aplicarla ("escribe un
                # correo de bienvenida para nuevos clientes"): se crea
                # desde cero.
                content = "(Sin texto previo: crea el contenido desde cero siguiendo el encargo.)"
                origin = "cero"
            else:
                self._show_panel(
                    "",
                    note=f"Entendido: {action.label}. Copia o dicta el texto y vuelve a pedirlo.",
                )
                return
        log.info("Orden '%s' sobre %s (%d caracteres)", action.label, origin, len(content))
        # La mesa se abre ya con el texto de partida, para que se vea que
        # la orden se ha entendido mientras el modelo trabaja.
        if self.panel is None:
            self._show_panel(content if origin != "cero" else "")
        self._polish(action, content)

    # ------------------------------------------------------------------
    # Mini-burbujas
    # ------------------------------------------------------------------

    def _current_text(self) -> str:
        """Sobre que texto actuan las acciones: lo ultimo dictado y, si no
        hay nada, lo que haya en el portapapeles. Asi se puede copiar un
        prompt de cualquier sitio, pulsar el boton derecho y mejorarlo sin
        haber dictado nada."""
        if self.pending_text:
            return self.pending_text
        if self.core.last_dictation:
            return self.core.last_dictation
        try:
            clip = (pyperclip.paste() or "").strip()
        except Exception:
            return ""
        return clip if 0 < len(clip) <= 8000 else ""

    def _show_actions(self) -> None:
        self._open_bubbles(self._menu_actions())

    def _menu_actions(self) -> list[tuple[str, str]]:
        if self._current_text():
            return (
                [(a.label, a.label) for a in MENU_ACTIONS]
                + [("Panel y más modos", "__panel__"), ("Cerrar", "__quit__")]
            )
        return [
            ("Más grande", "__bigger__"),
            ("Más pequeño", "__smaller__"),
            ("Cerrar", "__quit__"),
        ]

    def _on_menu(self) -> None:
        self._open_bubbles(self._menu_actions())

    def _open_bubbles(self, actions: list[tuple[str, str]]) -> None:
        _close_safely(self.bubbles)
        self.bubbles = ActionBubbles(
            actions, self.orb.orb_center(), self.orb.orb_radius()
        )
        self.bubbles.chosen.connect(self._on_action)
        # Qt borra el objeto C++ al cerrarse (WA_DeleteOnClose) y la
        # referencia de Python se queda apuntando a un cadaver: tocarla
        # lanza RuntimeError. Se limpia en cuanto muere.
        self.bubbles.destroyed.connect(self._forget_bubbles)
        self.bubbles.dismissed.connect(self._forget_bubbles)
        self.bubbles.show()
        self.bubbles.raise_()
        self.bubbles.activateWindow()

    def _on_action(self, label: str, payload: str) -> None:
        self.bubbles = None
        if payload == "__quit__":
            self.quit()
            return
        if payload == "__bigger__":
            self.orb.set_size(self.orb.base_size + 8)
            return
        if payload == "__smaller__":
            self.orb.set_size(self.orb.base_size - 8)
            return
        if payload == "__panel__":
            text = self._current_text()
            if text:
                self.pending_text = text
                self._show_panel(text)
            return
        action = ACTIONS_BY_LABEL.get(payload)
        if action is not None:
            self._polish(action)

    # ------------------------------------------------------------------
    # Pulido con IA
    # ------------------------------------------------------------------

    def _polish(self, action, text: str | None = None) -> None:
        """Si el panel esta abierto se trabaja sobre lo que hay en el, que
        puede venir ya pulido de una accion anterior: asi se puede encadenar
        (corregir, luego formal, luego resumir) sin salir de la mesa."""
        text = text if text is not None else self._current_text()
        if not text:
            return
        self.pending_text = text

        engine = get_engine(self.core.engine_env)
        if not self._engine_ready(engine):
            self._show_ollama_panel(engine)
            return

        self.polish_serial += 1
        serial = self.polish_serial
        self.orb.set_busy(True)
        if self.panel is not None:
            self._panel_busy(f"{action.label}: trabajando...")
        log.info("Pulido '%s' sobre %d caracteres", action.label, len(text))

        def work():
            started = time.monotonic()
            try:
                result = engine.polish(
                    text,
                    action.instruction,
                    system=action.system,
                    temperature=action.temperature,
                )
                log.info("Pulido listo en %.1fs", time.monotonic() - started)
                if serial == self.polish_serial:
                    self.bridge.polished.emit(result, "")
            except Exception as exc:  # noqa: BLE001
                log.exception("Error llamando al motor de IA")
                if serial == self.polish_serial:
                    self.bridge.polished.emit("", str(exc))

        threading.Thread(target=work, daemon=True).start()

    def _engine_ready(self, engine) -> bool:
        try:
            return bool(engine.is_available())
        except Exception:
            return False

    def _panel_busy(self, label: str | None) -> None:
        try:
            if self.panel is not None:
                self.panel.set_busy(label)
        except RuntimeError:
            self.panel = None

    def _cancel_polish(self) -> None:
        """No se puede abortar la peticion HTTP, pero si ignorar su
        respuesta y devolver el panel al usuario ahora mismo."""
        self.polish_serial += 1
        self.orb.set_busy(False)
        self._panel_busy(None)

    def _on_polished(self, text: str, error: str) -> None:
        self.orb.set_busy(False)
        if error:
            # Sin modelo o sin red no se pierde el dictado: se ofrece el
            # texto en crudo, que es mejor que quedarse sin nada.
            log.error("Pulido fallido: %s", error)
            self._show_panel(self.pending_text, note=f"No se pudo pulir: {error}")
            return
        if self.panel is not None:
            try:
                self.panel.set_text(text)
                self.panel.set_busy(None)
                self.panel.raise_()
                return
            except RuntimeError:
                self.panel = None
        self._show_panel(text)

    def _show_panel(self, text: str, note: str | None = None) -> None:
        _close_safely(self.panel)
        self.panel = ResultPanel(
            text,
            self.orb.orb_center(),
            [a.label for a in MENU_ACTIONS],
            [a.label for a in ACTIONS],
        )
        self.panel.destroyed.connect(self._forget_panel)
        self.panel.paste_requested.connect(self._paste_from_panel)
        self.panel.action_requested.connect(self._on_panel_action)
        self.panel.free_requested.connect(self._on_panel_free)
        self.panel.cancel_requested.connect(self._cancel_polish)
        self.panel.dismissed.connect(self._forget)
        self.panel.show()
        self.panel.raise_()
        self.panel.activateWindow()
        if note:
            self.panel.status.setText(note)

    def _on_panel_action(self, label: str, text: str) -> None:
        action = ACTIONS_BY_LABEL.get(label)
        if action is not None:
            self._polish(action, text)

    def _on_panel_free(self, instruction: str, text: str) -> None:
        """Lo escrito en "Pídele otra cosa": si nombra un modo conocido se
        usa ese experto; si no, la frase es el encargo."""
        command = parse_command(instruction, strict=False)
        if command is None:
            return
        action = command.action
        if not action.keywords and not action.instruction:
            action = free_action(instruction)
        self._polish(action, text or "(Sin texto previo: crea el contenido desde cero siguiendo el encargo.)")

    def _paste_from_panel(self, text: str) -> None:
        _close_safely(self.panel)
        self.panel = None
        self.pending_text = ""
        self._paste(text)

    def _forget(self) -> None:
        self.panel = None
        self.pending_text = ""

    # ------------------------------------------------------------------
    # IA local que no responde: explicarlo e instalarla
    # ------------------------------------------------------------------

    def _show_ollama_panel(self, engine) -> None:
        _close_safely(self.ollama_panel)
        model = getattr(engine, "model", "?")
        host = getattr(engine, "host", "?")
        if sys.platform == "win32":
            command = f"Descarga Ollama de ollama.com y luego: ollama pull {model}"
        else:
            command = f"{ollama_setup.linux_mac_install_command()} && ollama pull {model}"
        self.ollama_panel = OllamaPanel(self.orb.orb_center(), model, host, command)
        self.ollama_panel.destroyed.connect(self._forget_ollama_panel)
        self.ollama_panel.install_requested.connect(lambda: self._install_ollama(engine))
        self.ollama_panel.retry_requested.connect(self._retry_after_install)
        self.ollama_panel.dismissed.connect(self._forget_ollama_panel)
        self.ollama_panel.show()
        self.ollama_panel.raise_()
        self.ollama_panel.activateWindow()
        log.warning("IA local no disponible (%s, modelo %s)", host, model)

    def _install_ollama(self, engine) -> None:
        host = getattr(engine, "host", "http://localhost:11434")
        model = getattr(engine, "model", "")

        def work():
            try:
                if sys.platform == "win32":
                    import os
                    import tempfile

                    dest = os.path.join(tempfile.gettempdir(), "OllamaSetup.exe")
                    self.bridge.install_status.emit("Descargando el instalador...")
                    ollama_setup.download_windows_installer(dest)
                    ollama_setup.launch_windows_installer(dest)
                    self.bridge.install_done.emit(
                        "Instalador abierto. Termínalo y pulsa Reintentar."
                    )
                    return

                if not ollama_setup.is_ollama_running(host):
                    self.bridge.install_status.emit(
                        "Abriendo una terminal para instalar Ollama "
                        "(puede pedirte tu contraseña)..."
                    )
                    ollama_setup.run_install_linux_mac().wait()
                    self.bridge.install_status.emit("Esperando a que Ollama arranque...")
                    for _ in range(30):
                        if ollama_setup.is_ollama_running(host):
                            break
                        time.sleep(1)
                    else:
                        self.bridge.install_done.emit(
                            "Ollama no respondió. Pulsa Reintentar cuando esté listo."
                        )
                        return

                if not ollama_setup.has_model(host, model):
                    self.bridge.install_status.emit(f"Descargando el modelo {model}...")
                    ollama_setup.pull_model(
                        host,
                        model,
                        on_progress=lambda s: self.bridge.install_status.emit(
                            f"Descargando {model}: {s}"
                        ),
                        on_fraction=self.bridge.install_fraction.emit,
                    )
                self.bridge.install_status.emit("Preparando el asistente...")
                ollama_setup.create_assistant_model(host, model)
                self.bridge.install_done.emit("Listo. Ya puedes usar el asistente.")
            except Exception as exc:  # noqa: BLE001
                log.exception("Error instalando Ollama")
                self.bridge.install_done.emit(f"No se pudo instalar: {exc}")

        threading.Thread(target=work, daemon=True).start()

    def _on_install_status(self, text: str) -> None:
        try:
            if self.ollama_panel is not None:
                self.ollama_panel.set_status(text)
        except RuntimeError:
            self.ollama_panel = None

    def _on_install_fraction(self, fraction: float) -> None:
        try:
            if self.ollama_panel is not None:
                self.ollama_panel.set_fraction(fraction)
        except RuntimeError:
            self.ollama_panel = None

    def _on_install_done(self, message: str) -> None:
        try:
            if self.ollama_panel is not None:
                self.ollama_panel.finish(message)
        except RuntimeError:
            self.ollama_panel = None

    def _retry_after_install(self) -> None:
        engine = get_engine(self.core.engine_env)
        if self._engine_ready(engine):
            _close_safely(self.ollama_panel)
            self.ollama_panel = None
            self._show_actions()
        else:
            self._on_install_status("Sigue sin responder. Revisa la terminal.")

    def _forget_ollama_panel(self, *_) -> None:
        self.ollama_panel = None

    def _forget_bubbles(self, *_) -> None:
        self.bubbles = None

    def _forget_panel(self, *_) -> None:
        self.panel = None

    def _paste(self, text: str, remember: bool = False) -> None:
        """Devuelve el foco a la ventana donde estabas y pega alli.

        Sin el paso de restituir el foco, el Ctrl+V simulado acaba en la
        ventana del orbe y el texto no aparece en ningun sitio (aunque
        queda en el portapapeles, que es el plan B de siempre)."""
        if not text:
            return
        self.focus.restore()

        def do_paste():
            previous = paste_text(text, self.core.auto_paste)
            if remember:
                self.core.remember_dictation(text, previous)

        QTimer.singleShot(PASTE_DELAY_MS, do_paste)

    # ------------------------------------------------------------------

    def start_dictation_from_hotkey(self) -> None:
        """La tecla del asistente: graba como el orbe, se trae el orbe a la
        pantalla donde estas trabajando, y lo que digas se trata como una
        orden ("optimiza prompt profesional...", "pasa esto a legal")."""
        self.assistant_listening = True
        self.orb.summon()
        self.orb.listening = True
        self.orb._ensure_timer()
        self._on_start()

    def stop_dictation_from_hotkey(self) -> None:
        self.orb.listening = False
        self.orb._ensure_timer()
        self._on_stop()

    def quit(self) -> None:
        self.orb.close()
        self.app.quit()

    def run(self) -> int:
        self.orb.show()
        return self.app.exec()
