"""
io_tiff.py
----------
Lectura y escritura de imágenes TIFF de 16 y 32 bits.

TIFF es un formato común como paso intermedio en astrofotografía:
muchos astrofotógrafos exportan desde su software de captura a TIFF
antes de procesar, y es el formato de salida habitual de PixInsight
y Siril para intercambiar con Photoshop/GIMP.

Usa tifffile para máxima compatibilidad con TIFF de 16/32 bits
y múltiples canales.
"""

from pathlib import Path
import numpy as np

try:
    import tifffile
    HAS_TIFFFILE = True
except ImportError:
    HAS_TIFFFILE = False

TIFF_EXTENSIONS = {".tif", ".tiff"}


def is_tiff_file(path):
    return Path(path).suffix.lower() in TIFF_EXTENSIONS


def _require_tifffile():
    if not HAS_TIFFFILE:
        raise ImportError(
            "Para leer archivos TIFF necesitas instalar tifffile: "
            "pip install tifffile"
        )


def load_tiff(path):
    """
    Carga un archivo TIFF y lo devuelve como array float32.

    Devuelve
    --------
    data : numpy array float32
        (alto, ancho) para monocroma, (alto, ancho, 3) para RGB.
    """
    _require_tifffile()

    data = tifffile.imread(str(path))

    if data.ndim == 3 and data.shape[0] in (3, 4) and data.shape[0] < data.shape[1]:
        data = np.moveaxis(data, 0, -1)

    if data.ndim == 3 and data.shape[-1] == 4:
        data = data[..., :3]

    data = data.astype(np.float32)

    return data


def save_tiff(path, data, bits=32):
    """
    Guarda un array como TIFF.

    Parámetros
    ----------
    bits : int
        16 o 32. TIFF de 32 bits preserva la precisión float completa;
        16 bits es más compatible con editores gráficos.
    """
    _require_tifffile()

    data_to_save = data.copy()

    if data_to_save.ndim == 3 and data_to_save.shape[-1] == 3:
        data_to_save = np.moveaxis(data_to_save, -1, 0)

    if bits == 16:
        max_val = np.max(data_to_save) if np.max(data_to_save) > 0 else 1.0
        data_to_save = (data_to_save / max_val * 65535).astype(np.uint16)
    else:
        data_to_save = data_to_save.astype(np.float32)

    tifffile.imwrite(str(path), data_to_save)
