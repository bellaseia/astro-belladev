"""
sharpen.py
----------
Nitidez (sharpening) para imágenes astronómicas.

Métodos disponibles:
- Unsharp Mask (USM): el clásico. Resta una versión borrosa de la
  imagen para potenciar los detalles finos. Rápido y predecible.
- Deconvolution (Richardson-Lucy): recupera detalle real perdido
  por el seeing/óptica. Más lento pero teóricamente superior al USM
  porque modela la PSF real del sistema óptico.
- Solo luminancia: aplica la nitidez solo al canal L, preservando
  el color sin amplificar ruido cromático.
"""

import numpy as np
import cv2
from scipy.signal import fftconvolve


def sharpen_unsharp_mask(data, radius=2.0, amount=1.0, threshold=0):
    """
    Unsharp Mask: potencia detalles finos.

    Parámetros
    ----------
    radius : float
        Radio del desenfoque gaussiano (píxeles). Mayor = detalles
        más gruesos.
    amount : float
        Intensidad del efecto (1.0 = normal, 2.0 = fuerte).
    threshold : int
        Diferencia mínima para aplicar el efecto (0-255 escala).
        Evita amplificar ruido en zonas planas.
    """
    if data.ndim == 3:
        return _sharpen_luminance_only(
            data, lambda d: sharpen_unsharp_mask(d, radius, amount, threshold)
        )

    original_max = np.max(data) if np.max(data) > 0 else 1.0
    normalized = (data / original_max).astype(np.float32)

    ksize = int(radius * 4) | 1
    blurred = cv2.GaussianBlur(normalized, (ksize, ksize), radius)

    detail = normalized - blurred

    if threshold > 0:
        threshold_f = threshold / 255.0
        mask = np.abs(detail) > threshold_f
        detail = detail * mask

    sharpened = normalized + amount * detail
    sharpened = np.clip(sharpened, 0, 1)

    return (sharpened * original_max).astype(np.float32)


def sharpen_deconvolution(data, psf_sigma=1.5, iterations=15):
    """
    Richardson-Lucy deconvolution: recupera detalle perdido por
    el seeing y las aberraciones ópticas.

    Parámetros
    ----------
    psf_sigma : float
        Sigma de la PSF gaussiana estimada (en píxeles).
        Típicamente entre 1.0 y 3.0 para astrofotografía.
    iterations : int
        Nº de iteraciones. Más = más detalle pero riesgo de
        amplificar ruido (10-30 es un rango razonable).
    """
    if data.ndim == 3:
        return _sharpen_luminance_only(
            data, lambda d: sharpen_deconvolution(d, psf_sigma, iterations)
        )

    original_max = np.max(data) if np.max(data) > 0 else 1.0
    normalized = data / original_max
    normalized = np.clip(normalized, 1e-10, None)

    size = int(psf_sigma * 6) | 1
    y, x = np.mgrid[-size//2:size//2+1, -size//2:size//2+1]
    psf = np.exp(-(x**2 + y**2) / (2 * psf_sigma**2))
    psf = psf / psf.sum()

    psf_mirror = psf[::-1, ::-1]

    estimate = normalized.copy()

    for _ in range(iterations):
        blurred = fftconvolve(estimate, psf, mode='same')
        blurred = np.clip(blurred, 1e-10, None)
        ratio = normalized / blurred
        correction = fftconvolve(ratio, psf_mirror, mode='same')
        estimate = estimate * correction
        estimate = np.clip(estimate, 0, None)

    estimate = np.clip(estimate, 0, 1)
    return (estimate * original_max).astype(np.float32)


def _sharpen_luminance_only(data, sharpen_func):
    """
    Aplica sharpening solo al canal de luminancia (L en Lab),
    preservando la crominancia intacta.
    """
    original_max = np.max(data) if np.max(data) > 0 else 1.0
    normalized = (data / original_max * 255).astype(np.uint8)

    lab = cv2.cvtColor(normalized, cv2.COLOR_RGB2Lab)

    l_channel = lab[..., 0].astype(np.float32)
    l_sharpened = sharpen_func(l_channel)

    l_max = np.max(l_sharpened) if np.max(l_sharpened) > 0 else 1.0
    lab[..., 0] = np.clip(l_sharpened / l_max * 255, 0, 255).astype(np.uint8)

    rgb_result = cv2.cvtColor(lab, cv2.COLOR_Lab2RGB)
    return rgb_result.astype(np.float32) / 255.0 * original_max


def sharpen_image(data, method="unsharp_mask", **kwargs):
    """
    Punto de entrada principal para nitidez.

    Parámetros
    ----------
    method : str
        "unsharp_mask" (defecto) o "deconvolution".
    """
    if method == "unsharp_mask":
        radius = kwargs.get("radius", 2.0)
        amount = kwargs.get("amount", 1.0)
        threshold = kwargs.get("threshold", 0)
        return sharpen_unsharp_mask(data, radius, amount, threshold)
    elif method == "deconvolution":
        psf_sigma = kwargs.get("psf_sigma", 1.5)
        iterations = kwargs.get("iterations", 15)
        return sharpen_deconvolution(data, psf_sigma, iterations)
    else:
        raise ValueError(f"Método de sharpen desconocido: {method}")
