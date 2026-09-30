"""Mesa de trabajo: el texto dictado o pulido, editable, con las acciones
de IA a mano para seguir puliendo sin cerrar nada, y el boton de pegar
para mandarlo a la ventana donde estabas (Gmail, un documento, lo que sea).

Abajo del todo, "Pídele otra cosa": escribes el encargo con tus palabras
("hazlo más corto", "ponlo en una tabla") y el asistente lo aplica.

Sin marco, oscuro y pegado al orbe."""

from __future__ import annotations

import time

from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QGuiApplication, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from brand_loader import BrandLoader

WIDTH = 580
BG = "#171022"
INK = "#F4F1F7"
MUTED = "#A99FB8"
CYAN = "#4DD9E6"
PURPLE = "#875A7B"
PURPLE_HOT = "#9E6C90"
TEAL = "#017E84"
TEAL_HOT = "#029197"
GHOST = "#211936"
GHOST_HOT = "#2E2348"

BUTTON_CSS = """
QPushButton {{
    background: {bg};
    color: {fg};
    border: none;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 12px;
}}
QPushButton:hover {{ background: {hot}; }}
QPushButton:disabled {{ background: #1C1530; color: #6B6280; }}
"""

class ResultPanel(QWidget):
    paste_requested = pyqtSignal(str)
    action_requested = pyqtSignal(str, str)   # etiqueta de accion, texto actual
    free_requested = pyqtSignal(str, str)     # encargo escrito, texto actual
    cancel_requested = pyqtSignal()
    dismissed = pyqtSignal()

    def __init__(
        self,
        text: str,
        anchor: QPoint,
        action_labels: list[str],
        more_labels: list[str] | None = None,
    ):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self._busy_since = 0.0
        self._tick = QTimer(self)
        self._tick.setInterval(500)
        self._tick.timeout.connect(self._update_elapsed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        self.status = QLabel("Listo para pegar, o pule un poco más")
        self.status.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        layout.addWidget(self.status)

        self.bar = BrandLoader(orb_size=30)
        self.bar.hide()
        layout.addWidget(self.bar)

        self.editor = QTextEdit()
        self.editor.setPlainText(text)
        self.editor.setStyleSheet(
            f"QTextEdit {{ background: #0F0A16; color: {INK}; border: 1px solid #2A1F3D;"
            f" border-radius: 10px; padding: 10px; font-size: 14px; }}"
        )
        self.editor.setMinimumHeight(150)
        layout.addWidget(self.editor)

        self.action_buttons: list[QPushButton] = []
        actions_row = QHBoxLayout()
        actions_row.setSpacing(6)
        for label in action_labels:
            button = QPushButton(label)
            button.setStyleSheet(BUTTON_CSS.format(bg=PURPLE, hot=PURPLE_HOT, fg=INK))
            button.clicked.connect(
                lambda _, l=label: self.action_requested.emit(l, self.editor.toPlainText())
            )
            actions_row.addWidget(button)
            self.action_buttons.append(button)

        # El resto de modos, en un desplegable para no llenar el panel.
        self.more = QComboBox()
        self.more.addItem("Más modos...")
        for label in more_labels or []:
            if label not in action_labels:
                self.more.addItem(label)
        self.more.setStyleSheet(
            f"QComboBox {{ background: {GHOST}; color: {INK}; border: none;"
            f" border-radius: 8px; padding: 7px 10px; font-size: 12px; }}"
            f"QComboBox QAbstractItemView {{ background: {GHOST}; color: {INK};"
            f" selection-background-color: {PURPLE}; }}"
        )
        self.more.activated.connect(self._on_more)
        actions_row.addWidget(self.more)
        layout.addLayout(actions_row)

        self.ask = QLineEdit()
        self.ask.setPlaceholderText(
            "Pídele otra cosa y pulsa Enter: hazlo más corto, ponlo en una tabla..."
        )
        self.ask.setStyleSheet(
            f"QLineEdit {{ background: #0F0A16; color: {INK}; border: 1px solid #2A1F3D;"
            f" border-radius: 8px; padding: 8px 10px; font-size: 12px; }}"
        )
        self.ask.returnPressed.connect(self._on_ask)
        layout.addWidget(self.ask)

        bottom = QHBoxLayout()
        bottom.setSpacing(6)
        self.paste_button = QPushButton("Pegar donde estaba")
        self.paste_button.setStyleSheet(BUTTON_CSS.format(bg=TEAL, hot=TEAL_HOT, fg=INK))
        self.paste_button.clicked.connect(
            lambda: self.paste_requested.emit(self.editor.toPlainText())
        )
        bottom.addWidget(self.paste_button, 2)

        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setStyleSheet(BUTTON_CSS.format(bg=GHOST, hot=GHOST_HOT, fg=MUTED))
        self.cancel_button.clicked.connect(self.cancel_requested.emit)
        self.cancel_button.hide()
        bottom.addWidget(self.cancel_button, 1)

        self.close_button = QPushButton("Cerrar")
        self.close_button.setStyleSheet(BUTTON_CSS.format(bg=GHOST, hot=GHOST_HOT, fg=MUTED))
        self.close_button.clicked.connect(self._dismiss)
        bottom.addWidget(self.close_button, 1)
        layout.addLayout(bottom)

        self.resize(WIDTH, 360)
        self._place_near(anchor)
        self.editor.setFocus()

    # ------------------------------------------------------------------

    def set_text(self, text: str) -> None:
        self.editor.setPlainText(text)

    def text(self) -> str:
        return self.editor.toPlainText()

    def set_busy(self, label: str | None) -> None:
        """`label` con texto = trabajando; None = terminado."""
        if label:
            self._busy_since = time.monotonic()
            self.status.setText(label)
            self.status.setStyleSheet(f"color: {CYAN}; font-size: 12px;")
            self.bar.set_fraction(None)   # no sabemos cuánto tardará
            self.bar.start()
            self.cancel_button.show()
            self.paste_button.setEnabled(False)
            for button in self.action_buttons:
                button.setEnabled(False)
            self.more.setEnabled(False)
            self.ask.setEnabled(False)
            self._tick.start()
        else:
            self._tick.stop()
            self.bar.stop()
            self.cancel_button.hide()
            self.status.setText("Listo para pegar, o pule un poco más")
            self.status.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
            self.paste_button.setEnabled(True)
            for button in self.action_buttons:
                button.setEnabled(True)
            self.more.setEnabled(True)
            self.ask.setEnabled(True)

    def _on_more(self, index: int) -> None:
        if index <= 0:
            return
        label = self.more.itemText(index)
        self.more.setCurrentIndex(0)
        self.action_requested.emit(label, self.editor.toPlainText())

    def _on_ask(self) -> None:
        instruction = self.ask.text().strip()
        if not instruction:
            return
        self.ask.clear()
        self.free_requested.emit(instruction, self.editor.toPlainText())

    def _update_elapsed(self) -> None:
        """Contar los segundos en voz alta evita la duda de si se ha
        colgado: en CPU un texto largo puede tardar un minuto."""
        seconds = int(time.monotonic() - self._busy_since)
        base = self.status.text().split("  ·")[0]
        self.status.setText(f"{base}  ·  {seconds} s")

    # ------------------------------------------------------------------

    def _place_near(self, anchor: QPoint) -> None:
        screen = QGuiApplication.screenAt(anchor) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        x = anchor.x() - self.width() // 2
        y = anchor.y() - self.height() - 40
        x = max(area.left() + 10, min(x, area.right() - self.width() - 10))
        y = max(area.top() + 10, min(y, area.bottom() - self.height() - 10))
        self.move(x, y)

    def _dismiss(self) -> None:
        self.dismissed.emit()
        self.close()

    def keyPressEvent(self, event):  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self._dismiss()
        elif (
            event.key() == Qt.Key.Key_Return
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.paste_requested.emit(self.editor.toPlainText())

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0.0, 0.0, float(self.width()), float(self.height()), 16, 16)
        painter.fillPath(path, QColor(BG))
        painter.end()
