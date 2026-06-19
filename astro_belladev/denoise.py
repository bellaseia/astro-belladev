"""
denoise.py
----------
Reducción de ruido para imágenes astronómicas.

Métodos disponibles:
- Bilateral filter: preserva bordes (bueno para nebulosas con
  estructura fina). Filtra en espacio y en intensidad a la vez.
- Non-local means (NLM): busca parches similares en toda la imagen
  y los promedia. Mejor calidad que bilateral, más lento.
- Denoise selectivo: aplica distinta intensidad a luminancia
  (más agresivo) y crominancia (más suave), que es como lo hacen
  PixInsight y SASpro.

Todos operan en float32 y preservan el rango dinámico original.
"""

import numpy as np
import cv2


def denoise_bilateral(data, d=9, sigma_color=75.0, sigma_space=75.0):
    """
    Filtro bilateral: reduce ruido preservando bordes.

    Parámetros
    ----------
    d : int
        Diámetro del vecindario (píxeles). Mayor = más suavizado.
    sigma_color : float
        Rango de intensidad del filtro. Mayor = mezcla más tonos.
    sigma_space : float
        Rango espacial. Mayor = vecindario más amplio.
    """
    original_max = np.max(data) if np.max(data) > 0 else 1.0

    if data.ndim == 3:
        normalized = (data / original_max * 255).astype(np.uint8)
        filtered = cv2.bilateralFilter(normalized, d, sigma_color, sigma_space)
        return filtered.astype(np.float32) / 255.0 * original_max

    normalized = (data / original_max * 255).astype(np.uint8)
    filtered = cv2.bilateralFilter(normalized, d, sigma_color, sigma_space)
    return filtered.astype(np.float32) / 255.0 * original_max


def denoise_nlm(data, h=10.0, template_size=7, search_size=21):
    """
    Non-Local Means: máxima calidad de denoising.

    Parámetros
    ----------
    h : float
        Intensidad del filtrado. Mayor = más suavizado.
    template_size : int
        Tamaño del parche de comparación (impar).
    search_size : int
        Tamaño de la ventana de búsqueda (impar).
    """
    original_max = np.max(data) if np.max(data) > 0 else 1.0

    if data.ndim == 3:
        normalized = (data / original_max * 255).astype(np.uint8)
        filtered = cv2.fastNlMeansDenoisingColored(
            normalized, None, h, h,
            template_size, search_size
        )
        return filtered.astype(np.float32) / 255.0 * original_max

    normalized = (data / original_max * 255).astype(np.uint8)
    filtered = cv2.fastNlMeansDenoising(
        normalized, None, h, template_size, search_size
    )
    return filtered.astype(np.float32) / 255.0 * original_max


def denoise_selective(data, lum_strength=0.7, chrom_strength=0.3, method="nlm"):
    """
    Denoise selectivo: luminancia y crominancia por separado.
    La luminancia se filtra más agresivamente (contiene la mayoría
    del ruido visible), mientras que la crominancia se filtra más
    suave para preservar el color.

    Parámetros
    ----------
    lum_strength : float (0-1)
        Intensidad del filtrado de luminancia. 1.0 = máximo.
    chrom_strength : float (0-1)
        Intensidad del filtrado cromático. 1.0 = máximo.
    method : str
        "bilateral" o "nlm".
    """
    if data.ndim != 3 or data.shape[-1] != 3:
        if method == "nlm":
            return denoise_nlm(data, h=lum_strength * 20)
        return denoise_bilateral(data, sigma_color=lum_strength * 150)

    original_max = np.max(data) if np.max(data) > 0 else 1.0
    normalized = (data / original_max * 255).astype(np.uint8)

    lab = cv2.cvtColor(normalized, cv2.COLOR_RGB2Lab)

    l_channel = lab[..., 0]
    a_channel = lab[..., 1]
    b_channel = lab[..., 2]

    lum_h = lum_strength * 20
    chrom_h = chrom_strength * 15

    if method == "nlm":
        l_filtered = cv2.fastNlMeansDenoising(l_channel, None, lum_h, 7, 21)
        a_filtered = cv2.fastNlMeansDenoising(a_channel, None, chrom_h, 7, 21)
        b_filtered = cv2.fastNlMeansDenoising(b_channel, None, chrom_h, 7, 21)
    else:
        d = 9
        l_filtered = cv2.bilateralFilter(l_channel, d, lum_strength * 150, 75)
        a_filtered = cv2.bilateralFilter(a_channel, d, chrom_strength * 100, 75)
        b_filtered = cv2.bilateralFilter(b_channel, d, chrom_strength * 100, 75)

    lab_filtered = np.stack([l_filtered, a_filtered, b_filtered], axis=-1)
    rgb_filtered = cv2.cvtColor(lab_filtered, cv2.COLOR_Lab2RGB)

    return rgb_filtered.astype(np.float32) / 255.0 * original_max


def denoise_image(data, method="selective", strength=0.5, **kwargs):
    """
    Punto de entrada principal para reducción de ruido.

    Parámetros
    ----------
    method : str
        "bilateral", "nlm" o "selective" (defecto).
    strength : float (0-1)
        Intensidad global del filtrado.
    """
    if method == "bilateral":
        sigma = strength * 150
        return denoise_bilateral(data, sigma_color=sigma, sigma_space=75)
    elif method == "nlm":
        h = strength * 20
        return denoise_nlm(data, h=h)
    elif method == "selective":
        lum_s = kwargs.get("lum_strength", strength)
        chrom_s = kwargs.get("chrom_strength", strength * 0.5)
        base_method = kwargs.get("base_method", "nlm")
        return denoise_selective(data, lum_s, chrom_s, base_method)
    else:
        raise ValueError(f"Método de denoise desconocido: {method}")
