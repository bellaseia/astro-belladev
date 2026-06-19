"""
io_fits.py
----------
Funciones para leer y guardar imágenes en formato FITS, el estándar
para datos astronómicos (lo usan Siril, PixInsight y SASpro).

Una imagen FITS se guarda en este proyecto como un array de numpy:
- (alto, ancho)        -> imagen monocroma o Bayer sin debayerear
- (alto, ancho, 3)      -> imagen de color RGB ya debayereada

Soporta detección automática de patrón Bayer en el header FITS
(keyword BAYERPAT / COLORTYP) para debayer transparente.
También carga RAW de DSLR (.cr2, .nef, .arw, .dng...) y TIFF.
"""

from pathlib import Path
import numpy as np
from astropy.io import fits

from .io_raw import is_raw_file, load_raw_bayer, RAW_EXTENSIONS
from .io_tiff import is_tiff_file, load_tiff, TIFF_EXTENSIONS
from .debayer import debayer, detect_pattern, is_bayer

FITS_EXTENSIONS = {".fits", ".fit", ".fts"}

ALL_EXTENSIONS = FITS_EXTENSIONS | RAW_EXTENSIONS | TIFF_EXTENSIONS


def load_fits(path):
    """
    Carga una imagen FITS y la devuelve como array de numpy en float32.

    Devuelve también el header original, porque más adelante
    (WCS, metadatos de exposición, filtro, etc.) lo necesitaremos.
    """
    with fits.open(path) as hdul:
        data = hdul[0].data.astype(np.float32)
        header = hdul[0].header

    # Algunas cámaras guardan el eje de color primero (3, alto, ancho).
    # Lo normalizamos a (alto, ancho, 3) para trabajar siempre igual.
    if data.ndim == 3 and data.shape[0] == 3:
        data = np.moveaxis(data, 0, -1)

    return data, header


def load_image(path, auto_debayer=True, bayer_pattern=None):
    """
    Carga una imagen desde cualquier formato soportado (FITS, RAW, TIFF).

    Parámetros
    ----------
    path : str o Path
        Ruta al archivo de imagen.
    auto_debayer : bool
        Si True, detecta y aplica debayer automáticamente en FITS Bayer
        y RAW. Si False, devuelve los datos en bruto.
    bayer_pattern : str o None
        Fuerza un patrón Bayer específico ("RGGB", etc.). Si None,
        se autodetecta del header/metadatos del archivo.

    Devuelve
    --------
    data : numpy array float32
    header : dict o FITS header (None para RAW/TIFF)
    """
    path = Path(path)
    suffix = path.suffix.lower()

    if is_raw_file(path):
        bayer_data, detected_pattern, metadata = load_raw_bayer(path)
        if auto_debayer:
            pattern = bayer_pattern or detected_pattern or "RGGB"
            data = debayer(bayer_data, pattern=pattern)
        else:
            data = bayer_data
        return data, None

    if is_tiff_file(path):
        data = load_tiff(path)
        return data, None

    data, header = load_fits(path)

    if auto_debayer and data.ndim == 2 and is_bayer(data, header):
        pattern = bayer_pattern or detect_pattern(header)
        if pattern is not None:
            data = debayer(data, pattern=pattern)

    return data, header


def save_fits(path, data, header=None, overwrite=True):
    """
    Guarda un array de numpy como archivo FITS.
    """
    data_to_save = data.astype(np.float32)

    # Si es color (alto, ancho, 3), lo volvemos a poner en el orden
    # que espera el estándar FITS: (3, alto, ancho).
    if data_to_save.ndim == 3 and data_to_save.shape[-1] == 3:
        data_to_save = np.moveaxis(data_to_save, -1, 0)

    hdu = fits.PrimaryHDU(data=data_to_save, header=header)
    hdu.writeto(path, overwrite=overwrite)


def load_folder(folder, auto_debayer=True, bayer_pattern=None):
    """
    Carga todos los archivos de imagen soportados de una carpeta.
    Formatos: FITS (.fits/.fit/.fts), RAW (.cr2/.nef/.arw/.dng/...),
    TIFF (.tif/.tiff).
    """
    folder = Path(folder)
    paths = sorted([
        p for p in folder.iterdir()
        if p.is_file()
        and p.suffix.lower() in ALL_EXTENSIONS
    ])

    if not paths:
        raise FileNotFoundError(
            f"No se encontraron archivos de imagen en {folder}. "
            f"Formatos soportados: {', '.join(sorted(ALL_EXTENSIONS))}"
        )

    frames = []
    for p in paths:
        data, _ = load_image(p, auto_debayer=auto_debayer, bayer_pattern=bayer_pattern)
        frames.append(data)

    return frames, paths
