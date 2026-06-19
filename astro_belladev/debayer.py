"""
debayer.py
----------
Demosaicing (debayer) de imágenes con patrón Bayer (CFA).

Las cámaras a color con sensor de un solo chip (DSLR, mirrorless,
astrocámaras OSC) capturan cada píxel a través de un filtro de un
solo color (R, G o B). El debayer interpola los canales que faltan
para producir una imagen RGB completa.

Patrones soportados: RGGB, BGGR, GRBG, GBRG (los cuatro estándar).
Usa OpenCV para el demosaicing (método por defecto: VNG, calidad
superior al bilineal básico).
"""

import numpy as np
import cv2

# OpenCV nombra los patrones Bayer por la posición (1,1) del bloque 2x2,
# que es la opuesta a la convención astronómica (posición 0,0).
BAYER_PATTERNS = {
    "RGGB": cv2.COLOR_BayerBG2RGB,
    "BGGR": cv2.COLOR_BayerRG2RGB,
    "GRBG": cv2.COLOR_BayerGB2RGB,
    "GBRG": cv2.COLOR_BayerGR2RGB,
}

BAYER_PATTERNS_VNG = {
    "RGGB": cv2.COLOR_BayerBG2RGB_VNG,
    "BGGR": cv2.COLOR_BayerRG2RGB_VNG,
    "GRBG": cv2.COLOR_BayerGB2RGB_VNG,
    "GBRG": cv2.COLOR_BayerGR2RGB_VNG,
}


def is_bayer(data, header=None):
    """
    Detecta si una imagen es Bayer (CFA sin debayerear).
    - Si hay header FITS, busca el keyword BAYERPAT.
    - Si no, asume que una imagen 2D podría ser Bayer (el caller decide).
    """
    if header is not None:
        return "BAYERPAT" in header or "COLORTYP" in header

    return data.ndim == 2


def detect_pattern(header):
    """
    Extrae el patrón Bayer del header FITS.
    Busca BAYERPAT (estándar) y COLORTYP (usado por algunas cámaras ZWO).
    """
    pattern = None

    if header is not None:
        pattern = header.get("BAYERPAT", header.get("COLORTYP", None))

    if pattern is not None:
        pattern = pattern.strip().upper()
        if pattern in BAYER_PATTERNS:
            return pattern

    return None


def debayer(data, pattern="RGGB", method="vng"):
    """
    Convierte una imagen Bayer 2D (alto, ancho) en RGB (alto, ancho, 3).

    Parámetros
    ----------
    data : numpy array 2D, float32
        Imagen en bruto con patrón Bayer.
    pattern : str
        Patrón de color: "RGGB", "BGGR", "GRBG" o "GBRG".
    method : str
        Método de interpolación: "bilinear" (rápido) o "vng" (mejor calidad).

    Devuelve
    --------
    numpy array float32, shape (alto, ancho, 3)
    """
    pattern = pattern.upper()
    if pattern not in BAYER_PATTERNS:
        raise ValueError(
            f"Patrón Bayer desconocido: {pattern}. "
            f"Usa uno de: {list(BAYER_PATTERNS.keys())}"
        )

    if data.ndim != 2:
        raise ValueError(
            f"debayer espera una imagen 2D (alto, ancho), "
            f"pero recibió shape {data.shape}"
        )

    original_max = np.max(data) if np.max(data) > 0 else 1.0

    if method == "vng":
        # VNG solo soporta 8 bits en OpenCV -> escalamos a uint8
        normalized = (data / original_max * 255).astype(np.uint8)
        code = BAYER_PATTERNS_VNG[pattern]
        rgb = cv2.cvtColor(normalized, code)
        rgb_float = rgb.astype(np.float32) / 255.0 * original_max
    else:
        # Bilinear soporta uint8 y uint16 -> usamos uint16 para
        # preservar la profundidad de bits (importante en astro)
        normalized = (data / original_max * 65535).astype(np.uint16)
        code = BAYER_PATTERNS[pattern]
        rgb = cv2.cvtColor(normalized, code)
        rgb_float = rgb.astype(np.float32) / 65535.0 * original_max

    return rgb_float
