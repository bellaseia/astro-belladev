"""
curves.py
---------
Curvas y niveles para ajuste tonal de imágenes astronómicas.

- Niveles (Levels): ajuste de punto negro, punto medio (gamma)
  y punto blanco. Equivale al diálogo de niveles de Photoshop/GIMP.
- Curvas (Curves): transformación tonal libre definida por puntos
  de control con interpolación spline.
- Operan por canal (R, G, B, L) o sobre todos a la vez.
"""

import numpy as np
from scipy.interpolate import PchipInterpolator


def adjust_levels(data, black=0.0, midtone=0.5, white=1.0, channel=None):
    """
    Ajuste de niveles (punto negro / gamma / punto blanco).

    Parámetros
    ----------
    black : float (0-1)
        Todo lo que esté por debajo se recorta a 0.
    midtone : float (0-1)
        Punto medio (gamma). <0.5 = más oscuro, >0.5 = más claro.
    white : float (0-1)
        Todo lo que esté por encima se recorta a 1.
    channel : int o None
        Canal a ajustar (0=R, 1=G, 2=B). None = todos.
    """
    result = data.astype(np.float32).copy()

    data_min = np.min(result) if np.min(result) >= 0 else 0
    data_max = np.max(result) if np.max(result) > 0 else 1.0

    if channel is not None and result.ndim == 3:
        ch = result[..., channel]
        ch_norm = (ch - data_min) / (data_max - data_min)
        ch_norm = _apply_levels_normalized(ch_norm, black, midtone, white)
        result[..., channel] = ch_norm * (data_max - data_min) + data_min
        return result

    if result.ndim == 3:
        for c in range(result.shape[-1]):
            ch = result[..., c]
            ch_norm = (ch - data_min) / (data_max - data_min)
            ch_norm = _apply_levels_normalized(ch_norm, black, midtone, white)
            result[..., c] = ch_norm * (data_max - data_min) + data_min
        return result

    norm = (result - data_min) / (data_max - data_min)
    norm = _apply_levels_normalized(norm, black, midtone, white)
    return norm * (data_max - data_min) + data_min


def _apply_levels_normalized(data, black, midtone, white):
    """Aplica niveles sobre datos ya normalizados a 0-1."""
    result = (data - black) / max(white - black, 1e-10)
    result = np.clip(result, 0, 1)

    if midtone != 0.5 and midtone > 0:
        gamma = np.log(0.5) / np.log(midtone)
        result = np.power(result, gamma)

    return result


def adjust_curves(data, control_points=None, channel=None):
    """
    Ajuste por curva definida por puntos de control.

    Parámetros
    ----------
    control_points : list of (input, output)
        Puntos de control de la curva, en rango 0-1.
        Ejemplo: [(0, 0), (0.25, 0.15), (0.75, 0.85), (1, 1)]
        Si None, se usa una curva identidad (sin cambio).
    channel : int o None
        Canal a ajustar. None = todos.
    """
    if control_points is None:
        return data.copy()

    points = sorted(control_points, key=lambda p: p[0])

    if points[0][0] > 0:
        points.insert(0, (0.0, 0.0))
    if points[-1][0] < 1:
        points.append((1.0, 1.0))

    x_points = np.array([p[0] for p in points])
    y_points = np.array([p[1] for p in points])

    interpolator = PchipInterpolator(x_points, y_points)

    result = data.astype(np.float32).copy()
    data_min = np.min(result) if np.min(result) >= 0 else 0
    data_max = np.max(result) if np.max(result) > 0 else 1.0

    if channel is not None and result.ndim == 3:
        ch = result[..., channel]
        ch_norm = (ch - data_min) / (data_max - data_min)
        ch_norm = np.clip(interpolator(ch_norm), 0, 1)
        result[..., channel] = ch_norm * (data_max - data_min) + data_min
        return result

    if result.ndim == 3:
        for c in range(result.shape[-1]):
            ch = result[..., c]
            ch_norm = (ch - data_min) / (data_max - data_min)
            ch_norm = np.clip(interpolator(ch_norm), 0, 1)
            result[..., c] = ch_norm * (data_max - data_min) + data_min
        return result

    norm = (result - data_min) / (data_max - data_min)
    norm = np.clip(interpolator(norm), 0, 1)
    return norm * (data_max - data_min) + data_min


def get_histogram(data, bins=256, channel=None):
    """
    Calcula el histograma de la imagen para mostrar en la GUI.

    Devuelve
    --------
    dict con 'bins' (centros) y 'counts' (por canal o global).
    """
    data_min = np.min(data)
    data_max = np.max(data)

    if channel is not None and data.ndim == 3:
        counts, edges = np.histogram(data[..., channel], bins=bins,
                                      range=(data_min, data_max))
        centers = (edges[:-1] + edges[1:]) / 2
        return {"bins": centers, "counts": counts}

    if data.ndim == 3:
        result = {"bins": None}
        for c, name in enumerate(["R", "G", "B"]):
            counts, edges = np.histogram(data[..., c], bins=bins,
                                          range=(data_min, data_max))
            if result["bins"] is None:
                result["bins"] = (edges[:-1] + edges[1:]) / 2
            result[name] = counts

        luminance = data.mean(axis=-1)
        counts_l, _ = np.histogram(luminance, bins=bins,
                                    range=(data_min, data_max))
        result["L"] = counts_l
        return result

    counts, edges = np.histogram(data, bins=bins,
                                  range=(data_min, data_max))
    centers = (edges[:-1] + edges[1:]) / 2
    return {"bins": centers, "counts": counts}
