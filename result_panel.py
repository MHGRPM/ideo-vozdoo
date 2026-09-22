"""Panel con el texto ya pulido, para revisarlo (y retocarlo) antes de
pegarlo. Sin marco, oscuro y pegado al orbe."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QGuiApplication, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

WIDTH = 420
BG = "#171022"
INK = "#F4F1F7"
MUTED = "#A99FB8"
PURPLE = "#875A7B"
PURPLE_HOT = "#9E6C90"
TEAL = "#017E84"
TEAL_HOT = "#029197"

BUTTON_CSS = """
QPushButton {{
    background: {bg};
    color: {fg};
    border: none;
    border-radius: 8px;
    padding: 9px 14px;
    font-size: 13px;
}}
QPushButton:hover {{ background: {hot}; }}
"""


class ResultPanel(QWidget):
    paste_requested = pyqtSignal(str)
    retry_requested = pyqtSignal()
    dismissed = pyqtSignal()

    def __init__(self, text: str, anchor: QPoint):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        self.editor = QTextEdit()
        self.editor.setPlainText(text)
        self.editor.setStyleSheet(
            f"QTextEdit {{ background: #0F0A16; color: {INK}; border: 1px solid #2A1F3D;"
            f" border-radius: 10px; padding: 10px; font-size: 14px; }}"
        )
        self.editor.setMinimumHeight(120)
        layout.addWidget(self.editor)

        row = QHBoxLayout()
        row.setSpacing(8)
        paste = QPushButton("Pegar")
        paste.setStyleSheet(BUTTON_CSS.format(bg=TEAL, hot=TEAL_HOT, fg=INK))
        paste.clicked.connect(lambda: self.paste_requested.emit(self.editor.toPlainText()))
        retry = QPushButton("Otra acción")
        retry.setStyleSheet(BUTTON_CSS.format(bg=PURPLE, hot=PURPLE_HOT, fg=INK))
        retry.clicked.connect(self._retry)
        close = QPushButton("Descartar")
        close.setStyleSheet(BUTTON_CSS.format(bg="#211936", hot="#2E2348", fg=MUTED))
        close.clicked.connect(self._dismiss)
        for button in (paste, retry, close):
            row.addWidget(button)
        layout.addLayout(row)

        self.resize(WIDTH, 220)
        self._place_near(anchor)
        self.editor.setFocus()

    def _place_near(self, anchor: QPoint) -> None:
        """Se coloca al lado del orbe, pero sin salirse de la pantalla:
        el orbe suele estar en una esquina y el panel no cabe hacia fuera."""
        screen = QGuiApplication.screenAt(anchor) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        x = anchor.x() - self.width() // 2
        y = anchor.y() - self.height() - 40
        x = max(area.left() + 10, min(x, area.right() - self.width() - 10))
        y = max(area.top() + 10, min(y, area.bottom() - self.height() - 10))
        self.move(x, y)

    def _retry(self) -> None:
        self.retry_requested.emit()
        self.close()

    def _dismiss(self) -> None:
        self.dismissed.emit()
        self.close()

    def keyPressEvent(self, event):  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self._dismiss()
        elif event.key() == Qt.Key.Key_Return and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.paste_requested.emit(self.editor.toPlainText())

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(float(0), float(0), float(self.width()), float(self.height()), 16, 16)
        painter.fillPath(path, QColor(BG))
        painter.end()
