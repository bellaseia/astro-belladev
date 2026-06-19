"""
masks.py
--------
Máscaras para procesamiento selectivo de regiones de la imagen.

Las máscaras permiten aplicar una operación solo a ciertas zonas:
por ejemplo, reducir ruido solo en el fondo (sin tocar estrellas),
o saturar solo las nebulosas sin afectar las estrellas.

Tipos de máscara:
- Luminancia: protege zonas claras u oscuras según un umbral.
- Rango: selecciona píxeles dentro de un rango de brillo.
- Estrellas (star mask): detecta estrellas automáticamente.
- Inversa: invierte cualquier máscara.

Todas las máscaras devuelven un array float32 de 0.0 (no seleccionado)
a 1.0 (totalmente seleccionado), con transiciones suaves.
"""

import numpy as np
import cv2
from scipy.ndimage import label, binary_dilation, generate_binary_structure


def _to_luminance(data):
    if data.ndim == 3:
        return data.mean(axis=-1)
    return data


def mask_luminance(data, shadows=0.0, highlights=1.0, softness=0.1):
    """
    Máscara de luminancia: selecciona píxeles por brillo.

    Parámetros
    ----------
    shadows : float (0-1)
        Umbral inferior. Píxeles más oscuros que esto quedan fuera.
    highlights : float (0-1)
        Umbral superior. Píxeles más brillantes que esto quedan fuera.
    softness : float (0-1)
        Suavizado de los bordes de la máscara.
    """
    lum = _to_luminance(data).astype(np.float32)

    lmin = np.min(lum)
    lmax = np.max(lum)
    if lmax > lmin:
        lum_norm = (lum - lmin) / (lmax - lmin)
    else:
        return np.ones_like(lum)

    mask = np.ones_like(lum_norm)

    if softness > 0.01:
        if shadows > 0:
            mask *= np.clip((lum_norm - shadows) / softness, 0, 1)
        if highlights < 1:
            mask *= np.clip((highlights - lum_norm) / softness, 0, 1)
    else:
        mask *= (lum_norm >= shadows).astype(np.float32)
        mask *= (lum_norm <= highlights).astype(np.float32)

    return mask


def mask_range(data, low=0.2, high=0.8, softness=0.05):
    """
    Máscara de rango: selecciona píxeles dentro de un rango de brillo.
    Útil para seleccionar solo la nebulosa (tonos medios) o solo
    las estrellas brillantes.

    Parámetros
    ----------
    low, high : float (0-1)
        Rango de brillo a seleccionar.
    softness : float
        Transición suave en los bordes del rango.
    """
    return mask_luminance(data, shadows=low, highlights=high, softness=softness)


def mask_stars(data, threshold_sigma=5.0, dilation_radius=3, softness=2.0):
    """
    Máscara de estrellas: detecta estrellas automáticamente y genera
    una máscara suave alrededor de cada una.

    Parámetros
    ----------
    threshold_sigma : float
        Sigmas sobre el fondo para detectar estrellas.
    dilation_radius : int
        Radio de dilatación alrededor de cada estrella (píxeles).
    softness : float
        Sigma del desenfoque gaussiano para suavizar la máscara.
    """
    lum = _to_luminance(data).astype(np.float32)

    flat = lum.flatten()
    for _ in range(3):
        med = np.median(flat)
        std = np.std(flat)
        keep = np.abs(flat - med) < 3 * std
        flat = flat[keep]

    bg_median = np.median(flat)
    bg_std = np.std(flat)
    threshold = bg_median + threshold_sigma * bg_std

    binary = lum > threshold

    struct = generate_binary_structure(2, 2)
    for _ in range(dilation_radius):
        binary = binary_dilation(binary, structure=struct)

    mask = binary.astype(np.float32)

    if softness > 0:
        ksize = int(softness * 6) | 1
        mask = cv2.GaussianBlur(mask, (ksize, ksize), softness)

    return np.clip(mask, 0, 1)


def mask_invert(mask):
    """Invierte una máscara: lo seleccionado pasa a no seleccionado."""
    return 1.0 - mask


def apply_with_mask(original, processed, mask):
    """
    Combina imagen original y procesada usando una máscara.
    Donde mask=1.0 se usa la imagen procesada, donde mask=0.0
    se usa la original.

    Parámetros
    ----------
    original : numpy array
        Imagen sin procesar.
    processed : numpy array
        Imagen con la operación aplicada.
    mask : numpy array 2D
        Máscara de selección (0-1).
    """
    if original.shape != processed.shape:
        raise ValueError(
            f"Las imágenes deben tener el mismo tamaño: "
            f"{original.shape} vs {processed.shape}"
        )

    if original.ndim == 3:
        mask_3d = mask[..., np.newaxis]
        return (processed * mask_3d + original * (1 - mask_3d)).astype(np.float32)

    return (processed * mask + original * (1 - mask)).astype(np.float32)


def extract_starless(data, star_mask=None, threshold_sigma=5.0,
                      dilation_radius=5, softness=3.0):
    """
    Elimina estrellas de la imagen rellenando las zonas estelares
    con una interpolación del fondo circundante.

    Parámetros
    ----------
    star_mask : numpy array o None
        Máscara de estrellas. Si None, se genera automáticamente.
    threshold_sigma, dilation_radius, softness : float/int
        Parámetros para la detección de estrellas (si star_mask es None).

    Devuelve
    --------
    starless : imagen sin estrellas
    stars_only : solo las estrellas (para recombinar después)
    """
    if star_mask is None:
        star_mask = mask_stars(
            data,
            threshold_sigma=threshold_sigma,
            dilation_radius=dilation_radius,
            softness=softness,
        )

    star_binary = (star_mask > 0.5).astype(np.uint8)

    if data.ndim == 3:
        starless = np.zeros_like(data)
        for c in range(data.shape[-1]):
            channel = data[..., c].copy()
            original_max = np.max(channel) if np.max(channel) > 0 else 1.0
            ch_norm = (channel / original_max * 255).astype(np.uint8)
            inpainted = cv2.inpaint(ch_norm, star_binary, 5, cv2.INPAINT_NS)
            starless[..., c] = inpainted.astype(np.float32) / 255.0 * original_max
    else:
        original_max = np.max(data) if np.max(data) > 0 else 1.0
        data_norm = (data / original_max * 255).astype(np.uint8)
        inpainted = cv2.inpaint(data_norm, star_binary, 5, cv2.INPAINT_NS)
        starless = inpainted.astype(np.float32) / 255.0 * original_max

    star_mask_3d = star_mask[..., np.newaxis] if data.ndim == 3 else star_mask
    stars_only = data * star_mask_3d

    return starless.astype(np.float32), stars_only.astype(np.float32)


def combine_starless_stars(starless, stars_only, blend=1.0):
    """
    Recombina la imagen sin estrellas con las estrellas.
    Permite controlar la intensidad de las estrellas en el resultado.

    Parámetros
    ----------
    blend : float (0-1)
        Intensidad de las estrellas. 0 = sin estrellas, 1 = todas.
    """
    return (starless + stars_only * blend).astype(np.float32)


def reduce_star_halos(data, halo_radius=5, strength=0.7):
    """
    Reduce halos alrededor de estrellas brillantes.
    Detecta las estrellas y suaviza los bordes donde el halo
    es más pronunciado.

    Parámetros
    ----------
    halo_radius : int
        Radio de la zona de halo alrededor de cada estrella.
    strength : float (0-1)
        Intensidad de la reducción.
    """
    star_mask_tight = mask_stars(data, threshold_sigma=8.0, dilation_radius=1, softness=1.0)
    star_mask_wide = mask_stars(data, threshold_sigma=4.0, dilation_radius=halo_radius, softness=3.0)

    halo_mask = np.clip(star_mask_wide - star_mask_tight, 0, 1)

    if data.ndim == 3:
        lum = data.mean(axis=-1)
    else:
        lum = data

    bg_median = np.median(lum[halo_mask < 0.3])

    result = data.copy()
    halo_factor = 1.0 - (strength * halo_mask)

    if data.ndim == 3:
        for c in range(data.shape[-1]):
            result[..., c] = data[..., c] * halo_factor + bg_median * (1 - halo_factor) * 0.3
    else:
        result = data * halo_factor + bg_median * (1 - halo_factor) * 0.3

    return np.clip(result, 0, None).astype(np.float32)
