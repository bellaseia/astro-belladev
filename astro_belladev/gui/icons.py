"""
icons.py
--------
Iconos SVG inline para Astro BellaDev.

Iconos vectoriales en el estilo BellaDev (azul acero) generados
como SVG inline para no depender de archivos externos.
Se cargan como QIcon via QPixmap desde bytes SVG.
"""

from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import QByteArray, QSize
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtGui import QPainter, QImage

_ICON_CACHE = {}

def _svg_to_icon(svg_str, size=24):
    """Convierte SVG string a QIcon."""
    key = hash(svg_str + str(size))
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]

    svg_bytes = QByteArray(svg_str.encode('utf-8'))
    renderer = QSvgRenderer(svg_bytes)

    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()

    pixmap = QPixmap.fromImage(image)
    icon = QIcon(pixmap)
    _ICON_CACHE[key] = icon
    return icon


# Color base para los iconos (BellaDev blue)
C = "#6BA3D6"  # Azul claro para fondo oscuro
CD = "#2D5F8A"  # Azul oscuro para fondo claro

# === ICONOS ===

SVGS = {
    # --- Archivo ---
    "open": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <path d="M3 7V17C3 18.1 3.9 19 5 19H19C20.1 19 21 18.1 21 17V9C21 7.9 20.1 7 19 7H12L10 5H5C3.9 5 3 5.9 3 7Z" stroke="{C}" stroke-width="1.5" fill="none"/>
    </svg>''',

    "save": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <path d="M5 3H16L21 8V19C21 20.1 20.1 21 19 21H5C3.9 21 3 20.1 3 19V5C3 3.9 3.9 3 5 3Z" stroke="{C}" stroke-width="1.5"/>
        <rect x="7" y="13" width="10" height="6" rx="1" stroke="{C}" stroke-width="1.5"/>
        <rect x="8" y="3" width="6" height="5" rx="1" fill="{C}" opacity="0.3"/>
    </svg>''',

    "export": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <path d="M12 3V16M12 3L7 8M12 3L17 8" stroke="{C}" stroke-width="1.5" stroke-linecap="round"/>
        <path d="M4 17V19C4 20.1 4.9 21 6 21H18C19.1 21 20 20.1 20 19V17" stroke="{C}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>''',

    # --- Acciones generales ---
    "undo": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <path d="M4 9H15C17.8 9 20 11.2 20 14C20 16.8 17.8 19 15 19H10" stroke="{C}" stroke-width="1.5" stroke-linecap="round"/>
        <path d="M8 5L4 9L8 13" stroke="{C}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    "auto": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="9" stroke="{C}" stroke-width="1.5"/>
        <path d="M12 7V12L15 14" stroke="{C}" stroke-width="1.5" stroke-linecap="round"/>
        <circle cx="12" cy="12" r="2" fill="{C}"/>
    </svg>''',

    # --- Pre-procesamiento ---
    "calibrate": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="3" width="18" height="18" rx="3" stroke="{C}" stroke-width="1.5"/>
        <line x1="3" y1="12" x2="21" y2="12" stroke="{C}" stroke-width="1" opacity="0.5"/>
        <line x1="12" y1="3" x2="12" y2="21" stroke="{C}" stroke-width="1" opacity="0.5"/>
        <circle cx="12" cy="12" r="3" stroke="{C}" stroke-width="1.5"/>
    </svg>''',

    "score": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="14" width="4" height="7" rx="1" fill="{C}" opacity="0.5"/>
        <rect x="10" y="9" width="4" height="12" rx="1" fill="{C}" opacity="0.7"/>
        <rect x="17" y="4" width="4" height="17" rx="1" fill="{C}"/>
    </svg>''',

    "debayer": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="3" width="8" height="8" rx="1" fill="#D94452" opacity="0.6"/>
        <rect x="13" y="3" width="8" height="8" rx="1" fill="#4CAF6E" opacity="0.6"/>
        <rect x="3" y="13" width="8" height="8" rx="1" fill="#4CAF6E" opacity="0.6"/>
        <rect x="13" y="13" width="8" height="8" rx="1" fill="#4A7FB5" opacity="0.6"/>
    </svg>''',

    "align": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <rect x="2" y="2" width="10" height="10" rx="2" stroke="{C}" stroke-width="1.5" opacity="0.5"/>
        <rect x="6" y="6" width="10" height="10" rx="2" stroke="{C}" stroke-width="1.5" opacity="0.7"/>
        <rect x="10" y="10" width="10" height="10" rx="2" stroke="{C}" stroke-width="1.5"/>
    </svg>''',

    "stack": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <path d="M12 2L22 8L12 14L2 8Z" stroke="{C}" stroke-width="1.5" fill="{C}" fill-opacity="0.2"/>
        <path d="M2 12L12 18L22 12" stroke="{C}" stroke-width="1.5"/>
        <path d="M2 16L12 22L22 16" stroke="{C}" stroke-width="1.5" opacity="0.5"/>
    </svg>''',

    # --- Procesamiento ---
    "stretch": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="3" width="18" height="18" rx="2" stroke="{C}" stroke-width="1.5"/>
        <path d="M3 18Q8 16 12 10Q16 4 21 3" stroke="{C}" stroke-width="2" fill="none"/>
    </svg>''',

    "background": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="3" width="18" height="18" rx="2" stroke="{C}" stroke-width="1.5"/>
        <path d="M3 15Q7 12 12 13Q17 14 21 11" stroke="{C}" stroke-width="1.5" stroke-dasharray="3 2"/>
    </svg>''',

    "denoise": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="9" stroke="{C}" stroke-width="1.5"/>
        <path d="M6 12H8L9.5 8L12 16L14.5 10L16 12H18" stroke="{C}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    "sharpen": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <polygon points="12,2 15,9 22,9 16,14 18,21 12,17 6,21 8,14 2,9 9,9" stroke="{C}" stroke-width="1.5" fill="{C}" fill-opacity="0.15"/>
    </svg>''',

    "color": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <circle cx="10" cy="10" r="6" fill="#D94452" opacity="0.4"/>
        <circle cx="14" cy="10" r="6" fill="#4CAF6E" opacity="0.4"/>
        <circle cx="12" cy="14" r="6" fill="#4A7FB5" opacity="0.4"/>
    </svg>''',

    "levels": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <line x1="4" y1="8" x2="20" y2="8" stroke="{C}" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="4" y1="12" x2="20" y2="12" stroke="{C}" stroke-width="1.5" stroke-linecap="round"/>
        <line x1="4" y1="16" x2="20" y2="16" stroke="{C}" stroke-width="1.5" stroke-linecap="round"/>
        <circle cx="8" cy="8" r="2.5" fill="{C}"/>
        <circle cx="14" cy="12" r="2.5" fill="{C}"/>
        <circle cx="10" cy="16" r="2.5" fill="{C}"/>
    </svg>''',

    "stars": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <polygon points="12,2 14,8 20,9 15,13 17,20 12,16 7,20 9,13 4,9 10,8" fill="{C}" opacity="0.8"/>
        <circle cx="6" cy="5" r="1" fill="{C}" opacity="0.6"/>
        <circle cx="19" cy="4" r="1.5" fill="{C}" opacity="0.4"/>
        <circle cx="20" cy="18" r="1" fill="{C}" opacity="0.5"/>
    </svg>''',

    "starless": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <polygon points="12,2 14,8 20,9 15,13 17,20 12,16 7,20 9,13 4,9 10,8" stroke="{C}" stroke-width="1.5" fill="none" opacity="0.4"/>
        <line x1="4" y1="4" x2="20" y2="20" stroke="{C}" stroke-width="2" stroke-linecap="round"/>
    </svg>''',

    "spikes": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="3" fill="{C}"/>
        <line x1="12" y1="2" x2="12" y2="22" stroke="{C}" stroke-width="1" opacity="0.6"/>
        <line x1="2" y1="12" x2="22" y2="12" stroke="{C}" stroke-width="1" opacity="0.6"/>
        <line x1="5" y1="5" x2="19" y2="19" stroke="{C}" stroke-width="0.7" opacity="0.3"/>
        <line x1="19" y1="5" x2="5" y2="19" stroke="{C}" stroke-width="0.7" opacity="0.3"/>
    </svg>''',

    # --- AI ---
    "ai": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="9" stroke="{C}" stroke-width="1.5"/>
        <circle cx="12" cy="12" r="3" fill="{C}" opacity="0.5"/>
        <path d="M12 3V7M12 17V21M3 12H7M17 12H21" stroke="{C}" stroke-width="1.5" stroke-linecap="round"/>
        <path d="M6.3 6.3L8.8 8.8M15.2 15.2L17.7 17.7M6.3 17.7L8.8 15.2M15.2 8.8L17.7 6.3" stroke="{C}" stroke-width="1" stroke-linecap="round" opacity="0.5"/>
    </svg>''',

    # --- Herramientas ---
    "crop": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <path d="M7 1V17H23M1 7H17V23" stroke="{C}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>''',

    "rotate": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <path d="M4 12C4 7.6 7.6 4 12 4C16.4 4 20 7.6 20 12" stroke="{C}" stroke-width="1.5" stroke-linecap="round"/>
        <path d="M20 12C20 16.4 16.4 20 12 20C7.6 20 4 16.4 4 12" stroke="{C}" stroke-width="1.5" stroke-linecap="round" stroke-dasharray="3 2"/>
        <path d="M16 4L20 4L20 8" stroke="{C}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>''',

    "heal": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="3" width="18" height="18" rx="3" stroke="{C}" stroke-width="1.5"/>
        <path d="M12 7V17M7 12H17" stroke="{C}" stroke-width="2" stroke-linecap="round"/>
    </svg>''',

    "mosaic": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <rect x="2" y="2" width="9" height="9" rx="1" stroke="{C}" stroke-width="1.5"/>
        <rect x="13" y="2" width="9" height="9" rx="1" stroke="{C}" stroke-width="1.5"/>
        <rect x="2" y="13" width="9" height="9" rx="1" stroke="{C}" stroke-width="1.5"/>
        <rect x="13" y="13" width="9" height="9" rx="1" stroke="{C}" stroke-width="1.5"/>
    </svg>''',

    "catalog": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="9" stroke="{C}" stroke-width="1.5"/>
        <circle cx="10" cy="9" r="1.5" fill="{C}" opacity="0.8"/>
        <circle cx="15" cy="11" r="1" fill="{C}" opacity="0.6"/>
        <circle cx="8" cy="14" r="1" fill="{C}" opacity="0.5"/>
        <circle cx="14" cy="16" r="1.5" fill="{C}" opacity="0.7"/>
        <circle cx="17" cy="7" r="0.8" fill="{C}" opacity="0.4"/>
    </svg>''',

    # --- Vista ---
    "histogram": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <rect x="2" y="16" width="3" height="5" rx="0.5" fill="{C}" opacity="0.5"/>
        <rect x="6" y="12" width="3" height="9" rx="0.5" fill="{C}" opacity="0.6"/>
        <rect x="10" y="6" width="3" height="15" rx="0.5" fill="{C}" opacity="0.8"/>
        <rect x="14" y="9" width="3" height="12" rx="0.5" fill="{C}" opacity="0.7"/>
        <rect x="18" y="14" width="3" height="7" rx="0.5" fill="{C}" opacity="0.5"/>
    </svg>''',

    # --- Macros ---
    "macro": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <path d="M4 6H20M4 12H20M4 18H14" stroke="{C}" stroke-width="1.5" stroke-linecap="round"/>
        <path d="M17 16L21 18L17 20" stroke="{C}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="{C}" fill-opacity="0.3"/>
    </svg>''',

    # --- Asistente ---
    "assistant": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <path d="M12 2C6.5 2 2 6.5 2 12C2 17.5 6.5 22 12 22C17.5 22 22 17.5 22 12C22 6.5 17.5 2 12 2Z" stroke="{C}" stroke-width="1.5"/>
        <path d="M12 8V13" stroke="{C}" stroke-width="2" stroke-linecap="round"/>
        <circle cx="12" cy="16.5" r="1" fill="{C}"/>
    </svg>''',

    # --- Planner ---
    "planner": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="9" stroke="{C}" stroke-width="1.5"/>
        <path d="M12 6V12H17" stroke="{C}" stroke-width="1.5" stroke-linecap="round"/>
        <circle cx="7" cy="5" r="1" fill="{C}" opacity="0.6"/>
        <circle cx="18" cy="8" r="1.2" fill="{C}" opacity="0.4"/>
        <circle cx="5" cy="16" r="0.8" fill="{C}" opacity="0.5"/>
    </svg>''',

    # --- Narrowband ---
    "narrowband": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="3" width="18" height="18" rx="2" stroke="{C}" stroke-width="1.5"/>
        <line x1="3" y1="9" x2="21" y2="9" stroke="#D94452" stroke-width="2" opacity="0.6"/>
        <line x1="3" y1="14" x2="21" y2="14" stroke="#4CAF6E" stroke-width="2" opacity="0.6"/>
        <line x1="3" y1="19" x2="21" y2="19" stroke="#4A7FB5" stroke-width="2" opacity="0.6"/>
    </svg>''',

    # --- Settings ---
    "settings": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="3" stroke="{C}" stroke-width="1.5"/>
        <path d="M12 1V4M12 20V23M1 12H4M20 12H23M4.2 4.2L6.3 6.3M17.7 17.7L19.8 19.8M4.2 19.8L6.3 17.7M17.7 6.3L19.8 4.2" stroke="{C}" stroke-width="1.5" stroke-linecap="round"/>
    </svg>''',

    "theme": f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="9" stroke="{C}" stroke-width="1.5"/>
        <path d="M12 3A9 9 0 0 1 12 21Z" fill="{C}" opacity="0.4"/>
    </svg>''',
}


def get_icon(name, size=20):
    """Obtiene un QIcon por nombre."""
    svg = SVGS.get(name)
    if svg is None:
        return QIcon()
    return _svg_to_icon(svg, size)


def get_all_icon_names():
    """Lista todos los iconos disponibles."""
    return list(SVGS.keys())
