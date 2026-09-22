"""Pega el orbe con el nucleo: microfono, Whisper, motor de IA y pegado.

El orbe solo emite señales ("he empezado a hablar", "he elegido esta
accion"); aqui se decide que hacer con ellas. Todo lo que tarda —
transcribir y llamar al modelo — corre en un hilo aparte para que el
orbe siga animandose."""

from __future__ import annotations

import logging
import threading

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication

from action_bubbles import ActionBubbles
from clipboard_paste import paste_text
from llm_engine import get_engine
from orb_widget import OrbWidget
from polish_actions import PRESET_INSTRUCTIONS
from result_panel import ResultPanel

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
    hotkey_start = pyqtSignal()          # emitidas desde el hilo del listener
    hotkey_stop = pyqtSignal()


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

        self.level_timer = QTimer()
        self.level_timer.setInterval(50)
        self.level_timer.timeout.connect(self._poll_level)

        self.orb.dictation_started.connect(self._on_start)
        self.orb.dictation_stopped.connect(self._on_stop)
        self.orb.dictation_cancelled.connect(self._on_cancel)
        self.orb.menu_requested.connect(self._on_menu)
        self.orb.quit_requested.connect(self.quit)
        self.bridge.transcribed.connect(self._on_transcribed)
        self.bridge.polished.connect(self._on_polished)
        self.bridge.hotkey_start.connect(self.start_dictation_from_hotkey)
        self.bridge.hotkey_stop.connect(self.stop_dictation_from_hotkey)

    # ------------------------------------------------------------------
    # Dictado
    # ------------------------------------------------------------------

    def _on_start(self) -> None:
        self.core.start_custom_recording()
        self.level_timer.start()

    def _poll_level(self) -> None:
        self.orb.set_level(self.core.mic_level())

    def _on_cancel(self) -> None:
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
        if error:
            log.error("Transcripcion fallida: %s", error)
            return
        if not text:
            log.info("Audio vacio o sin voz, nada que hacer")
            return
        self.pending_text = text
        log.info("Dictado: %s", text)
        self._show_actions()

    # ------------------------------------------------------------------
    # Mini-burbujas
    # ------------------------------------------------------------------

    def _show_actions(self) -> None:
        actions = [("Tal cual", "")] + list(PRESET_INSTRUCTIONS.items())
        self._open_bubbles(actions)

    def _on_menu(self) -> None:
        """Boton derecho. Si hay algo dictado, las acciones sobre ese
        texto; si no, las de manejo del propio orbe."""
        if self.pending_text:
            self._show_actions()
            return
        self._open_bubbles(
            [
                ("Más grande", "__bigger__"),
                ("Más pequeño", "__smaller__"),
                ("Salir", "__quit__"),
            ]
        )

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

    def _on_action(self, label: str, instruction: str) -> None:
        self.bubbles = None
        if instruction == "__quit__":
            self.quit()
            return
        if instruction == "__bigger__":
            self.orb.set_size(self.orb.base_size + 8)
            return
        if instruction == "__smaller__":
            self.orb.set_size(self.orb.base_size - 8)
            return
        if instruction == "":
            self._paste(self.pending_text)
            self.pending_text = ""
            return
        self._polish(instruction)

    # ------------------------------------------------------------------
    # Pulido con IA
    # ------------------------------------------------------------------

    def _polish(self, instruction: str) -> None:
        self.orb.set_busy(True)
        text = self.pending_text
        engine = get_engine(self.core.engine_env)

        def work():
            try:
                self.bridge.polished.emit(engine.polish(text, instruction), "")
            except Exception as exc:  # noqa: BLE001
                log.exception("Error llamando al motor de IA")
                self.bridge.polished.emit("", str(exc))

        threading.Thread(target=work, daemon=True).start()

    def _on_polished(self, text: str, error: str) -> None:
        self.orb.set_busy(False)
        if error:
            # Sin modelo o sin red no se pierde el dictado: se ofrece el
            # texto en crudo, que es mejor que quedarse sin nada.
            log.error("Pulido fallido: %s", error)
            self._show_panel(self.pending_text)
            return
        self._show_panel(text)

    def _show_panel(self, text: str) -> None:
        _close_safely(self.panel)
        self.panel = ResultPanel(text, self.orb.orb_center())
        self.panel.destroyed.connect(self._forget_panel)
        self.panel.paste_requested.connect(self._paste_from_panel)
        self.panel.retry_requested.connect(self._show_actions)
        self.panel.dismissed.connect(self._forget)
        self.panel.show()
        self.panel.raise_()
        self.panel.activateWindow()

    def _paste_from_panel(self, text: str) -> None:
        _close_safely(self.panel)
        self.panel = None
        self.pending_text = ""
        self._paste(text)

    def _forget(self) -> None:
        self.panel = None
        self.pending_text = ""

    def _forget_bubbles(self, *_) -> None:
        self.bubbles = None

    def _forget_panel(self, *_) -> None:
        self.panel = None

    def _paste(self, text: str) -> None:
        """Se pega con un respiro: al cerrar nuestras ventanas el foco
        tarda un instante en volver a donde estaba el cursor."""
        if not text:
            return
        QTimer.singleShot(
            PASTE_DELAY_MS, lambda: paste_text(text, self.core.auto_paste)
        )

    # ------------------------------------------------------------------

    def start_dictation_from_hotkey(self) -> None:
        """El hotkey hace lo mismo que mantener pulsado el orbe."""
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
