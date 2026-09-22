"""Orbe flotante de Vozdoo: vive en una esquina, escucha al mantener el
clic y abre las mini-burbujas de accion con el boton derecho.

Ventana sin marco, siempre encima y con transparencia real por pixel
(PyQt6). Los fotogramas de `assets/orb-frames/` solo se reproducen
mientras se esta hablando: en reposo el orbe se queda congelado y no
gasta CPU."""

from __future__ import annotations

import json
import logging
import math
import sys
from pathlib import Path

from PyQt6.QtCore import QPoint, QPointF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QGuiApplication, QPainter, QPixmap, QRadialGradient
from PyQt6.QtWidgets import QWidget

log = logging.getLogger("vozdoo")

FRAMES_DIR = Path(__file__).resolve().parent / "assets" / "orb-frames"
STATE_FILE = Path(__file__).resolve().parent / ".orb-state.json"

MIN_SIZE = 28
MAX_SIZE = 140
DEFAULT_SIZE = 44
MARGIN = 14          # separacion de la esquina al arrancar por primera vez
DRAG_THRESHOLD = 10  # pixeles que hay que mover para que sea arrastre y no dictado
FPS_MS = 50          # 20 fps, el ritmo del video original

PURPLE = QColor(135, 90, 123)
CYAN = QColor(77, 217, 230)


class OrbWidget(QWidget):
    """Señales hacia el nucleo. El orbe no sabe grabar ni transcribir:
    solo dice cuando el usuario empieza y deja de hablar."""

    dictation_started = pyqtSignal()
    dictation_stopped = pyqtSignal()
    dictation_cancelled = pyqtSignal()
    menu_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setToolTip(
            "Vozdoo — manten pulsado para dictar, boton derecho para las acciones, "
            "arrastra para moverlo, rueda para cambiar el tamaño"
        )

        self.frames = [QPixmap(str(p)) for p in sorted(FRAMES_DIR.glob("orb*.webp"))]
        if not self.frames:
            log.warning("No hay fotogramas del orbe en %s", FRAMES_DIR)

        self.base_size = DEFAULT_SIZE
        self.index = 0
        self.phase = 0.0
        self.level = 0.0          # volumen del micro, 0..1
        self.hover = False
        self.listening = False
        self.busy = False         # pensando: el nucleo esta llamando al modelo
        self._press_origin: QPoint | None = None
        self._window_origin: QPoint | None = None
        self._dragging = False
        self._size_now = float(DEFAULT_SIZE)
        self._scaled_cache: dict[int, list[QPixmap]] = {}

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

        self._restore_state()
        self._apply_box()

    # ------------------------------------------------------------------
    # Estado persistente (posicion y tamaño entre arranques)
    # ------------------------------------------------------------------

    def _restore_state(self) -> None:
        try:
            saved = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            self.base_size = max(MIN_SIZE, min(MAX_SIZE, int(saved["size"])))
            self._size_now = float(self.base_size)
            self._saved_pos = QPoint(int(saved["x"]), int(saved["y"]))
        except Exception:
            self._saved_pos = None

    def _save_state(self) -> None:
        try:
            STATE_FILE.write_text(
                json.dumps({"x": self.x(), "y": self.y(), "size": self.base_size}),
                encoding="utf-8",
            )
        except Exception:
            log.debug("No se pudo guardar la posicion del orbe", exc_info=True)

    # ------------------------------------------------------------------
    # Geometria
    # ------------------------------------------------------------------

    def _box(self) -> int:
        """La ventana es mayor que el orbe para que quepa el halo."""
        return int(MAX_SIZE * 1.9) if self.base_size > 90 else int(self.base_size * 2.6) + 40

    def _apply_box(self) -> None:
        box = self._box()
        center = self.geometry().center() if self.isVisible() else None
        self.resize(box, box)
        if center is not None:
            self.move(center.x() - box // 2, center.y() - box // 2)
        elif self._saved_pos is not None:
            self.move(self._saved_pos)
        else:
            screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
            area = screen.availableGeometry()
            self.move(area.right() - box - MARGIN, area.bottom() - box - MARGIN)

    def orb_center(self) -> QPoint:
        """Centro del orbe en coordenadas de pantalla, para colocar las
        mini-burbujas y el panel de resultado alrededor."""
        return self.geometry().center()

    def orb_radius(self) -> int:
        return int(self._size_now / 2)

    def set_size(self, size: int) -> None:
        self.base_size = max(MIN_SIZE, min(MAX_SIZE, int(size)))
        self._scaled_cache.clear()
        self._apply_box()
        self._ensure_timer()
        self.update()
        self._save_state()

    # ------------------------------------------------------------------
    # Estados
    # ------------------------------------------------------------------

    def set_level(self, level: float) -> None:
        """Volumen del micro (0..1): el halo late con la voz de verdad."""
        self.level = max(0.0, min(1.0, level))

    def set_busy(self, busy: bool) -> None:
        self.busy = busy
        self._ensure_timer()
        self.update()

    def _target_size(self) -> float:
        if self.listening:
            return self.base_size * 1.75
        if self.busy:
            return self.base_size * 1.4
        if self.hover:
            return self.base_size * 1.35
        return float(self.base_size)

    def _animating(self) -> bool:
        return (
            self.listening
            or self.busy
            or abs(self._size_now - self._target_size()) > 0.5
        )

    def _ensure_timer(self) -> None:
        """El reloj solo corre cuando hay algo que animar. En reposo el
        orbe esta congelado y el proceso no consume CPU."""
        if self._animating():
            if not self.timer.isActive():
                self.timer.start(FPS_MS)
        elif self.timer.isActive():
            self.timer.stop()
            self.update()

    def _tick(self) -> None:
        if self.listening:
            self.index = (self.index + 1) % max(1, len(self.frames))
            self.phase += 0.12
        elif self.busy:
            self.phase += 0.18
        else:
            self.index = 0
        self._size_now += (self._target_size() - self._size_now) * 0.3
        self.update()
        self._ensure_timer()

    # ------------------------------------------------------------------
    # Raton: mantener = dictar, arrastrar = mover, rueda = tamaño
    # ------------------------------------------------------------------

    def enterEvent(self, event):  # noqa: N802 (API de Qt)
        self.hover = True
        self._ensure_timer()

    def leaveEvent(self, event):  # noqa: N802
        self.hover = False
        self._ensure_timer()

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.MouseButton.RightButton:
            self.menu_requested.emit()
            return
        if event.button() != Qt.MouseButton.LeftButton:
            return
        self._press_origin = event.globalPosition().toPoint()
        self._window_origin = self.pos()
        self._dragging = False
        self.listening = True
        self._ensure_timer()
        self.dictation_started.emit()

    def mouseMoveEvent(self, event):  # noqa: N802
        if self._press_origin is None:
            return
        delta = event.globalPosition().toPoint() - self._press_origin
        if not self._dragging and delta.manhattanLength() > DRAG_THRESHOLD:
            # Se ha movido: no queria dictar, queria mover el orbe.
            self._dragging = True
            if self.listening:
                self.listening = False
                self.dictation_cancelled.emit()
        if self._dragging and self._window_origin is not None:
            self.move(self._window_origin + delta)

    def mouseReleaseEvent(self, event):  # noqa: N802
        if event.button() != Qt.MouseButton.LeftButton:
            return
        was_listening = self.listening
        self.listening = False
        self._press_origin = None
        self._window_origin = None
        self._ensure_timer()
        if self._dragging:
            self._dragging = False
            self._save_state()
            return
        if was_listening:
            self.dictation_stopped.emit()

    def wheelEvent(self, event):  # noqa: N802
        step = 4 if event.angleDelta().y() > 0 else -4
        self.set_size(self.base_size + step)

    # ------------------------------------------------------------------
    # Pintado
    # ------------------------------------------------------------------

    def _frames_at(self, size: int) -> list[QPixmap]:
        """Escala los fotogramas una vez por tamaño en vez de en cada
        repintado: a 20 fps, reescalar 24 imagenes cada vez es tirar CPU.
        Se escala a pixeles fisicos y se marca el ratio, que si no en
        pantallas con escalado el orbe sale borroso."""
        dpr = self.devicePixelRatioF()
        key = int(size * dpr)
        cached = self._scaled_cache.get(key)
        if cached is None:
            cached = []
            for frame in self.frames:
                scaled = frame.scaled(
                    key,
                    key,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                scaled.setDevicePixelRatio(dpr)
                cached.append(scaled)
            if len(self._scaled_cache) > 8:
                self._scaled_cache.clear()
            self._scaled_cache[key] = cached
        return cached

    def paintEvent(self, event):  # noqa: N802
        if not self.frames:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center = QPointF(self.width() / 2, self.height() / 2)

        if self.listening:
            # Mientras se habla el orbe late con el volumen real del micro.
            diameter = self._size_now * (1.0 + 0.16 * self.level)
        elif self.busy:
            diameter = self._size_now * (1.0 + 0.03 * math.sin(self.phase))
        else:
            diameter = self._size_now

        if self.listening or self.busy or self.hover:
            halo_r = diameter * (1.05 if self.listening else 0.95)
            halo = QRadialGradient(center, halo_r)
            if self.listening:
                strength = int(150 + 90 * self.level)
            elif self.busy:
                strength = 150
            else:
                strength = 120
            halo.setColorAt(0.45, QColor(PURPLE.red(), PURPLE.green(), PURPLE.blue(), strength))
            halo.setColorAt(0.75, QColor(CYAN.red(), CYAN.green(), CYAN.blue(), strength // 3))
            halo.setColorAt(1.0, QColor(0, 0, 0, 0))
            painter.setBrush(halo)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, halo_r, halo_r)

        painter.setOpacity(1.0 if (self.hover or self.listening or self.busy) else 0.85)
        size = max(1, int(diameter))
        frames = self._frames_at(size)
        pix = frames[self.index % len(frames)]
        painter.drawPixmap(
            int(center.x() - size / 2), int(center.y() - size / 2), pix
        )
        painter.end()

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        self._follow_all_desktops()

    def _follow_all_desktops(self) -> None:
        """Que el orbe esté en todos los escritorios virtuales.

        Sin esto el orbe se queda en el escritorio donde arrancó y
        desaparece al cambiar de área de trabajo, que es justo cuando más
        falta hace. Qt no lo expone, así que se pide por EWMH con
        python-xlib (ya viene con pynput en Linux). Si algo falla, el orbe
        sigue funcionando: solo se queda en su escritorio."""
        if sys.platform != "linux":
            return
        try:
            from Xlib import X, Xatom, display, protocol

            disp = display.Display()
            win = disp.create_resource_object("window", int(self.winId()))
            root = disp.screen().root

            # 0xFFFFFFFF = "en todos los escritorios"
            win.change_property(
                disp.intern_atom("_NET_WM_DESKTOP"), Xatom.CARDINAL, 32, [0xFFFFFFFF]
            )
            # Y el mensaje que entienden los gestores de ventanas modernos
            # para una ventana ya mapeada.
            event = protocol.event.ClientMessage(
                window=win,
                client_type=disp.intern_atom("_NET_WM_STATE"),
                data=(32, [1, disp.intern_atom("_NET_WM_STATE_STICKY"), 0, 1, 0]),
            )
            root.send_event(
                event, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask
            )
            disp.flush()
        except Exception:
            log.debug("No se pudo fijar el orbe a todos los escritorios", exc_info=True)

    def closeEvent(self, event):  # noqa: N802
        self._save_state()
        super().closeEvent(event)
