"""Cargador con la marca Odoo I+D+E: el propio orbe girando y una barra
en púrpura y teal corporativos.

La barra de serie de Qt es un rectángulo azul de sistema que no pinta
nada junto al orbe. Esta reutiliza los mismos fotogramas del orbe, así
que esperar a la IA se parece a lo que ya estabas mirando."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPixmap
from PyQt6.QtWidgets import QWidget

FRAMES_DIR = Path(__file__).resolve().parent / "assets" / "orb-frames"

TRACK = QColor("#0F0A16")
PURPLE = QColor("#714B67")      # primario Odoo
PURPLE_LIGHT = QColor("#875A7B")
TEAL = QColor("#017E84")        # secundario Odoo

FPS_MS = 50
BAR_HEIGHT = 10
GAP = 10


class BrandLoader(QWidget):
    def __init__(self, parent: QWidget | None = None, orb_size: int = 26):
        super().__init__(parent)
        self.orb_size = orb_size
        self.setFixedHeight(max(orb_size, BAR_HEIGHT))
        self.frames = [QPixmap(str(p)) for p in sorted(FRAMES_DIR.glob("orb*.webp"))]
        self._scaled: list[QPixmap] = []
        self.index = 0
        self.travel = 0.0
        self.fraction: float | None = None   # None = no sabemos cuánto falta
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    # ------------------------------------------------------------------

    def start(self) -> None:
        if not self.timer.isActive():
            self.timer.start(FPS_MS)
        self.show()

    def stop(self) -> None:
        self.timer.stop()
        self.hide()

    def set_fraction(self, fraction: float | None) -> None:
        """Con porcentaje real pinta el avance; sin él, la luz viaja."""
        self.fraction = fraction
        self.update()

    def _tick(self) -> None:
        if self.frames:
            self.index = (self.index + 1) % len(self.frames)
        self.travel = (self.travel + 0.018) % 1.0
        self.update()

    # ------------------------------------------------------------------

    def _orb_frames(self) -> list[QPixmap]:
        dpr = self.devicePixelRatioF()
        target = int(self.orb_size * dpr)
        if not self._scaled or self._scaled[0].width() != target:
            self._scaled = []
            for frame in self.frames:
                scaled = frame.scaled(
                    target,
                    target,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                scaled.setDevicePixelRatio(dpr)
                self._scaled.append(scaled)
        return self._scaled

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        left = 0
        if self.frames:
            frames = self._orb_frames()
            pixmap = frames[self.index % len(frames)]
            top = (self.height() - self.orb_size) / 2
            painter.drawPixmap(0, int(top), pixmap)
            left = self.orb_size + GAP

        bar = QRectF(left, (self.height() - BAR_HEIGHT) / 2,
                     max(0, self.width() - left), BAR_HEIGHT)
        track = QPainterPath()
        track.addRoundedRect(bar, BAR_HEIGHT / 2, BAR_HEIGHT / 2)
        painter.fillPath(track, TRACK)

        if self.fraction is None:
            # Un destello que recorre la barra de lado a lado, con el
            # purpura y el teal de Odoo dentro del propio destello: si el
            # degradado se reparte por toda la barra, el trozo visible
            # sale de un solo tono y no se reconoce la marca.
            width = bar.width() * 0.40
            span = bar.width() + width
            x = bar.left() - width + span * self.travel
            light = QRectF(x, bar.top(), width, BAR_HEIGHT)
            gradient = QLinearGradient(light.left(), 0, light.right(), 0)
            gradient.setColorAt(0.0, QColor(PURPLE.red(), PURPLE.green(), PURPLE.blue(), 0))
            gradient.setColorAt(0.35, PURPLE_LIGHT)
            gradient.setColorAt(0.7, TEAL)
            gradient.setColorAt(1.0, QColor(TEAL.red(), TEAL.green(), TEAL.blue(), 0))
        else:
            light = QRectF(bar.left(), bar.top(),
                           bar.width() * max(0.0, min(1.0, self.fraction)), BAR_HEIGHT)
            gradient = QLinearGradient(light.left(), 0, light.right(), 0)
            gradient.setColorAt(0.0, PURPLE)
            gradient.setColorAt(0.6, PURPLE_LIGHT)
            gradient.setColorAt(1.0, TEAL)

        if light.width() > 0:
            painter.setClipPath(track)
            painter.fillRect(light, gradient)
        painter.end()
