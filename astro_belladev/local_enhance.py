"""
local_enhance.py
----------------
Ecualización local de histograma (CLAHE) y contraste local.

CLAHE revela detalle debil en zonas oscuras sin quemar las
brillantes. Es como hacer un stretch localizado en cada zona
de la imagen. Muy util para nebulosas con mucho rango dinamico.
"""

import numpy as np
import cv2


def clahe(data, clip_limit=2.0, grid_size=8):
    """
    CLAHE: Contrast Limited Adaptive Histogram Equalization.
    Ecualiza el histograma localmente en bloques de la imagen.

    Parametros
    ----------
    clip_limit : float
        Limite de contraste (1-10). Mayor = mas contraste local.
    grid_size : int
        Tamano de la rejilla de bloques (4-16). Mayor = mas local.
    """
    grid_size = int(grid_size)
    clip_limit = float(clip_limit)

    if data.ndim == 3:
        original_max = np.max(data) if np.max(data) > 0 else 1.0
        normalized = np.clip(data / original_max, 0, 1)
        img_uint8 = (normalized * 255).astype(np.uint8)

        lab = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2Lab)
        clahe_obj = cv2.createCLAHE(
            clipLimit=clip_limit,
            tileGridSize=(grid_size, grid_size),
        )
        lab[..., 0] = clahe_obj.apply(lab[..., 0])
        result = cv2.cvtColor(lab, cv2.COLOR_Lab2RGB)
        return result.astype(np.float32) / 255.0 * original_max

    original_max = np.max(data) if np.max(data) > 0 else 1.0
    normalized = np.clip(data / original_max * 255, 0, 255).astype(np.uint8)

    clahe_obj = cv2.createCLAHE(
        clipLimit=clip_limit,
        tileGridSize=(grid_size, grid_size),
    )
    result = clahe_obj.apply(normalized)
    return result.astype(np.float32) / 255.0 * original_max


def local_contrast(data, radius=50, strength=0.5):
    """
    Contraste local: potencia la diferencia entre cada pixel
    y su entorno. Revela textura y estructura.

    Parametros
    ----------
    radius : int
        Radio del entorno local (pixeles).
    strength : float (0-1)
        Intensidad del efecto.
    """
    if data.ndim == 3:
        original_max = np.max(data) if np.max(data) > 0 else 1.0
        normalized = np.clip(data / original_max, 0, 1)
        img_uint8 = (normalized * 255).astype(np.uint8)

        lab = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2Lab)
        l_channel = lab[..., 0].astype(np.float32)

        ksize = radius * 2 + 1
        local_mean = cv2.GaussianBlur(l_channel, (ksize, ksize), radius / 3)
        detail = l_channel - local_mean

        l_enhanced = l_channel + detail * strength
        lab[..., 0] = np.clip(l_enhanced, 0, 255).astype(np.uint8)

        result = cv2.cvtColor(lab, cv2.COLOR_Lab2RGB)
        return result.astype(np.float32) / 255.0 * original_max

    ksize = radius * 2 + 1
    local_mean = cv2.GaussianBlur(
        data.astype(np.float32), (ksize, ksize), radius / 3
    )
    detail = data - local_mean
    result = data + detail * strength
    return np.clip(result, 0, None).astype(np.float32)
