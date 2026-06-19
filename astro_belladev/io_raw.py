"""
io_raw.py
---------
Lectura de archivos RAW de cámaras DSLR y mirrorless.

Formatos soportados (vía rawpy/LibRaw):
  Canon (.cr2, .cr3), Nikon (.nef), Sony (.arw),
  Adobe DNG (.dng), y prácticamente cualquier RAW de cámara.

Dos modos de lectura:
  - raw_bayer: extrae los datos Bayer sin procesar, para que el
    pipeline de astro haga su propio debayer después de calibrar.
  - raw_rgb: usa el motor de rawpy para producir RGB directamente
    (útil para previsualización rápida, pero pierde control sobre
    el debayer).
"""

from pathlib import Path
import numpy as np

try:
    import rawpy
    HAS_RAWPY = True
except ImportError:
    HAS_RAWPY = False

RAW_EXTENSIONS = {
    ".cr2", ".cr3", ".nef", ".arw", ".dng",
    ".orf", ".rw2", ".raf", ".pef", ".srw",
}


def is_raw_file(path):
    return Path(path).suffix.lower() in RAW_EXTENSIONS


def _require_rawpy():
    if not HAS_RAWPY:
        raise ImportError(
            "Para leer archivos RAW necesitas instalar rawpy: "
            "pip install rawpy"
        )


def _rawpy_pattern_to_str(raw):
    """Convierte el patrón numérico de rawpy a string RGGB/BGGR/etc."""
    desc = raw.color_desc.decode() if isinstance(raw.color_desc, bytes) else raw.color_desc
    pattern_idx = raw.raw_pattern.flatten()[:4]
    color_map = {i: c for i, c in enumerate(desc)}
    return "".join(color_map[idx] for idx in pattern_idx)


def load_raw_bayer(path):
    """
    Carga un archivo RAW y devuelve los datos Bayer sin procesar.

    Devuelve
    --------
    data : numpy array float32, 2D (alto, ancho)
        Datos Bayer en bruto.
    pattern : str
        Patrón Bayer detectado ("RGGB", "BGGR", etc.)
    metadata : dict
        Metadatos básicos extraídos del RAW.
    """
    _require_rawpy()

    raw = rawpy.imread(str(path))

    bayer_data = raw.raw_image_visible.astype(np.float32)

    pattern = _rawpy_pattern_to_str(raw)

    metadata = {
        "camera": getattr(raw, "camera_make", "") + " " + getattr(raw, "camera_model", ""),
        "black_level": raw.black_level_per_channel,
        "white_level": raw.white_level,
        "bayer_pattern": pattern,
    }

    for ch_idx in range(4):
        bl = raw.black_level_per_channel[ch_idx]
        if bl > 0:
            rows = range(ch_idx // 2, bayer_data.shape[0], 2)
            cols = range(ch_idx % 2, bayer_data.shape[1], 2)
            bayer_data[np.ix_(rows, cols)] -= bl

    bayer_data = np.clip(bayer_data, 0, None)

    raw.close()

    return bayer_data, pattern, metadata


def load_raw_rgb(path):
    """
    Carga un archivo RAW y devuelve la imagen ya procesada en RGB.
    Útil para previsualización rápida, pero para el pipeline de astro
    es mejor usar load_raw_bayer y hacer el debayer manualmente.
    """
    _require_rawpy()

    raw = rawpy.imread(str(path))
    rgb = raw.postprocess(
        use_camera_wb=True,
        no_auto_bright=True,
        output_bps=16,
        gamma=(1, 1),
    )
    raw.close()

    return rgb.astype(np.float32)
