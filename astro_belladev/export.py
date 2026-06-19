"""
export.py
---------
Exportación de imágenes a formatos de visualización (PNG, JPEG).

Los formatos FITS y TIFF preservan la profundidad de bits completa
y son para procesamiento. PNG y JPEG son para compartir el resultado
final en redes, web o imprimir.

PNG: 8 o 16 bits, sin pérdida, soporta transparencia.
JPEG: 8 bits, con compresión (lossy), tamaño pequeño.
"""

from pathlib import Path
import numpy as np
import cv2


def _normalize_for_export(data, bits=8):
    """
    Normaliza datos float32 a rango entero para exportación.
    Asume que la imagen ya está estirada (rango ~0-1).
    Si no lo está, la normaliza al rango completo.
    """
    result = data.astype(np.float32).copy()

    dmin = np.min(result)
    dmax = np.max(result)

    if dmax <= 0:
        if bits == 16:
            return np.zeros_like(result, dtype=np.uint16)
        return np.zeros_like(result, dtype=np.uint8)

    if dmax > 1.0:
        result = (result - dmin) / (dmax - dmin)

    result = np.clip(result, 0, 1)

    if bits == 16:
        return (result * 65535).astype(np.uint16)
    return (result * 255).astype(np.uint8)


def _rgb_to_bgr(data):
    """OpenCV usa BGR, nosotros RGB."""
    if data.ndim == 3 and data.shape[-1] == 3:
        return data[..., ::-1].copy()
    return data


def save_png(path, data, bits=16):
    """
    Guarda como PNG.

    Parámetros
    ----------
    path : str
        Ruta de salida (.png).
    data : numpy array
        Imagen a guardar.
    bits : int
        8 o 16. PNG de 16 bits preserva más rango dinámico.
    """
    normalized = _normalize_for_export(data, bits=bits)
    bgr = _rgb_to_bgr(normalized)

    compression = [cv2.IMWRITE_PNG_COMPRESSION, 6]
    cv2.imwrite(str(path), bgr, compression)


def save_jpeg(path, data, quality=95):
    """
    Guarda como JPEG.

    Parámetros
    ----------
    path : str
        Ruta de salida (.jpg/.jpeg).
    quality : int (1-100)
        Calidad de compresión. 95 = alta calidad, 75 = web.
    """
    normalized = _normalize_for_export(data, bits=8)
    bgr = _rgb_to_bgr(normalized)

    params = [cv2.IMWRITE_JPEG_QUALITY, quality]
    cv2.imwrite(str(path), bgr, params)


def save_image(path, data, **kwargs):
    """
    Punto de entrada principal: detecta formato por extensión.
    Soporta FITS, TIFF, PNG y JPEG.
    """
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".png":
        bits = kwargs.get("bits", 16)
        save_png(str(path), data, bits=bits)

    elif suffix in (".jpg", ".jpeg"):
        quality = kwargs.get("quality", 95)
        save_jpeg(str(path), data, quality=quality)

    elif suffix in (".tif", ".tiff"):
        from .io_tiff import save_tiff
        bits = kwargs.get("bits", 32)
        save_tiff(str(path), data, bits=bits)

    elif suffix in (".fits", ".fit", ".fts"):
        from .io_fits import save_fits
        save_fits(str(path), data)

    else:
        raise ValueError(
            f"Formato no soportado: {suffix}. "
            f"Usa .fits, .tiff, .png o .jpg"
        )
