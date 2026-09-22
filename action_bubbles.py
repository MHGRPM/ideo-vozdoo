"""Mini-burbujas de accion que brotan alrededor del orbe.

Es una sola ventana transparente a pantalla completa: asi un clic fuera
de cualquier burbuja las cierra, sin tener que perseguir el foco."""

from __future__ import annotations

import math

from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QColor,
    QCursor,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QPainter,
    QPainterPath,
)
from PyQt6.QtWidgets import QWidget

BUBBLE_H = 34
PAD_X = 18
GAP = 12
PURPLE = QColor("#875A7B")
PURPLE_HOT = QColor("#9E6C90")
TEAL = QColor("#017E84")
TEAL_HOT = QColor("#029197")
DANGER = QColor("#8C3B45")
INK = QColor("#F4F1F7")


class ActionBubbles(QWidget):
    chosen = pyqtSignal(str, str)   # etiqueta, instruccion ("" = pegar tal cual)
    dismissed = pyqtSignal()

    def __init__(self, actions: list[tuple[str, str]], center: QPoint, orb_radius: int):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMouseTracking(True)

        screen = QGuiApplication.screenAt(center) or QGuiApplication.primaryScreen()
        self.setGeometry(screen.geometry())

        self.actions = actions
        self.center = QPointF(center - screen.geometry().topLeft())
        self.orb_radius = orb_radius
        self.hot = -1
        self.progress = 0.0
        # El clic derecho que abre las burbujas suelta el boton encima de
        # esta ventana recien creada; sin este desarme inicial el propio
        # gesto de abrirlas las cerraba al instante.
        self.armed = False
        QTimer.singleShot(220, self._arm)

        self.font = QFont()
        self.font.setPointSize(10)
        self.metrics = QFontMetrics(self.font)

        self.rects = self._layout()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._grow)
        self.timer.start(16)

        # Red de seguridad: esta ventana es transparente y ocupa toda la
        # pantalla, asi que si se quedara abierta por un fallo el usuario
        # no podria pulsar en nada. Se cierra sola pase lo que pase.
        self.lifetime = QTimer(self)
        self.lifetime.setSingleShot(True)
        self.lifetime.timeout.connect(self._timeout)
        self.lifetime.start(12000)

    # ------------------------------------------------------------------

    def _layout(self) -> list[QRectF]:
        """Las burbujas se abren en abanico hacia el centro de la pantalla,
        que es donde hay sitio: el orbe suele vivir pegado a una esquina."""
        area = self.rect()
        to_center = QPointF(area.center()) - self.center
        base_angle = math.atan2(to_center.y(), to_center.x())
        count = len(self.actions)
        spread = math.radians(96)
        start = base_angle - spread / 2
        step = spread / max(1, count - 1)
        radius = self.orb_radius + 86

        rects: list[QRectF] = []
        for i, (label, _) in enumerate(self.actions):
            angle = start + step * i
            width = self.metrics.horizontalAdvance(label) + PAD_X * 2
            cx = self.center.x() + math.cos(angle) * (radius + width * 0.25)
            cy = self.center.y() + math.sin(angle) * radius
            rects.append(
                QRectF(cx - width / 2, cy - BUBBLE_H / 2, width, BUBBLE_H)
            )
        return rects

    def _arm(self) -> None:
        self.armed = True

    def _timeout(self) -> None:
        self.dismissed.emit()
        self.close()

    def _grow(self) -> None:
        self.progress = min(1.0, self.progress + 0.14)
        if self.progress >= 1.0:
            self.timer.stop()
        self.update()

    # ------------------------------------------------------------------

    def mouseMoveEvent(self, event):  # noqa: N802
        pos = event.position()
        hot = -1
        for i, rect in enumerate(self.rects):
            if rect.contains(pos):
                hot = i
                break
        if hot != self.hot:
            self.hot = hot
            self.setCursor(
                QCursor(Qt.CursorShape.PointingHandCursor if hot >= 0 else Qt.CursorShape.ArrowCursor)
            )
            self.update()

    def mousePressEvent(self, event):  # noqa: N802
        if not self.armed:
            return
        pos = event.position()
        for i, rect in enumerate(self.rects):
            if rect.contains(pos):
                label, instruction = self.actions[i]
                self.chosen.emit(label, instruction)
                self.close()
                return
        self.dismissed.emit()
        self.close()

    def keyPressEvent(self, event):  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.dismissed.emit()
            self.close()

    # ------------------------------------------------------------------

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self.font)

        for i, rect in enumerate(self.rects):
            # Cada burbuja sale despedida desde el centro del orbe, un
            # pelin despues que la anterior.
            delay = i * 0.06
            local = max(0.0, min(1.0, (self.progress - delay) / max(0.01, 1.0 - delay)))
            eased = 1 - (1 - local) ** 3
            if eased <= 0:
                continue
            grown = QRectF(
                self.center.x() + (rect.center().x() - self.center.x()) * eased
                - rect.width() / 2 * eased,
                self.center.y() + (rect.center().y() - self.center.y()) * eased
                - rect.height() / 2 * eased,
                rect.width() * eased,
                rect.height() * eased,
            )

            label, instruction = self.actions[i]
            if instruction == "__quit__":
                color = DANGER
            elif instruction == "":
                color = TEAL_HOT if i == self.hot else TEAL
            else:
                color = PURPLE_HOT if i == self.hot else PURPLE

            shadow = QPainterPath()
            shadow.addRoundedRect(grown.translated(0, 2), grown.height() / 2, grown.height() / 2)
            painter.fillPath(shadow, QColor(0, 0, 0, 70))

            path = QPainterPath()
            path.addRoundedRect(grown, grown.height() / 2, grown.height() / 2)
            painter.fillPath(path, color)

            if eased > 0.75:
                painter.setOpacity((eased - 0.75) / 0.25)
                painter.setPen(INK)
                painter.drawText(grown, Qt.AlignmentFlag.AlignCenter, label)
                painter.setOpacity(1.0)
        painter.end()
