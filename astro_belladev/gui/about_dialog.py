"""
about_dialog.py
---------------
Dialogo About con branding BellaDev.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class AboutDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Astro BellaDev")
        self.setFixedSize(420, 380)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(30, 30, 30, 20)

        title = QLabel("ASTRO BELLADEV")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setStyleSheet("color: #4A7FB5; letter-spacing: 4px;")
        layout.addWidget(title)

        version = QLabel("v1.1.0")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setObjectName("subtitle")
        layout.addWidget(version)

        desc = QLabel(
            "Astrophotography Processing Suite\n\n"
            "62 modules | 102 actions | 10 scripts | 158 catalog\n"
            "AI Denoise | Plate Solving | Narrowband\n"
            "Auto & Expert mode\n\n"
            "Developed by BellaDev\n"
            "belladev.es"
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        layout.addStretch()

        techs = QLabel(
            "Python | PyQt6 | NumPy | OpenCV | AstroPy\n"
            "rawpy | tifffile | SciPy | astroalign"
        )
        techs.setAlignment(Qt.AlignmentFlag.AlignCenter)
        techs.setObjectName("subtitle")
        layout.addWidget(techs)

        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
