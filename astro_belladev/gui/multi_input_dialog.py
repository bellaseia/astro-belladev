"""
multi_input_dialog.py
---------------------
Dialogos para acciones que necesitan multiples inputs:
HDR, Mosaico, PixelMath, Narrowband, Batch.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QLineEdit, QTextEdit,
    QGroupBox, QFormLayout, QComboBox, QMessageBox,
    QDoubleSpinBox,
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
import numpy as np


class HDRDialog(QDialog):
    """Combina exposicion corta + larga."""

    def __init__(self, current_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HDR Multiscale")
        self.setMinimumWidth(500)
        self.result = None
        self.current = current_data

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Selecciona la imagen de exposicion corta.\n"
            "La imagen actual se usa como exposicion larga."
        ))

        row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Imagen corta...")
        self.path_edit.setStyleSheet(
            "background:#1A1E30;color:#E0E4EC;"
            "border:1px solid #2A2F45;padding:6px;"
        )
        row.addWidget(self.path_edit)
        btn = QPushButton("...")
        btn.setFixedWidth(40)
        btn.clicked.connect(self._browse)
        row.addWidget(btn)
        layout.addLayout(row)

        self.blend_spin = QDoubleSpinBox()
        self.blend_spin.setRange(0.01, 0.5)
        self.blend_spin.setValue(0.1)
        fl = QFormLayout()
        fl.addRow("Blend width:", self.blend_spin)
        layout.addLayout(fl)

        bl = QHBoxLayout()
        bl.addStretch()
        QPushButton("Cancelar", clicked=self.reject)
        bl.addWidget(QPushButton("Cancelar", clicked=self.reject))
        ok = QPushButton("Combinar")
        ok.setObjectName("primary")
        ok.clicked.connect(self._combine)
        bl.addWidget(ok)
        layout.addLayout(bl)

    def _browse(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "Imagen corta", "",
            "Astro (*.fits *.fit *.tif *.tiff *.png);;All (*)",
        )
        if p:
            self.path_edit.setText(p)

    def _combine(self):
        path = self.path_edit.text().strip()
        if not path:
            return
        try:
            from ..io_fits import load_image
            from ..mosaic import hdr_combine
            short, _ = load_image(path)
            self.result = hdr_combine(
                short, self.current,
                blend_width=self.blend_spin.value(),
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def get_result(self):
        return self.result


class PixelMathDialog(QDialog):
    """Editor de expresiones PixelMath."""

    def __init__(self, current_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PixelMath")
        self.setMinimumSize(550, 400)
        self.result = None
        self.current = current_data

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Escribe una expresion. 'img' = imagen actual.\n"
            "Funciones: min, max, clip, sqrt, log, normalize, "
            "where, abs, mean, median"
        ))

        self.expr_edit = QTextEdit()
        self.expr_edit.setFont(QFont("Consolas", 13))
        self.expr_edit.setPlainText("normalize(img)")
        self.expr_edit.setMaximumHeight(100)
        self.expr_edit.setStyleSheet(
            "background:#1A1E30;color:#E0E4EC;"
            "border:1px solid #2A2F45;"
        )
        layout.addWidget(self.expr_edit)

        # Presets
        presets = QGroupBox("Presets")
        pl = QVBoxLayout(presets)
        for name, expr in [
            ("Normalizar (0-1)", "normalize(img)"),
            ("Invertir", "invert(img)"),
            ("Aumentar contraste", "clip((img - median(img)) * 2 + 0.5, 0, 1)"),
            ("Luminancia", "(img[:,:,0] + img[:,:,1] + img[:,:,2]) / 3" if current_data.ndim == 3 else "img"),
            ("Gamma 0.5", "power(normalize(img), 0.5)"),
        ]:
            b = QPushButton(name)
            b.clicked.connect(
                lambda ch, e=expr: self.expr_edit.setPlainText(e)
            )
            pl.addWidget(b)
        layout.addWidget(presets)

        bl = QHBoxLayout()
        bl.addStretch()
        bl.addWidget(QPushButton("Cancelar", clicked=self.reject))
        ok = QPushButton("Ejecutar")
        ok.setObjectName("primary")
        ok.clicked.connect(self._execute)
        bl.addWidget(ok)
        layout.addLayout(bl)

    def _execute(self):
        expr = self.expr_edit.toPlainText().strip()
        if not expr:
            return
        try:
            from ..pixelmath import PixelMathEngine
            engine = PixelMathEngine()
            engine.set_image("img", self.current)
            if self.current.ndim == 3:
                engine.set_image("R", self.current[..., 0])
                engine.set_image("G", self.current[..., 1])
                engine.set_image("B", self.current[..., 2])
            engine.set_image("L", self.current.mean(axis=-1)
                             if self.current.ndim == 3
                             else self.current)
            self.result = engine.evaluate(expr)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def get_result(self):
        return self.result


class NarrowbandDialog(QDialog):
    """Combinacion personalizada de canales narrowband."""

    def __init__(self, current_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Narrowband - Combinacion personalizada")
        self.setMinimumWidth(500)
        self.result = None
        self.current = current_data

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            "Carga imagenes Ha, OIII y/o SII y selecciona "
            "una paleta de color."
        ))

        style = ("background:#1A1E30;color:#E0E4EC;"
                 "border:1px solid #2A2F45;padding:6px;")

        self.inputs = {}
        for ch in ["Ha", "OIII", "SII"]:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{ch}:"))
            edit = QLineEdit()
            edit.setStyleSheet(style)
            edit.setPlaceholderText(f"Imagen {ch} (opcional)")
            row.addWidget(edit)
            btn = QPushButton("...")
            btn.setFixedWidth(40)
            btn.clicked.connect(
                lambda checked, e=edit: self._browse(e)
            )
            row.addWidget(btn)
            layout.addLayout(row)
            self.inputs[ch] = edit

        self.palette_combo = QComboBox()
        self.palette_combo.addItems([
            "SHO (Hubble)", "HOO (Bicolor)",
            "HOS", "Natural",
        ])
        fl = QFormLayout()
        fl.addRow("Paleta:", self.palette_combo)
        layout.addLayout(fl)

        bl = QHBoxLayout()
        bl.addStretch()
        bl.addWidget(QPushButton("Cancelar", clicked=self.reject))
        ok = QPushButton("Combinar")
        ok.setObjectName("primary")
        ok.clicked.connect(self._combine)
        bl.addWidget(ok)
        layout.addLayout(bl)

    def _browse(self, edit):
        p, _ = QFileDialog.getOpenFileName(
            self, "Imagen", "",
            "Astro (*.fits *.fit *.tif *.tiff);;All (*)",
        )
        if p:
            edit.setText(p)

    def _combine(self):
        try:
            from ..io_fits import load_image
            from ..narrowband import combine_palette

            channels = {}
            for ch, edit in self.inputs.items():
                path = edit.text().strip()
                if path:
                    data, _ = load_image(path)
                    if data.ndim == 3:
                        data = data.mean(axis=-1)
                    channels[ch] = data

            if len(channels) < 2:
                QMessageBox.warning(
                    self, "Faltan canales",
                    "Necesitas al menos 2 canales (Ha + OIII)",
                )
                return

            palette_map = {
                "SHO (Hubble)": "SHO",
                "HOO (Bicolor)": "HOO",
                "HOS": "HOS",
                "Natural": "natural",
            }
            palette = palette_map.get(
                self.palette_combo.currentText(), "SHO"
            )
            self.result = combine_palette(channels, palette)
            self.accept()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def get_result(self):
        return self.result
