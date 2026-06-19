"""
scnr.py
-------
SCNR (Subtractive Chromatic Noise Reduction) y LRGB Combine.

SCNR: elimina el exceso de verde que aparece tras el debayer
en camaras OSC. Es uno de los pasos mas usados en PixInsight.

LRGB: combina una imagen de luminancia (mono, alta SNR) con
una imagen RGB (color) para obtener lo mejor de ambas.
Esencial para usuarios de camaras monocromaticas con rueda
de filtros LRGB.
"""

import numpy as np


def scnr_average_neutral(data, amount=1.0):
    """
    SCNR Average Neutral: el metodo clasico de PixInsight.
    Reemplaza el exceso de verde por el promedio de R y B.

    Parametros
    ----------
    amount : float (0-1)
        Intensidad de la correccion. 1.0 = correccion total.
    """
    if data.ndim != 3 or data.shape[-1] != 3:
        return data.copy()

    result = data.astype(np.float32).copy()
    r = result[..., 0]
    g = result[..., 1]
    b = result[..., 2]

    neutral = (r + b) / 2.0
    mask = g > neutral
    correction = np.where(mask, neutral, g)
    result[..., 1] = g * (1 - amount) + correction * amount

    return result


def scnr_maximum_mask(data, amount=1.0):
    """
    SCNR Maximum Mask: limita el verde al maximo de R y B.
    Mas agresivo que average neutral.
    """
    if data.ndim != 3 or data.shape[-1] != 3:
        return data.copy()

    result = data.astype(np.float32).copy()
    r = result[..., 0]
    g = result[..., 1]
    b = result[..., 2]

    max_rb = np.maximum(r, b)
    mask = g > max_rb
    correction = np.where(mask, max_rb, g)
    result[..., 1] = g * (1 - amount) + correction * amount

    return result


def scnr_additive_mask(data, amount=1.0):
    """
    SCNR Additive Mask: redistribuye el exceso de verde
    entre R y B proporcionalmente. Preserva mejor el brillo.
    """
    if data.ndim != 3 or data.shape[-1] != 3:
        return data.copy()

    result = data.astype(np.float32).copy()
    r = result[..., 0]
    g = result[..., 1]
    b = result[..., 2]

    neutral = (r + b) / 2.0
    excess = np.maximum(g - neutral, 0) * amount

    result[..., 1] = g - excess
    result[..., 0] = r + excess * 0.5
    result[..., 2] = b + excess * 0.5

    return np.clip(result, 0, None)


def lrgb_combine(luminance, rgb, lum_weight=1.0):
    """
    LRGB Combine: sustituye la luminancia de la imagen RGB
    por una imagen de luminancia dedicada (mayor SNR).

    Parametros
    ----------
    luminance : numpy array 2D
        Imagen de luminancia (mono).
    rgb : numpy array (h, w, 3)
        Imagen RGB (color).
    lum_weight : float (0-1)
        Peso de la luminancia. 1.0 = sustitucion total.
    """
    if rgb.ndim != 3 or rgb.shape[-1] != 3:
        raise ValueError("rgb debe ser una imagen de 3 canales")
    if luminance.ndim != 2:
        raise ValueError("luminance debe ser una imagen mono (2D)")

    result = rgb.astype(np.float32).copy()

    rgb_lum = result.mean(axis=-1)

    lum_max = np.max(luminance) if np.max(luminance) > 0 else 1.0
    rgb_lum_max = np.max(rgb_lum) if np.max(rgb_lum) > 0 else 1.0
    lum_scaled = luminance / lum_max * rgb_lum_max

    target_lum = rgb_lum * (1 - lum_weight) + lum_scaled * lum_weight

    safe_rgb_lum = np.where(rgb_lum > 0, rgb_lum, 1.0)
    scale = target_lum / safe_rgb_lum

    for c in range(3):
        result[..., c] *= scale

    return np.clip(result, 0, None).astype(np.float32)


def lrgb_combine_lab(luminance, rgb, lum_weight=1.0):
    """
    LRGB en espacio Lab: sustituye solo el canal L sin tocar
    la crominancia. Resultado mas limpio que el metodo RGB.
    """
    import cv2

    if rgb.ndim != 3:
        raise ValueError("rgb debe ser RGB")

    rgb_max = np.max(rgb) if np.max(rgb) > 0 else 1.0
    rgb_norm = np.clip(rgb / rgb_max, 0, 1)
    rgb_uint8 = (rgb_norm * 255).astype(np.uint8)

    lab = cv2.cvtColor(rgb_uint8, cv2.COLOR_RGB2Lab).astype(np.float32)

    lum_max = np.max(luminance) if np.max(luminance) > 0 else 1.0
    lum_norm = np.clip(luminance / lum_max, 0, 1)
    lum_l = lum_norm * 255

    lab[..., 0] = lab[..., 0] * (1 - lum_weight) + lum_l * lum_weight
    lab = np.clip(lab, 0, 255).astype(np.uint8)

    result = cv2.cvtColor(lab, cv2.COLOR_Lab2RGB)
    return result.astype(np.float32) / 255.0 * rgb_max
