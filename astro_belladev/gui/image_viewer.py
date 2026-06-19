"""
image_viewer.py
---------------
Preview de imagen con zoom al cursor, pan con arrastre,
canales RGB/L, crosshair y drag & drop.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton,
)
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (
    QImage, QPixmap, QPainter, QWheelEvent,
    QMouseEvent, QColor, QPen, QFont,
    QDragEnterEvent, QDropEvent, QTransform,
)
import numpy as np


class ImageCanvas(QWidget):
    """Canvas con zoom al cursor, pan y crosshair."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._pixmap = None
        self._zoom = 1.0
        self._offset = QPointF(0, 0)
        self._dragging = False
        self._drag_start = QPointF()
        self._drag_offset_start = QPointF()
        self._mouse_pos = None
        self._image_shape = None
        self._show_crosshair = True

    def set_pixmap(self, pixmap, shape):
        self._pixmap = pixmap
        self._image_shape = shape
        self.update()

    def fit_to_window(self):
        if self._pixmap is None:
            return
        pw = self._pixmap.width()
        ph = self._pixmap.height()
        if pw == 0 or ph == 0:
            return
        cw = self.width()
        ch = self.height()
        self._zoom = min(cw / pw, ch / ph)
        self._offset = QPointF(0, 0)
        self.update()

    def zoom_at(self, pos, factor):
        """Zoom centrado en el punto del cursor."""
        old_zoom = self._zoom
        self._zoom = max(0.05, min(self._zoom * factor, 20.0))

        # Ajustar offset para que el punto bajo el cursor no se mueva
        ratio = self._zoom / old_zoom
        self._offset = pos - ratio * (pos - self._offset)
        self.update()

    def _image_rect(self):
        """Rectangulo de la imagen escalada en coordenadas del widget."""
        if self._pixmap is None:
            return QRectF()
        pw = self._pixmap.width() * self._zoom
        ph = self._pixmap.height() * self._zoom
        cx = self.width() / 2 + self._offset.x()
        cy = self.height() / 2 + self._offset.y()
        return QRectF(cx - pw / 2, cy - ph / 2, pw, ph)

    def _widget_to_image(self, pos):
        """Convierte coordenadas del widget a coordenadas de la imagen."""
        rect = self._image_rect()
        if rect.width() == 0 or rect.height() == 0:
            return None
        x = (pos.x() - rect.x()) / rect.width()
        y = (pos.y() - rect.y()) / rect.height()
        if 0 <= x <= 1 and 0 <= y <= 1 and self._image_shape:
            ix = int(x * self._image_shape[1])
            iy = int(y * self._image_shape[0])
            return ix, iy
        return None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Fondo segun tema
        bg = self.palette().window().color()
        painter.fillRect(self.rect(), bg)

        if self._pixmap is None:
            self._draw_welcome(painter)
            painter.end()
            return

        # Dibujar imagen escalada
        rect = self._image_rect()
        painter.drawPixmap(rect.toRect(), self._pixmap)

        # Crosshair + coordenadas
        if self._mouse_pos and self._show_crosshair:
            mx = self._mouse_pos.x()
            my = self._mouse_pos.y()

            pen = QPen(QColor(74, 127, 181, 60))
            pen.setWidth(1)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawLine(int(mx), 0, int(mx), self.height())
            painter.drawLine(0, int(my), self.width(), int(my))

            coords = self._widget_to_image(self._mouse_pos)
            if coords:
                ix, iy = coords
                text = f"({ix}, {iy})"
                font = QFont("Segoe UI", 10)
                painter.setFont(font)

                fm = painter.fontMetrics()
                tw = fm.horizontalAdvance(text) + 8
                th = fm.height() + 4

                tx = int(mx) + 14
                ty = int(my) - 14

                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(15, 18, 30, 210))
                painter.drawRoundedRect(tx, ty - th, tw, th, 3, 3)

                painter.setPen(QColor(180, 190, 210))
                painter.drawText(tx + 4, ty - 4, text)

        painter.end()

    def mousePressEvent(self, event):
        if event.button() in (
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.MiddleButton,
        ):
            self._dragging = True
            self._drag_start = event.position()
            self._drag_offset_start = QPointF(self._offset)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        self._mouse_pos = event.position()
        if self._dragging:
            delta = event.position() - self._drag_start
            self._offset = self._drag_offset_start + delta
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() in (
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.MiddleButton,
        ):
            self._dragging = False
            self.setCursor(Qt.CursorShape.CrossCursor)

    def wheelEvent(self, event):
        pos = event.position()
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 0.87
        self.zoom_at(pos, factor)

    def _draw_welcome(self, painter):
        """Dibuja pantalla de bienvenida con estrellas."""
        import random
        w = self.width()
        h = self.height()

        # Fondo con gradiente sutil
        from PyQt6.QtGui import QLinearGradient
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0.0, QColor(8, 10, 20))
        grad.setColorAt(0.3, QColor(10, 14, 28))
        grad.setColorAt(0.7, QColor(12, 16, 32))
        grad.setColorAt(1.0, QColor(8, 10, 22))
        painter.fillRect(self.rect(), grad)

        # Estrellas (seed fijo para que no parpadeen)
        random.seed(42)
        for _ in range(200):
            x = random.randint(0, w)
            y = random.randint(0, h)
            size = random.choice([1, 1, 1, 1, 2, 2, 3])
            alpha = random.randint(40, 200)
            temp = random.choice([
                QColor(200, 210, 255, alpha),
                QColor(255, 220, 180, alpha),
                QColor(180, 200, 255, alpha),
                QColor(255, 255, 240, alpha),
            ])
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(temp)
            painter.drawEllipse(x, y, size, size)

        # Unas estrellas mas brillantes con halo
        for _ in range(15):
            x = random.randint(20, w - 20)
            y = random.randint(20, h - 20)
            painter.setBrush(QColor(74, 127, 181, 15))
            painter.drawEllipse(x - 6, y - 6, 12, 12)
            painter.setBrush(QColor(200, 220, 255, 180))
            painter.drawEllipse(x - 1, y - 1, 3, 3)

        # Nebulosa sutil (mancha difusa)
        cx, cy = int(w * 0.6), int(h * 0.55)
        for r in range(80, 0, -2):
            alpha = int(3 * (80 - r) / 80)
            painter.setBrush(QColor(180, 60, 80, alpha))
            painter.drawEllipse(
                cx - r, cy - int(r * 0.7),
                r * 2, int(r * 1.4),
            )

        # Logo
        painter.setOpacity(1.0)
        font_title = QFont("Segoe UI", 28, QFont.Weight.Bold)
        font_title.setLetterSpacing(
            QFont.SpacingType.AbsoluteSpacing, 5
        )
        painter.setFont(font_title)
        painter.setPen(QColor(74, 127, 181, 200))
        painter.drawText(
            QRectF(0, h * 0.3, w, 50),
            Qt.AlignmentFlag.AlignCenter,
            "ASTRO BELLADEV",
        )

        # Subtitulo
        font_sub = QFont("Segoe UI", 12)
        painter.setFont(font_sub)
        painter.setPen(QColor(130, 142, 168, 180))
        painter.drawText(
            QRectF(0, h * 0.3 + 45, w, 30),
            Qt.AlignmentFlag.AlignCenter,
            "Astrophotography Processing Suite",
        )

        # Instrucciones
        font_hint = QFont("Segoe UI", 11)
        painter.setFont(font_hint)
        painter.setPen(QColor(100, 112, 138, 150))
        painter.drawText(
            QRectF(0, h * 0.3 + 85, w, 25),
            Qt.AlignmentFlag.AlignCenter,
            "Arrastra una imagen o pulsa Ctrl+O para abrir",
        )
        painter.drawText(
            QRectF(0, h * 0.3 + 108, w, 25),
            Qt.AlignmentFlag.AlignCenter,
            "Pre-procesamiento > Pipeline completo para apilar",
        )

    def enterEvent(self, event):
        self.setCursor(Qt.CursorShape.CrossCursor)

    def leaveEvent(self, event):
        self._mouse_pos = None
        self.update()


class ImageViewer(QWidget):
    """Preview con zoom al cursor, pan y drag&drop."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._image = None
        self._channel = "RGB"

        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # Controles
        controls = QHBoxLayout()
        controls.setContentsMargins(4, 2, 4, 2)

        self.channel_buttons = {}
        for ch in ["RGB", "R", "G", "B", "L"]:
            btn = QPushButton(ch)
            btn.setFixedSize(42, 28)
            btn.setCheckable(True)
            btn.setChecked(ch == "RGB")
            ch_name = ch
            btn.clicked.connect(
                lambda checked, c=ch_name: self._set_channel(c)
            )
            color_map = {
                "RGB": "#8892A8", "R": "#D94452",
                "G": "#4CAF6E", "B": "#4A9BD9", "L": "#B0B8C8",
            }
            c = color_map.get(ch, "#888")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {c};
                    border: 1px solid transparent;
                    border-radius: 4px; font-size: 13px;
                    font-weight: 600;
                }}
                QPushButton:checked {{
                    background-color: rgba({self._hex_rgb(c)}, 0.2);
                    border-color: {c};
                }}
                QPushButton:hover:!checked {{
                    background-color: rgba({self._hex_rgb(c)}, 0.1);
                }}
            """)
            controls.addWidget(btn)
            self.channel_buttons[ch] = btn

        controls.addStretch()

        for symbol, factor in [("-", 0.8), ("+", 1.25)]:
            btn = QPushButton(symbol)
            btn.setFixedSize(36, 28)
            f = factor
            btn.clicked.connect(
                lambda ch, fa=f: self._zoom_center(fa)
            )
            controls.addWidget(btn)

        fit_btn = QPushButton("Fit")
        fit_btn.setFixedSize(42, 28)
        fit_btn.clicked.connect(self._fit_to_window)
        controls.addWidget(fit_btn)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(50)
        self.zoom_label.setStyleSheet(
            "font-size: 13px; color: #8892A8;"
        )
        controls.addWidget(self.zoom_label)

        layout.addLayout(controls)

        # Canvas
        self._canvas = ImageCanvas(self)
        layout.addWidget(self._canvas, stretch=1)

    def set_image(self, data):
        self._image = data.copy()
        self._render()

    def _set_channel(self, channel):
        self._channel = channel
        for ch, btn in self.channel_buttons.items():
            btn.setChecked(ch == channel)
        if self._image is not None:
            self._render()

    def _render(self):
        if self._image is None:
            return

        data = self._image
        if data.ndim == 3 and self._channel != "RGB":
            ch_map = {"R": 0, "G": 1, "B": 2}
            if self._channel == "L":
                display = data.mean(axis=-1)
            else:
                display = data[..., ch_map.get(self._channel, 0)]
        elif data.ndim == 2:
            display = data
        else:
            display = data

        dmin = np.min(display)
        dmax = np.max(display)
        if dmax > dmin:
            normalized = ((display - dmin) / (dmax - dmin) * 255)
        else:
            normalized = np.zeros_like(display)

        normalized = np.clip(normalized, 0, 255).astype(np.uint8)
        h, w = normalized.shape[:2]

        if normalized.ndim == 2:
            qimg = QImage(
                normalized.data, w, h, w,
                QImage.Format.Format_Grayscale8,
            )
        else:
            rgb = np.ascontiguousarray(normalized)
            qimg = QImage(
                rgb.data, w, h, w * 3,
                QImage.Format.Format_RGB888,
            )

        pixmap = QPixmap.fromImage(qimg)
        self._canvas.set_pixmap(pixmap, data.shape)
        self.zoom_label.setText(
            f"{int(self._canvas._zoom * 100)}%"
        )

    def _zoom_center(self, factor):
        center = QPointF(
            self._canvas.width() / 2,
            self._canvas.height() / 2,
        )
        self._canvas.zoom_at(center, factor)
        self.zoom_label.setText(
            f"{int(self._canvas._zoom * 100)}%"
        )

    def _fit_to_window(self):
        self._canvas.fit_to_window()
        self.zoom_label.setText(
            f"{int(self._canvas._zoom * 100)}%"
        )

    def wheelEvent(self, event):
        # Delegado al canvas
        pass

    # Drag & Drop
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            main = self.parent()
            while main and not hasattr(main, '_open_dropped_file'):
                main = main.parent()
            if main:
                main._open_dropped_file(path)

    def _hex_rgb(self, hex_color):
        h = hex_color.lstrip('#')
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"{r}, {g}, {b}"
