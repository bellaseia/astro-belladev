"""
log_panel.py
------------
Panel de log/consola que captura los prints del motor
y los muestra en la GUI, como Siril y SASpro.
"""

import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QHBoxLayout,
    QPushButton, QLabel,
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QTextCursor, QColor


class LogSignal(QObject):
    """Señal para enviar texto al log desde cualquier hilo."""
    message = pyqtSignal(str)


class StdoutRedirector:
    """Redirige stdout/stderr al panel de log."""

    def __init__(self, signal, original):
        self.signal = signal
        self.original = original

    def write(self, text):
        if text.strip():
            self.signal.message.emit(text)
        if self.original:
            self.original.write(text)

    def flush(self):
        if self.original:
            self.original.flush()


class LogPanel(QWidget):
    """Panel de consola/log integrado en la GUI."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(80)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QHBoxLayout()
        header.setContentsMargins(8, 2, 8, 2)

        title = QLabel("Consola")
        title.setStyleSheet(
            "font-weight: 600; font-size: 12px; color: #8892A8;"
        )
        header.addWidget(title)
        header.addStretch()

        clear_btn = QPushButton("Limpiar")
        clear_btn.setFixedHeight(20)
        clear_btn.setStyleSheet(
            "font-size: 11px; padding: 1px 8px;"
        )
        clear_btn.clicked.connect(self._clear)
        header.addWidget(clear_btn)

        layout.addLayout(header)

        # Text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #0A0C14;
                color: #A0B0C0;
                border: none;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                padding: 4px;
            }
        """)
        layout.addWidget(self.log_text)

        # Setup redirect
        self._signal = LogSignal()
        self._signal.message.connect(self._append)
        self._stdout_redirect = StdoutRedirector(
            self._signal, sys.stdout
        )
        self._stderr_redirect = StdoutRedirector(
            self._signal, sys.stderr
        )
        sys.stdout = self._stdout_redirect
        sys.stderr = self._stderr_redirect

    def _append(self, text):
        """Añade texto al log con colores por tipo."""
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        text_stripped = text.strip()
        if not text_stripped:
            return

        # Color por contenido
        if any(w in text_stripped.lower() for w in
               ["error", "err:", "traceback", "exception"]):
            color = "#D94452"
        elif any(w in text_stripped.lower() for w in
                 ["aviso", "warning", "warn"]):
            color = "#E6A817"
        elif any(w in text_stripped.lower() for w in
                 ["ok", "listo", "completado", "done"]):
            color = "#4CAF6E"
        elif text_stripped.startswith("["):
            color = "#4A9BD9"
        else:
            color = "#A0B0C0"

        cursor.insertHtml(
            f'<span style="color:{color};">{text_stripped}</span><br>'
        )

        self.log_text.setTextCursor(cursor)
        self.log_text.ensureCursorVisible()

    def log(self, text, color=None):
        """API directa para escribir al log."""
        if color:
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertHtml(
                f'<span style="color:{color};">{text}</span><br>'
            )
            self.log_text.setTextCursor(cursor)
            self.log_text.ensureCursorVisible()
        else:
            self._append(text)

    def _clear(self):
        self.log_text.clear()

    def restore_stdout(self):
        """Restaura stdout/stderr original al cerrar."""
        sys.stdout = self._stdout_redirect.original
        sys.stderr = self._stderr_redirect.original
