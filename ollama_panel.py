"""Panel que aparece cuando la IA local no responde: explica que falta,
lo instala con un boton y enseña el progreso de la descarga del modelo.

Este flujo existia en la burbuja de tkinter y se perdio al migrar al
orbe. Sin el, a quien no es tecnico le aparece un error y se queda sin
saber que hacer."""

from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QGuiApplication, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from brand_loader import BrandLoader

WIDTH = 470
BG = "#171022"
INK = "#F4F1F7"
MUTED = "#A99FB8"
CYAN = "#4DD9E6"
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
    padding: 9px 13px;
    font-size: 12px;
}}
QPushButton:hover {{ background: {hot}; }}
QPushButton:disabled {{ background: #1C1530; color: #6B6280; }}
"""

class OllamaPanel(QWidget):
    install_requested = pyqtSignal()
    retry_requested = pyqtSignal()
    dismissed = pyqtSignal()

    def __init__(self, anchor: QPoint, model: str, host: str, command: str):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel("La IA local no está respondiendo")
        title.setStyleSheet(f"color: {INK}; font-size: 15px; font-weight: 600;")
        layout.addWidget(title)

        explain = QLabel(
            f"Vozdoo usa Ollama en tu propio ordenador para pulir textos: nada "
            f"sale de aquí. Ahora mismo no responde en {host}, o le falta el "
            f"modelo {model}."
        )
        explain.setWordWrap(True)
        explain.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        layout.addWidget(explain)

        manual = QLabel("Si prefieres hacerlo tú, en una terminal:")
        manual.setStyleSheet(f"color: {MUTED}; font-size: 11px;")
        layout.addWidget(manual)

        self.command = QLineEdit(command)
        self.command.setReadOnly(True)
        self.command.setStyleSheet(
            f"QLineEdit {{ background: #0F0A16; color: {CYAN}; border: 1px solid #2A1F3D;"
            f" border-radius: 8px; padding: 8px; font-family: monospace; font-size: 11px; }}"
        )
        layout.addWidget(self.command)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setStyleSheet(f"color: {CYAN}; font-size: 12px;")
        self.status.hide()
        layout.addWidget(self.status)

        self.bar = BrandLoader(orb_size=30)
        self.bar.hide()
        layout.addWidget(self.bar)

        row = QHBoxLayout()
        row.setSpacing(6)
        self.install_button = QPushButton("Instalarlo automáticamente")
        self.install_button.setStyleSheet(BUTTON_CSS.format(bg=TEAL, hot=TEAL_HOT, fg=INK))
        self.install_button.clicked.connect(self._on_install)
        row.addWidget(self.install_button, 2)

        self.retry_button = QPushButton("Reintentar")
        self.retry_button.setStyleSheet(BUTTON_CSS.format(bg=GHOST, hot=GHOST_HOT, fg=MUTED))
        self.retry_button.clicked.connect(self.retry_requested.emit)
        row.addWidget(self.retry_button, 1)

        close_button = QPushButton("Cerrar")
        close_button.setStyleSheet(BUTTON_CSS.format(bg=GHOST, hot=GHOST_HOT, fg=MUTED))
        close_button.clicked.connect(self._dismiss)
        row.addWidget(close_button, 1)
        layout.addLayout(row)

        self.resize(WIDTH, 260)
        self._place_near(anchor)

    # ------------------------------------------------------------------

    def _on_install(self) -> None:
        self.install_button.setEnabled(False)
        self.status.show()
        self.status.setText("Preparando la instalación...")
        self.bar.set_fraction(None)
        self.bar.start()
        self.install_requested.emit()

    def set_status(self, text: str) -> None:
        self.status.show()
        self.status.setText(text)

    def set_fraction(self, fraction: float) -> None:
        """Descarga con porcentaje real cuando Ollama lo informa; mientras
        no lo informa, la barra se queda indeterminada."""
        self.bar.set_fraction(None if fraction < 0 else fraction)

    def finish(self, message: str) -> None:
        self.bar.stop()
        self.install_button.setEnabled(True)
        self.set_status(message)

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

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0.0, 0.0, float(self.width()), float(self.height()), 16, 16)
        painter.fillPath(path, QColor(BG))
        painter.end()
