"""
histogram_widget.py
-------------------
Widget de histograma RGB + Luminancia.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtCore import Qt, QRect
import numpy as np


class HistogramWidget(QWidget):
    """Histograma interactivo RGB + Luminancia."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(100)
        self.setMaximumHeight(180)

        self._hist_data = None
        self._show_channels = {"R": True, "G": True, "B": True, "L": True}

        self.setStyleSheet("background-color: #0a0a1a;")

    def update_histogram(self, data, bins=256):
        """Calcula el histograma de la imagen."""
        from ..curves import get_histogram
        self._hist_data = get_histogram(data, bins=bins)
        self.update()

    def paintEvent(self, event):
        """Dibuja el histograma."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        bg = self.palette().window().color()
        painter.fillRect(0, 0, w, h, bg)

        if self._hist_data is None:
            painter.setPen(QColor(100, 100, 100))
            painter.drawText(QRect(0, 0, w, h),
                             Qt.AlignmentFlag.AlignCenter,
                             "Sin histograma")
            painter.end()
            return

        channel_colors = {
            "R": QColor(255, 80, 80, 150),
            "G": QColor(80, 255, 80, 150),
            "B": QColor(80, 80, 255, 150),
            "L": QColor(200, 200, 200, 100),
        }

        margin = 5
        plot_w = w - margin * 2
        plot_h = h - margin * 2

        all_max = 1
        for ch in ["R", "G", "B", "L"]:
            if ch in self._hist_data and self._show_channels.get(ch, False):
                counts = self._hist_data[ch]
                trimmed = np.sort(counts)[:-5] if len(counts) > 5 else counts
                all_max = max(all_max, np.max(trimmed) if len(trimmed) > 0 else 1)

        for ch in ["L", "R", "G", "B"]:
            if ch not in self._hist_data or not self._show_channels.get(ch, False):
                continue

            counts = self._hist_data[ch]
            color = channel_colors[ch]
            pen = QPen(color, 1)
            painter.setPen(pen)

            n_bins = len(counts)
            for i in range(n_bins):
                x = margin + int(i / n_bins * plot_w)
                bar_h = int(counts[i] / all_max * plot_h)
                bar_h = min(bar_h, plot_h)

                painter.drawLine(x, h - margin, x, h - margin - bar_h)

        painter.end()
