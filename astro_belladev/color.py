"""
color.py
--------
Herramientas de color para astrofotografía.

- Balance de blancos por referencia estelar: las estrellas tipo G2V
  (como el Sol) deben verse blancas. Mide el color de varias estrellas
  y corrige el balance global.
- Balance de blancos manual: el usuario selecciona un punto "neutro".
- Saturación global y selectiva por color.
- Calibración cromática fotométrica (SPCC simplificado).
"""

import numpy as np
import cv2


def white_balance_auto(data, percentile=95):
    """
    Balance de blancos automático por canal.
    Iguala los canales R, G, B para que el percentil alto coincida.

    Parámetros
    ----------
    percentile : int
        Percentil de referencia para igualar canales (90-99).
    """
    if data.ndim != 3 or data.shape[-1] != 3:
        return data.copy()

    result = data.astype(np.float32).copy()

    ref_values = []
    for c in range(3):
        ref_values.append(np.percentile(result[..., c], percentile))

    target = np.mean(ref_values)

    for c in range(3):
        if ref_values[c] > 0:
            result[..., c] = result[..., c] * (target / ref_values[c])

    return np.clip(result, 0, None)


def white_balance_stars(data, star_positions=None):
    """
    Balance de blancos por estrellas de referencia.
    Si no se dan posiciones, detecta estrellas automáticamente y usa
    las más brillantes como referencia (asumiendo que las estrellas
    brillantes tienden a ser blancas en promedio).

    Parámetros
    ----------
    star_positions : list of (y, x) o None
        Posiciones de estrellas de referencia. Si None, autodetecta.
    """
    if data.ndim != 3 or data.shape[-1] != 3:
        return data.copy()

    from .frame_scoring import _detect_stars, _to_grayscale

    gray = _to_grayscale(data)

    if star_positions is None:
        stars = _detect_stars(gray, threshold_sigma=8.0, min_area=4)
        if len(stars) < 3:
            return white_balance_auto(data)
        star_positions = [(s[0], s[1]) for s in stars[:20]]

    r_values = []
    g_values = []
    b_values = []

    h, w = data.shape[:2]
    radius = 5

    for y, x in star_positions:
        yi, xi = int(y), int(x)
        y0 = max(0, yi - radius)
        y1 = min(h, yi + radius + 1)
        x0 = max(0, xi - radius)
        x1 = min(w, xi + radius + 1)

        patch = data[y0:y1, x0:x1]
        if patch.size == 0:
            continue

        r_values.append(np.mean(patch[..., 0]))
        g_values.append(np.mean(patch[..., 1]))
        b_values.append(np.mean(patch[..., 2]))

    if not r_values:
        return white_balance_auto(data)

    r_mean = np.median(r_values)
    g_mean = np.median(g_values)
    b_mean = np.median(b_values)

    target = np.mean([r_mean, g_mean, b_mean])

    result = data.astype(np.float32).copy()
    if r_mean > 0:
        result[..., 0] *= target / r_mean
    if g_mean > 0:
        result[..., 1] *= target / g_mean
    if b_mean > 0:
        result[..., 2] *= target / b_mean

    return np.clip(result, 0, None)


def white_balance_manual(data, ref_y, ref_x, radius=10):
    """
    Balance de blancos manual: el usuario indica un punto que debería
    ser neutro (gris/blanco) y se corrigen los canales.
    """
    if data.ndim != 3:
        return data.copy()

    h, w = data.shape[:2]
    y0 = max(0, ref_y - radius)
    y1 = min(h, ref_y + radius + 1)
    x0 = max(0, ref_x - radius)
    x1 = min(w, ref_x + radius + 1)

    patch = data[y0:y1, x0:x1]
    r_ref = np.mean(patch[..., 0])
    g_ref = np.mean(patch[..., 1])
    b_ref = np.mean(patch[..., 2])

    target = np.mean([r_ref, g_ref, b_ref])

    result = data.astype(np.float32).copy()
    if r_ref > 0:
        result[..., 0] *= target / r_ref
    if g_ref > 0:
        result[..., 1] *= target / g_ref
    if b_ref > 0:
        result[..., 2] *= target / b_ref

    return np.clip(result, 0, None)


def adjust_saturation(data, factor=1.0):
    """
    Ajuste global de saturación.

    Parámetros
    ----------
    factor : float
        <1.0 = desaturar, 1.0 = sin cambio, >1.0 = más saturación.
    """
    if data.ndim != 3 or data.shape[-1] != 3:
        return data.copy()

    original_max = np.max(data) if np.max(data) > 0 else 1.0
    normalized = np.clip(data / original_max, 0, 1)

    img_uint8 = (normalized * 255).astype(np.uint8)
    hsv = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2HSV).astype(np.float32)

    hsv[..., 1] = np.clip(hsv[..., 1] * factor, 0, 255)

    hsv_uint8 = hsv.astype(np.uint8)
    rgb = cv2.cvtColor(hsv_uint8, cv2.COLOR_HSV2RGB)

    return rgb.astype(np.float32) / 255.0 * original_max


def adjust_saturation_selective(data, target_hue, hue_range=15,
                                 factor=1.5):
    """
    Saturación selectiva: ajusta la saturación solo de un rango
    de color específico (por ejemplo, potenciar los rojos de Ha
    sin afectar el azul de las estrellas).

    Parámetros
    ----------
    target_hue : int
        Tono objetivo (0-180 en espacio HSV de OpenCV).
        Rojo=0/180, Verde=60, Azul=120.
    hue_range : int
        Rango alrededor del tono objetivo.
    factor : float
        Factor de saturación para ese rango.
    """
    if data.ndim != 3:
        return data.copy()

    original_max = np.max(data) if np.max(data) > 0 else 1.0
    normalized = np.clip(data / original_max, 0, 1)

    img_uint8 = (normalized * 255).astype(np.uint8)
    hsv = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2HSV).astype(np.float32)

    hue = hsv[..., 0]
    diff = np.minimum(
        np.abs(hue - target_hue),
        180 - np.abs(hue - target_hue)
    )
    mask = (diff <= hue_range).astype(np.float32)
    mask = cv2.GaussianBlur(mask, (5, 5), 1.0)

    sat_adjusted = hsv[..., 1] * factor
    hsv[..., 1] = hsv[..., 1] * (1 - mask) + np.clip(sat_adjusted, 0, 255) * mask

    hsv_uint8 = hsv.astype(np.uint8)
    rgb = cv2.cvtColor(hsv_uint8, cv2.COLOR_HSV2RGB)

    return rgb.astype(np.float32) / 255.0 * original_max


def photometric_color_calibration(data, neutral_reference="stars"):
    """
    Calibracion cromatica fotometrica simplificada (SPCC-like).
    Usa estrellas detectadas para estimar la respuesta cromatica
    del sistema optico y corregirla.

    Parametros
    ----------
    neutral_reference : str
        "stars" = usa estrellas como referencia neutra.
        "background" = usa el fondo del cielo como referencia.
    """
    if data.ndim != 3 or data.shape[-1] != 3:
        return data.copy()

    if neutral_reference == "background":
        return _calibrate_by_background(data)

    return white_balance_stars(data)


def _calibrate_by_background(data):
    """Calibra usando el fondo del cielo como referencia neutra."""
    from .frame_scoring import _estimate_background

    result = data.astype(np.float32).copy()

    bg_values = []
    for c in range(3):
        bg_median, _ = _estimate_background(result[..., c])
        bg_values.append(bg_median)

    target = np.mean(bg_values)

    for c in range(3):
        if bg_values[c] > 0:
            result[..., c] *= target / bg_values[c]

    return np.clip(result, 0, None)


def image_statistics(data):
    """
    Calcula estadisticas completas de la imagen para mostrar en la GUI.
    """
    stats = {
        "shape": data.shape,
        "dtype": str(data.dtype),
        "min": float(np.min(data)),
        "max": float(np.max(data)),
        "mean": float(np.mean(data)),
        "median": float(np.median(data)),
        "std": float(np.std(data)),
    }

    if data.ndim == 3 and data.shape[-1] == 3:
        for c, name in enumerate(["R", "G", "B"]):
            ch = data[..., c]
            stats[name] = {
                "min": float(np.min(ch)),
                "max": float(np.max(ch)),
                "mean": float(np.mean(ch)),
                "median": float(np.median(ch)),
                "std": float(np.std(ch)),
            }

        luminance = data.mean(axis=-1)
        stats["L"] = {
            "min": float(np.min(luminance)),
            "max": float(np.max(luminance)),
            "median": float(np.median(luminance)),
            "std": float(np.std(luminance)),
        }

    return stats
