"""
background.py
-------------
Extracción de fondo (gradientes, viñeteo residual, contaminación
lumínica).

ABE (Automatic Background Extraction):
  Muestrea puntos del fondo automáticamente (evitando estrellas y
  nebulosas), ajusta una superficie polinómica y la resta.

DBE (Dynamic Background Extraction):
  El usuario define puntos de muestreo manualmente (en la GUI futura),
  y se ajusta la superficie solo a esos puntos. Más preciso en campos
  complicados.
"""

import numpy as np
from scipy.ndimage import median_filter, label
from numpy.polynomial import polynomial as P


def _detect_background_samples(data, grid_size=8, star_sigma=3.0):
    """
    Muestrea puntos del fondo evitando estrellas y señal extendida.
    Divide la imagen en una rejilla y toma la mediana de cada celda
    tras excluir píxeles brillantes.
    """
    h, w = data.shape[:2]
    gray = data.mean(axis=-1) if data.ndim == 3 else data

    cell_h = h // grid_size
    cell_w = w // grid_size

    bg_median = np.median(gray)
    bg_std = np.std(gray)
    threshold = bg_median + star_sigma * bg_std

    points = []
    values = []

    for iy in range(grid_size):
        for ix in range(grid_size):
            y0 = iy * cell_h
            x0 = ix * cell_w
            y1 = min(y0 + cell_h, h)
            x1 = min(x0 + cell_w, w)

            cell = gray[y0:y1, x0:x1]
            mask = cell < threshold
            if np.sum(mask) < 10:
                continue

            bg_value = np.median(cell[mask])
            cy = (y0 + y1) / 2.0 / h
            cx = (x0 + x1) / 2.0 / w

            points.append((cy, cx))
            values.append(bg_value)

    return np.array(points), np.array(values)


def _fit_surface(points, values, degree=3):
    """
    Ajusta una superficie polinómica 2D a los puntos de fondo muestreados.
    """
    y_coords = points[:, 0]
    x_coords = points[:, 1]

    n_coeffs = (degree + 1) * (degree + 2) // 2
    if len(points) < n_coeffs:
        degree = max(1, int(np.sqrt(len(points))) - 1)

    A = []
    for p in range(degree + 1):
        for q in range(degree + 1 - p):
            A.append(y_coords**p * x_coords**q)

    A = np.array(A).T
    coeffs, _, _, _ = np.linalg.lstsq(A, values, rcond=None)

    return coeffs, degree


def _evaluate_surface(coeffs, degree, shape):
    """Evalúa la superficie polinómica en toda la imagen."""
    h, w = shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    yy_norm = yy.astype(np.float32) / h
    xx_norm = xx.astype(np.float32) / w

    surface = np.zeros((h, w), dtype=np.float32)
    idx = 0
    for p in range(degree + 1):
        for q in range(degree + 1 - p):
            surface += coeffs[idx] * yy_norm**p * xx_norm**q
            idx += 1

    return surface


def extract_background_abe(data, grid_size=8, degree=3, star_sigma=3.0):
    """
    ABE: Automatic Background Extraction.
    Detecta el fondo automáticamente y lo resta.

    Parámetros
    ----------
    data : numpy array float32
    grid_size : int
        Tamaño de la rejilla de muestreo (más = más puntos).
    degree : int
        Grado del polinomio de la superficie (1-5).
    star_sigma : float
        Sigmas sobre la mediana para excluir estrellas del muestreo.

    Devuelve
    --------
    corrected : imagen con fondo extraído
    background : el modelo de fondo estimado
    """
    if data.ndim == 3:
        corrected = np.zeros_like(data)
        background = np.zeros_like(data)
        for c in range(data.shape[-1]):
            corrected[..., c], background[..., c] = extract_background_abe(
                data[..., c], grid_size, degree, star_sigma
            )
        return corrected, background

    points, values = _detect_background_samples(data, grid_size, star_sigma)

    if len(points) < 4:
        bg = np.median(data)
        background = np.full_like(data, bg)
        return data - bg, background

    coeffs, actual_degree = _fit_surface(points, values, degree)
    background = _evaluate_surface(coeffs, actual_degree, data.shape)

    corrected = data - background
    corrected = np.clip(corrected, 0, None)

    return corrected.astype(np.float32), background.astype(np.float32)


def extract_background_dbe(data, sample_points, degree=3):
    """
    DBE: Dynamic Background Extraction.
    Usa puntos de muestreo definidos por el usuario.

    Parámetros
    ----------
    sample_points : list of (y, x)
        Coordenadas normalizadas (0-1) de los puntos de muestreo.
    """
    gray = data.mean(axis=-1) if data.ndim == 3 else data
    h, w = gray.shape

    points = np.array(sample_points, dtype=np.float32)
    values = np.array([
        gray[int(p[0] * h), int(p[1] * w)] for p in points
    ], dtype=np.float32)

    coeffs, actual_degree = _fit_surface(points, values, degree)
    background = _evaluate_surface(coeffs, actual_degree, data.shape)

    if data.ndim == 3:
        corrected = np.zeros_like(data)
        for c in range(data.shape[-1]):
            bg_c = _evaluate_surface(
                *_fit_surface(
                    points,
                    np.array([data[int(p[0]*h), int(p[1]*w), c] for p in points]),
                    degree,
                ),
                data[..., c].shape,
            )
            corrected[..., c] = np.clip(data[..., c] - bg_c, 0, None)
        return corrected.astype(np.float32), background.astype(np.float32)

    corrected = np.clip(data - background, 0, None)
    return corrected.astype(np.float32), background.astype(np.float32)
