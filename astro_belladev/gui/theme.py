"""
theme.py
--------
Sistema de temas de Astro BellaDev.

Dos temas profesionales:
- Oscuro (BellaDev Dark): azul acero metalico, fondo oscuro,
  acentos en #4A7FB5 (azul BellaDev). Para sesiones nocturnas.
- Claro (BellaDev Light): fondo claro, texto oscuro,
  acentos en #2D5F8A. Para uso diurno.

Los colores estan extraidos del logo corporativo de BellaDev:
azul metalico (#4A7FB5), gris acero (#8899AA), blanco perla (#E8ECF0).
"""

from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtWidgets import QApplication


# === Paleta de colores BellaDev ===
BELLADEV_BLUE = "#4A7FB5"
BELLADEV_BLUE_DARK = "#2D5F8A"
BELLADEV_BLUE_LIGHT = "#6BA3D6"
BELLADEV_STEEL = "#8899AA"
BELLADEV_PEARL = "#E8ECF0"
BELLADEV_ACCENT = "#5B9BD5"
BELLADEV_SUCCESS = "#4CAF6E"
BELLADEV_WARNING = "#E6A817"
BELLADEV_ERROR = "#D94452"


THEMES = {
    "dark": {
        "name": "BellaDev Dark",
        "window_bg": "#12141F",
        "panel_bg": "#181B28",
        "surface": "#1E2233",
        "surface_hover": "#262B40",
        "surface_active": "#2D3350",
        "border": "#2A2F45",
        "border_light": "#353B55",
        "text_primary": "#E0E4EC",
        "text_secondary": "#8892A8",
        "text_disabled": "#4A5068",
        "accent": BELLADEV_BLUE,
        "accent_hover": BELLADEV_BLUE_LIGHT,
        "accent_dark": BELLADEV_BLUE_DARK,
        "header_bg": "#141726",
        "toolbar_bg": "#161929",
        "input_bg": "#1A1E30",
        "scrollbar": "#2A3048",
        "scrollbar_hover": "#3A4060",
        "canvas_bg": "#0A0C14",
        "histogram_bg": "#0D0F18",
        "success": BELLADEV_SUCCESS,
        "warning": BELLADEV_WARNING,
        "error": BELLADEV_ERROR,
        "shadow": "rgba(0, 0, 0, 0.4)",
    },
    "light": {
        "name": "BellaDev Light",
        "window_bg": "#F0F2F5",
        "panel_bg": "#FFFFFF",
        "surface": "#F7F8FA",
        "surface_hover": "#EDF0F5",
        "surface_active": "#E0E5EE",
        "border": "#D0D5E0",
        "border_light": "#E0E4EC",
        "text_primary": "#1A1E2E",
        "text_secondary": "#5A6378",
        "text_disabled": "#A0A8B8",
        "accent": BELLADEV_BLUE_DARK,
        "accent_hover": BELLADEV_BLUE,
        "accent_dark": "#1E4A6E",
        "header_bg": "#FFFFFF",
        "toolbar_bg": "#F5F6F8",
        "input_bg": "#FFFFFF",
        "scrollbar": "#C8CDD8",
        "scrollbar_hover": "#A8B0C0",
        "canvas_bg": "#E8EAEF",
        "histogram_bg": "#F0F2F5",
        "success": "#3A8F5C",
        "warning": "#C4900A",
        "error": "#C0392B",
        "shadow": "rgba(0, 0, 0, 0.08)",
    },
}


def get_theme(name="dark"):
    return THEMES.get(name, THEMES["dark"])


def build_stylesheet(theme_name="dark"):
    """Genera la hoja de estilos completa para un tema."""
    t = get_theme(theme_name)

    return f"""
    /* === GLOBAL === */
    QMainWindow {{
        background-color: {t['window_bg']};
    }}

    QWidget {{
        color: {t['text_primary']};
        font-family: 'Segoe UI', 'Inter', 'SF Pro Display', sans-serif;
        font-size: 14px;
    }}

    /* === MENU BAR === */
    QMenuBar {{
        background-color: {t['header_bg']};
        color: {t['text_primary']};
        border-bottom: 1px solid {t['border']};
        padding: 2px 0;
        font-size: 12px;
    }}
    QMenuBar::item {{
        padding: 5px 12px;
        border-radius: 4px;
        margin: 1px 2px;
    }}
    QMenuBar::item:selected {{
        background-color: {t['accent']};
        color: white;
    }}

    /* === MENUS === */
    QMenu {{
        background-color: {t['panel_bg']};
        border: 1px solid {t['border']};
        border-radius: 6px;
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 28px 6px 12px;
        border-radius: 4px;
        margin: 1px 4px;
    }}
    QMenu::item:selected {{
        background-color: {t['accent']};
        color: white;
    }}
    QMenu::separator {{
        height: 1px;
        background-color: {t['border']};
        margin: 4px 8px;
    }}
    QMenu::icon {{
        margin-left: 8px;
    }}

    /* === TOOLBARS === */
    QToolBar {{
        background-color: {t['toolbar_bg']};
        border-bottom: 1px solid {t['border']};
        spacing: 2px;
        padding: 3px 6px;
    }}
    QToolBar::separator {{
        width: 1px;
        background-color: {t['border']};
        margin: 4px 6px;
    }}
    QToolBar QToolButton {{
        background-color: {t['surface']};
        color: {t['text_primary']};
        border: 1px solid {t['border']};
        border-radius: 5px;
        padding: 5px 10px;
        margin: 1px;
        font-size: 13px;
        font-weight: 500;
    }}
    QToolBar QToolButton:hover {{
        background-color: {t['accent']};
        color: white;
        border-color: {t['accent_hover']};
    }}
    QToolBar QToolButton:pressed {{
        background-color: {t['accent_dark']};
    }}

    /* === BUTTONS === */
    QPushButton {{
        background-color: {t['surface']};
        color: {t['text_primary']};
        border: 1px solid {t['border']};
        border-radius: 5px;
        padding: 6px 14px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background-color: {t['surface_hover']};
        border-color: {t['accent']};
    }}
    QPushButton:pressed {{
        background-color: {t['surface_active']};
    }}
    QPushButton:disabled {{
        color: {t['text_disabled']};
        background-color: {t['surface']};
        border-color: {t['border']};
    }}
    QPushButton#primary {{
        background-color: {t['accent']};
        color: white;
        border: none;
        font-weight: 600;
    }}
    QPushButton#primary:hover {{
        background-color: {t['accent_hover']};
    }}

    /* === INPUTS === */
    QDoubleSpinBox, QSpinBox {{
        background-color: {t['input_bg']};
        color: {t['text_primary']};
        border: 1px solid {t['border']};
        border-radius: 4px;
        padding: 4px 8px;
        min-height: 24px;
    }}
    QDoubleSpinBox:focus, QSpinBox:focus {{
        border-color: {t['accent']};
    }}
    QDoubleSpinBox::up-button, QSpinBox::up-button,
    QDoubleSpinBox::down-button, QSpinBox::down-button {{
        border: none;
        width: 18px;
    }}

    QComboBox {{
        background-color: {t['input_bg']};
        color: {t['text_primary']};
        border: 1px solid {t['border']};
        border-radius: 4px;
        padding: 4px 8px;
        min-height: 24px;
    }}
    QComboBox:focus {{
        border-color: {t['accent']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {t['panel_bg']};
        color: {t['text_primary']};
        border: 1px solid {t['border']};
        selection-background-color: {t['accent']};
        selection-color: white;
        outline: none;
    }}
    QComboBox QAbstractItemView::item {{
        background-color: {t['panel_bg']};
        color: {t['text_primary']};
        padding: 6px 8px;
        min-height: 24px;
    }}
    QComboBox QAbstractItemView::item:hover {{
        background-color: {t['surface_hover']};
    }}
    QComboBox QAbstractItemView::item:selected {{
        background-color: {t['accent']};
        color: white;
    }}
    QComboBox QListView {{
        background-color: {t['panel_bg']};
        color: {t['text_primary']};
        border: 1px solid {t['border']};
    }}

    QCheckBox {{
        spacing: 6px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {t['border']};
        border-radius: 3px;
        background-color: {t['input_bg']};
    }}
    QCheckBox::indicator:checked {{
        background-color: {t['accent']};
        border-color: {t['accent']};
    }}

    QSlider::groove:horizontal {{
        height: 4px;
        background-color: {t['border']};
        border-radius: 2px;
    }}
    QSlider::handle:horizontal {{
        width: 14px;
        height: 14px;
        margin: -5px 0;
        background-color: {t['accent']};
        border-radius: 7px;
    }}
    QSlider::handle:horizontal:hover {{
        background-color: {t['accent_hover']};
    }}
    QSlider::sub-page:horizontal {{
        background-color: {t['accent']};
        border-radius: 2px;
    }}

    /* === SCROLL === */
    QScrollArea {{
        border: none;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 0;
    }}
    QScrollBar::handle:vertical {{
        background: {t['scrollbar']};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {t['scrollbar_hover']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
    }}
    QScrollBar::handle:horizontal {{
        background: {t['scrollbar']};
        border-radius: 4px;
        min-width: 30px;
    }}

    /* === PANELS === */
    QGroupBox {{
        color: {t['text_primary']};
        border: 1px solid {t['border']};
        border-radius: 6px;
        margin-top: 12px;
        padding: 12px 8px 8px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
    }}

    QTabWidget::pane {{
        border: 1px solid {t['border']};
        border-radius: 6px;
        background-color: {t['panel_bg']};
    }}
    QTabBar::tab {{
        background-color: {t['surface']};
        color: {t['text_secondary']};
        border: 1px solid {t['border']};
        border-bottom: none;
        border-top-left-radius: 5px;
        border-top-right-radius: 5px;
        padding: 6px 16px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background-color: {t['panel_bg']};
        color: {t['accent']};
        font-weight: 600;
    }}

    /* === LIST WIDGET === */
    QListWidget {{
        background-color: {t['panel_bg']};
        color: {t['text_primary']};
        border: 1px solid {t['border']};
        border-radius: 6px;
        outline: none;
        font-size: 13px;
    }}
    QListWidget::item {{
        padding: 6px 10px;
        border-bottom: 1px solid {t['border']};
        border-radius: 0;
    }}
    QListWidget::item:selected {{
        background-color: {t['accent']};
        color: white;
        border-radius: 4px;
    }}
    QListWidget::item:hover:!selected {{
        background-color: {t['surface_hover']};
    }}

    /* === PROGRESS BAR === */
    QProgressBar {{
        background-color: {t['surface']};
        border: 1px solid {t['border']};
        border-radius: 4px;
        text-align: center;
        color: {t['text_secondary']};
        font-size: 12px;
        min-height: 6px;
        max-height: 6px;
    }}
    QProgressBar::chunk {{
        background-color: {t['accent']};
        border-radius: 3px;
    }}

    /* === STATUS BAR === */
    QStatusBar {{
        background-color: {t['header_bg']};
        color: {t['text_secondary']};
        border-top: 1px solid {t['border']};
        font-size: 13px;
    }}

    /* === SPLITTER === */
    QSplitter::handle {{
        background-color: {t['border']};
        width: 1px;
        height: 1px;
    }}
    QSplitter::handle:hover {{
        background-color: {t['accent']};
    }}

    /* === TOOLTIP === */
    QToolTip {{
        background-color: {t['surface']};
        color: {t['text_primary']};
        border: 1px solid {t['border']};
        border-radius: 4px;
        padding: 4px 8px;
        font-size: 13px;
    }}

    /* === LABEL STYLES === */
    QLabel#title {{
        font-size: 14px;
        font-weight: 700;
        color: {t['text_primary']};
    }}
    QLabel#subtitle {{
        font-size: 13px;
        color: {t['text_secondary']};
    }}
    QLabel#accent {{
        color: {t['accent']};
        font-weight: 600;
    }}

    /* === DIALOGS === */
    QMessageBox {{
        background-color: {t['panel_bg']};
        color: {t['text_primary']};
    }}
    QMessageBox QLabel {{
        color: {t['text_primary']};
        font-size: 14px;
    }}
    QMessageBox QPushButton {{
        min-width: 80px;
        min-height: 28px;
    }}
    QDialog {{
        background-color: {t['panel_bg']};
        color: {t['text_primary']};
    }}
    QInputDialog {{
        background-color: {t['panel_bg']};
        color: {t['text_primary']};
    }}

    /* === APP HEADER/FOOTER === */
    QWidget#appHeader {{
        background-color: {t['header_bg']};
        border-bottom: 1px solid {t['border']};
    }}
    QWidget#appFooter {{
        background-color: {t['header_bg']};
        border-top: 1px solid {t['border']};
    }}
    QLabel#appLogo {{
        font-size: 15px;
        font-weight: 800;
        color: {t['accent']};
        letter-spacing: 3px;
    }}

    /* === CANVAS === */
    ImageCanvas {{
        background-color: {t['canvas_bg']};
        border: 1px solid {t['border']};
    }}

    /* === HISTOGRAM === */
    HistogramWidget {{
        background-color: {t['histogram_bg']};
        border-top: 1px solid {t['border']};
    }}

    /* === PROCESS ICONS BAR === */
    ProcessIconsBar {{
        background-color: {t['toolbar_bg']};
        border-top: 1px solid {t['border']};
    }}
    """
