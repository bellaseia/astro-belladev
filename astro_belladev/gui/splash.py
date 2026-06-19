"""
splash.py
---------
Splash screen con logo BellaDev al arrancar.
"""

from PyQt6.QtWidgets import QSplashScreen, QApplication
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QLinearGradient
from PyQt6.QtCore import Qt, QRect, QTimer


def create_splash():
    """Crea un splash screen con el branding BellaDev."""
    width, height = 520, 320

    pixmap = QPixmap(width, height)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    grad = QLinearGradient(0, 0, width, height)
    grad.setColorAt(0.0, QColor(12, 14, 28))
    grad.setColorAt(0.5, QColor(18, 22, 40))
    grad.setColorAt(1.0, QColor(10, 12, 24))
    painter.fillRect(0, 0, width, height, grad)

    accent = QColor(74, 127, 181)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(accent)
    painter.setOpacity(0.08)
    painter.drawEllipse(-80, -80, 300, 300)
    painter.drawEllipse(width - 150, height - 150, 280, 280)
    painter.setOpacity(1.0)

    painter.setPen(accent)
    painter.drawLine(40, 100, width - 40, 100)
    painter.setOpacity(0.3)
    painter.drawLine(40, 102, width - 40, 102)
    painter.setOpacity(1.0)

    title_font = QFont("Segoe UI", 32, QFont.Weight.Bold)
    title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4)
    painter.setFont(title_font)
    painter.setPen(QColor(230, 236, 242))
    painter.drawText(QRect(0, 30, width, 60),
                     Qt.AlignmentFlag.AlignCenter, "ASTRO")

    dev_font = QFont("Segoe UI", 28, QFont.Weight.Light)
    dev_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 6)
    painter.setFont(dev_font)
    painter.setPen(accent)
    painter.drawText(QRect(0, 65, width, 40),
                     Qt.AlignmentFlag.AlignCenter, "BELLADEV")

    sub_font = QFont("Segoe UI", 10)
    painter.setFont(sub_font)
    painter.setPen(QColor(136, 146, 168))
    painter.drawText(QRect(0, 115, width, 25),
                     Qt.AlignmentFlag.AlignCenter,
                     "Astrophotography Processing Suite")

    info_font = QFont("Segoe UI", 9)
    painter.setFont(info_font)
    painter.setPen(QColor(100, 110, 130))

    features = [
        "62 modules  |  102 actions  |  10 scripts  |  158 catalog",
        "AI Denoise  |  Plate Solving  |  Narrowband",
        "Auto & Expert mode  |  belladev.es",
    ]
    y = 165
    for line in features:
        painter.drawText(QRect(0, y, width, 20),
                         Qt.AlignmentFlag.AlignCenter, line)
        y += 20

    ver_font = QFont("Segoe UI", 8)
    painter.setFont(ver_font)
    painter.setPen(QColor(74, 127, 181, 180))
    painter.drawText(QRect(0, height - 35, width, 20),
                     Qt.AlignmentFlag.AlignCenter,
                     "v1.1.0  |  BellaDev  |  2026")

    painter.setPen(accent)
    painter.setOpacity(0.5)
    painter.drawRect(0, 0, width - 1, height - 1)
    painter.setOpacity(1.0)

    # Loading bar
    bar_y = height - 12
    bar_h = 3
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(30, 35, 55))
    painter.drawRoundedRect(40, bar_y, width - 80, bar_h, 1, 1)
    painter.setBrush(accent)
    painter.drawRoundedRect(40, bar_y, (width - 80) // 2, bar_h, 1, 1)

    painter.end()

    splash = QSplashScreen(pixmap)
    splash.setWindowFlags(
        Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint
    )
    return splash
