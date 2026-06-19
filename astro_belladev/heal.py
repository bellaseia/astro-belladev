"""
heal.py
-------
Herramienta de clonado/reparacion para eliminar artefactos.

Elimina satelites, estelas de aviones, pixeles calientes,
columnas muertas del sensor, y cualquier artefacto no deseado.
Equivale al tampón de clonar / parche de Photoshop.
"""

import numpy as np
import cv2


def remove_line(data, y1, x1, y2, x2, width=5):
    """
    Elimina una linea recta (satelite, avion) interpolando
    desde los bordes.

    Parametros
    ----------
    y1, x1, y2, x2 : int
        Coordenadas de inicio y fin de la linea.
    width : int
        Ancho de la franja a reparar (pixeles).
    """
    result = data.astype(np.float32).copy()
    h, w_img = result.shape[:2]

    mask = np.zeros((h, w_img), dtype=np.uint8)
    cv2.line(mask, (int(x1), int(y1)), (int(x2), int(y2)), 255, width)

    if result.ndim == 3:
        for c in range(result.shape[-1]):
            ch = result[..., c].copy()
            original_max = np.max(ch) if np.max(ch) > 0 else 1.0
            ch_uint8 = np.clip(ch / original_max * 255, 0, 255).astype(np.uint8)
            inpainted = cv2.inpaint(ch_uint8, mask, width + 2, cv2.INPAINT_NS)
            result[..., c] = inpainted.astype(np.float32) / 255.0 * original_max
    else:
        original_max = np.max(result) if np.max(result) > 0 else 1.0
        r_uint8 = np.clip(result / original_max * 255, 0, 255).astype(np.uint8)
        inpainted = cv2.inpaint(r_uint8, mask, width + 2, cv2.INPAINT_NS)
        result = inpainted.astype(np.float32) / 255.0 * original_max

    return result


def remove_hot_pixels(data, threshold_sigma=5.0):
    """
    Detecta y elimina pixeles calientes automaticamente.
    Un pixel caliente es mucho mas brillante que sus vecinos.
    """
    result = data.astype(np.float32).copy()

    if result.ndim == 3:
        for c in range(result.shape[-1]):
            result[..., c] = _fix_hot_channel(result[..., c], threshold_sigma)
        return result

    return _fix_hot_channel(result, threshold_sigma)


def _fix_hot_channel(channel, threshold_sigma):
    """Repara pixeles calientes en un canal."""
    from scipy.ndimage import median_filter

    local_median = median_filter(channel, size=3)
    diff = channel - local_median

    threshold = np.std(diff) * threshold_sigma
    hot_mask = diff > threshold

    result = channel.copy()
    result[hot_mask] = local_median[hot_mask]
    return result


def remove_dead_columns(data, threshold_sigma=3.0):
    """
    Detecta y repara columnas muertas del sensor.
    Una columna muerta tiene valores significativamente mas bajos
    que sus vecinas.
    """
    result = data.astype(np.float32).copy()
    gray = result.mean(axis=-1) if result.ndim == 3 else result

    col_means = np.mean(gray, axis=0)
    median_col = np.median(col_means)
    std_col = np.std(col_means)

    dead_cols = np.where(col_means < median_col - threshold_sigma * std_col)[0]

    for col in dead_cols:
        left = max(0, col - 1)
        right = min(gray.shape[1] - 1, col + 1)
        if result.ndim == 3:
            result[:, col, :] = (result[:, left, :] + result[:, right, :]) / 2
        else:
            result[:, col] = (result[:, left] + result[:, right]) / 2

    return result


def heal_region(data, mask):
    """
    Repara una region definida por una mascara usando inpainting.
    El usuario pinta la mascara sobre los artefactos en la GUI.

    Parametros
    ----------
    mask : numpy array 2D uint8
        Mascara donde 255 = zona a reparar, 0 = zona OK.
    """
    result = data.astype(np.float32).copy()
    mask_uint8 = (mask > 0.5).astype(np.uint8) * 255

    if result.ndim == 3:
        for c in range(result.shape[-1]):
            ch = result[..., c]
            original_max = np.max(ch) if np.max(ch) > 0 else 1.0
            ch_uint8 = np.clip(ch / original_max * 255, 0, 255).astype(np.uint8)
            inpainted = cv2.inpaint(ch_uint8, mask_uint8, 5, cv2.INPAINT_NS)
            result[..., c] = inpainted.astype(np.float32) / 255.0 * original_max
    else:
        original_max = np.max(result) if np.max(result) > 0 else 1.0
        r_uint8 = np.clip(result / original_max * 255, 0, 255).astype(np.uint8)
        inpainted = cv2.inpaint(r_uint8, mask_uint8, 5, cv2.INPAINT_NS)
        result = inpainted.astype(np.float32) / 255.0 * original_max

    return result


def auto_detect_satellites(data, min_length=50, threshold_sigma=5.0):
    """
    Detecta automaticamente estelas de satelites/aviones
    usando la transformada de Hough.

    Devuelve
    --------
    lines : lista de ((x1,y1), (x2,y2)) con las lineas detectadas.
    """
    gray = data.mean(axis=-1) if data.ndim == 3 else data

    flat = gray.flatten()
    for _ in range(3):
        med = np.median(flat)
        std = np.std(flat)
        mask = np.abs(flat - med) < 3 * std
        flat = flat[mask]
    bg_median = np.median(flat)
    bg_std = np.std(flat)

    signal = np.clip(gray - bg_median - threshold_sigma * bg_std, 0, None)
    signal_max = np.max(signal) if np.max(signal) > 0 else 1
    signal_uint8 = (signal / signal_max * 255).astype(np.uint8)

    edges = cv2.Canny(signal_uint8, 50, 150)

    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180,
        threshold=30,
        minLineLength=min_length,
        maxLineGap=10,
    )

    if lines is None:
        return []

    detected = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        length = np.sqrt((x2-x1)**2 + (y2-y1)**2)
        if length >= min_length:
            detected.append(((x1, y1), (x2, y2)))

    return detected
