"""
i18n.py
-------
Sistema de internacionalizacion para Astro BellaDev.

Soporta multiples idiomas. Cada string visible de la GUI
pasa por tr() que busca la traduccion en el idioma activo.

Uso:
    from .i18n import tr, set_language
    set_language("en")
    print(tr("Abrir"))  # -> "Open"
"""

_current_language = "es"

TRANSLATIONS = {
    "en": {
        # === General ===
        "Listo": "Ready",
        "Error": "Error",
        "Aviso": "Warning",
        "Sin imagen": "No image",
        "Aplicar": "Apply",
        "Reset": "Reset",
        "Deshacer": "Undo",
        "Cerrar": "Close",
        "Cancelar": "Cancel",
        "Aceptar": "OK",
        "Guardar": "Save",
        "Abrir": "Open",
        "Parametros": "Parameters",
        "Completado": "Done",

        # === Header ===
        "Modo: AUTO": "Mode: AUTO",
        "Modo: EXPERTO": "Mode: EXPERT",
        "AUTO": "AUTO",
        "EXPERTO": "EXPERT",
        "Cambiar tema claro/oscuro": "Toggle light/dark theme",

        # === Menus ===
        "Archivo": "File",
        "Pre-procesamiento": "Pre-processing",
        "Procesamiento": "Processing",
        "Herramientas": "Tools",
        "Asistente": "Assistant",
        "Planificador": "Planner",
        "Vista": "View",

        # === Pipeline ===
        "Pipeline": "Pipeline",
        "Abre una imagen (Ctrl+O)": "Open an image (Ctrl+O)",
        "Cargada": "Loaded",

        # === Toolbar ===
        "Abrir imagen (Ctrl+O)": "Open image (Ctrl+O)",
        "Guardar (Ctrl+S)": "Save (Ctrl+S)",
        "Deshacer (Ctrl+Z)": "Undo (Ctrl+Z)",
        "Pipeline automatico": "Automatic pipeline",
        "Auto": "Auto",
        "Calibrar": "Calibrate",
        "Calibrar light frames": "Calibrate light frames",
        "Scoring": "Scoring",
        "Evaluar calidad": "Evaluate quality",
        "Debayer": "Debayer",
        "CFA a RGB": "CFA to RGB",
        "Alinear": "Align",
        "Registro por estrellas": "Star registration",
        "Apilar": "Stack",
        "Stacking": "Stacking",
        "Stretch": "Stretch",
        "Estiramiento": "Stretching",
        "ABE": "ABE",
        "Extraccion de fondo": "Background extraction",
        "Denoise": "Denoise",
        "Reduccion de ruido": "Noise reduction",
        "Sharpen": "Sharpen",
        "Nitidez": "Sharpening",
        "Color": "Color",
        "Balance de blancos": "White balance",
        "Niveles": "Levels",
        "Curvas y niveles": "Curves & Levels",
        "Estrellas": "Stars",
        "Herramientas estelares": "Star tools",
        "Spikes": "Spikes",
        "Diffraction spikes": "Diffraction spikes",
        "Nebulosa": "Nebula",
        "Macro nebulosa completa": "Full nebula macro",
        "Procesamiento AI": "AI Processing",

        # === Viewer ===
        "Sin histograma": "No histogram",

        # === Status ===
        "Abre una imagen primero": "Open an image first",
        "Abre una imagen primero (Ctrl+O)": "Open an image first (Ctrl+O)",
        "Pipeline automatico completado": "Automatic pipeline completed",
        "Error al abrir": "Error opening file",
        "Error al guardar": "Error saving file",

        # === Modo ===
        "Modo automatico: el asistente decide los parametros": "Auto mode: the assistant decides parameters",
        "Modo experto: control total sobre cada parametro": "Expert mode: full control over every parameter",

        # === Histograma ===
        "Histograma": "Histogram",

        # === Imagenes ===
        "Mono": "Mono",
        "RGB": "RGB",

        "EXPERTO": "EXPERT",
        "Macro nebulosa": "Nebula macro",
        "Registro estrellas": "Star registration",
        "Fondo": "Background",
        "Ruido": "Noise",
        "Balance blancos": "White balance",
        "Curvas/niveles": "Curves/Levels",

        # === Submenus del registry ===
        "Mascaras": "Masks",
        "Narrowband": "Narrowband",
        "PixelMath": "PixelMath",
        "SCNR": "SCNR",
        "LRGB Combine": "LRGB Combine",
        "Contraste local": "Local Contrast",
        "Reparacion": "Repair",
        "Anotacion": "Annotation",
        "Guardar como": "Save As",
        "Exportar para": "Export For",
        "Auto-parametros": "Auto Parameters",
        "Tema": "Theme",
        "Oscuro": "Dark",
        "Claro": "Light",
        "Idioma / Language": "Language / Idioma",
        "Cargada": "Loaded",

        # === Params panel modo auto ===
        "Sin parametros configurables": "No configurable parameters",
        "Modo AUTO": "AUTO Mode",
        "Cambia a EXPERTO para ajustar manualmente.": "Switch to EXPERT to adjust manually.",

        # === Steps panel ===
        "Abre una imagen (Ctrl+O)": "Open an image (Ctrl+O)",

        # === Assistant panel ===
        "Analizar imagen": "Analyze image",
        "Abre una imagen para analizar": "Open an image to analyze",
        "Aplicar plan completo": "Apply full plan",
        "La imagen esta en buen estado": "The image is in good condition",
        "problemas detectados": "problems detected",
        "aspectos mejorables": "areas for improvement",
    },
}


def set_language(lang_code):
    """Cambia el idioma activo."""
    global _current_language
    _current_language = lang_code


def get_language():
    """Devuelve el idioma activo."""
    return _current_language


def tr(text):
    """Traduce un texto al idioma activo."""
    if _current_language == "es":
        return text

    lang_dict = TRANSLATIONS.get(_current_language, {})
    return lang_dict.get(text, text)


def available_languages():
    """Lista los idiomas disponibles."""
    return {
        "es": "Espanol",
        "en": "English",
    }
