"""
star_effects.py
---------------
Efectos y ajustes sobre estrellas.

1. Star Reduction: reduce el tamano de las estrellas sin eliminarlas.
   Equivale a MorphologicalTransformation de PixInsight.

2. Diffraction Spikes: anade las puntas de difraccion artificiales
   que producen los telescopios reflectores (4, 6 u 8 puntas).
   Los refractores no las producen, pero muchos astrofotografos
   las anaden por estetica. Solo se aplican a las estrellas
   mas brillantes para un efecto natural.
"""

import numpy as np
import cv2
import math


def star_reduction(data, amount=0.5, iterations=2):
    """
    Reduce el tamano de las estrellas sin eliminarlas.
    Usa erosion morfologica seguida de restauracion del brillo
    para que las estrellas queden mas pequeñas pero mantengan
    su intensidad pico.

    Parametros
    ----------
    amount : float (0-1)
        Intensidad de la reduccion. 0.5 = moderada.
    iterations : int
        Numero de iteraciones de erosion (1-5).
    """
    if data.ndim == 3:
        from .masks import mask_stars
        star_m = mask_stars(data, threshold_sigma=5.0, dilation_radius=2, softness=1.0)

        result = data.astype(np.float32).copy()
        original_max = np.max(result) if np.max(result) > 0 else 1.0
        normalized = np.clip(result / original_max, 0, 1)
        img_uint8 = (normalized * 255).astype(np.uint8)

        lab = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2Lab)
        l_channel = lab[..., 0].astype(np.float32)

        kernel_size = max(3, int(2 * amount + 1)) | 1
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
        )

        l_eroded = l_channel.copy()
        for _ in range(iterations):
            l_eroded = cv2.erode(l_eroded, kernel)

        l_reduced = l_channel * (1 - star_m * amount) + l_eroded * (star_m * amount)

        lab[..., 0] = np.clip(l_reduced, 0, 255).astype(np.uint8)
        rgb = cv2.cvtColor(lab, cv2.COLOR_Lab2RGB)
        return rgb.astype(np.float32) / 255.0 * original_max

    kernel_size = max(3, int(2 * amount + 1)) | 1
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
    )

    result = data.astype(np.float32).copy()
    for _ in range(iterations):
        result = cv2.erode(result, kernel)

    from .masks import mask_stars
    star_m = mask_stars(data, threshold_sigma=5.0, dilation_radius=2, softness=1.0)
    blended = data * (1 - star_m * amount) + result * (star_m * amount)

    return blended.astype(np.float32)


def diffraction_spikes(data, num_spikes=4, spike_length=0.15,
                        spike_width=1.5, spike_brightness=0.7,
                        rotation_deg=0, min_star_brightness=0.3,
                        spike_color=None):
    """
    Anade puntas de difraccion artificiales a las estrellas brillantes.

    Parametros
    ----------
    num_spikes : int
        Numero de puntas (4 = tipico reflector, 6 = hexagonal,
        8 = doble araña).
    spike_length : float (0-1)
        Longitud de las puntas relativa al tamano de la imagen.
        0.15 = 15% del lado mayor.
    spike_width : float
        Ancho de las puntas en pixeles.
    spike_brightness : float (0-1)
        Brillo de las puntas relativo a la estrella.
    rotation_deg : float
        Rotacion de las puntas en grados.
    min_star_brightness : float (0-1)
        Brillo minimo (normalizado) para que una estrella
        reciba puntas. Solo las mas brillantes.
    spike_color : tuple (R, G, B) o None
        Color de las puntas. None = color de la estrella.
    """
    result = data.astype(np.float32).copy()
    h, w = result.shape[:2]
    is_color = result.ndim == 3

    gray = result.mean(axis=-1) if is_color else result
    gray_max = np.max(gray) if np.max(gray) > 0 else 1.0
    gray_norm = gray / gray_max

    from .frame_scoring import _detect_stars, _to_grayscale
    stars = _detect_stars(gray, threshold_sigma=8.0, min_area=3, max_area=500)

    if not stars:
        return result

    brightness_threshold = min_star_brightness * gray_max
    bright_stars = []
    for y_c, x_c, slc, star_data, star_mask in stars:
        peak = np.max(star_data * star_mask)
        if peak >= brightness_threshold:
            bright_stars.append((x_c, y_c, peak))

    bright_stars.sort(key=lambda s: -s[2])
    bright_stars = bright_stars[:50]

    if not bright_stars:
        return result

    max_length_px = int(max(h, w) * spike_length)
    spike_layer = np.zeros_like(result)

    for sx, sy, peak in bright_stars:
        relative_brightness = peak / gray_max
        this_length = int(max_length_px * relative_brightness)
        this_brightness = spike_brightness * relative_brightness

        if spike_color is not None:
            color = np.array(spike_color, dtype=np.float32)
        elif is_color:
            ix, iy = int(sx), int(sy)
            ix = max(0, min(ix, w - 1))
            iy = max(0, min(iy, h - 1))
            color = result[iy, ix].copy()
            color_max = np.max(color) if np.max(color) > 0 else 1
            color = color / color_max
        else:
            color = np.array([1.0])

        for spike_idx in range(num_spikes):
            angle = rotation_deg + spike_idx * (360.0 / num_spikes)
            angle_rad = math.radians(angle)

            dx = math.cos(angle_rad)
            dy = -math.sin(angle_rad)

            for dist in range(1, this_length + 1):
                falloff = 1.0 - (dist / this_length) ** 1.5
                if falloff <= 0:
                    break

                px = int(sx + dx * dist)
                py = int(sy + dy * dist)

                if 0 <= px < w and 0 <= py < h:
                    intensity = this_brightness * falloff * peak

                    for dw in range(int(-spike_width), int(spike_width) + 1):
                        perp_x = int(px - dy * dw * 0.3)
                        perp_y = int(py + dx * dw * 0.3)

                        if 0 <= perp_x < w and 0 <= perp_y < h:
                            width_falloff = 1.0 - abs(dw) / max(spike_width, 1)
                            pixel_intensity = intensity * max(width_falloff, 0)

                            if is_color:
                                spike_layer[perp_y, perp_x] = np.maximum(
                                    spike_layer[perp_y, perp_x],
                                    color * pixel_intensity,
                                )
                            else:
                                spike_layer[perp_y, perp_x] = max(
                                    spike_layer[perp_y, perp_x],
                                    pixel_intensity,
                                )

    ksize = max(3, int(spike_width * 2)) | 1
    if is_color:
        for c in range(spike_layer.shape[-1]):
            spike_layer[..., c] = cv2.GaussianBlur(
                spike_layer[..., c], (ksize, ksize), spike_width * 0.5
            )
    else:
        spike_layer = cv2.GaussianBlur(
            spike_layer, (ksize, ksize), spike_width * 0.5
        )

    result = np.maximum(result, result + spike_layer * 0.8)

    return np.clip(result, 0, None).astype(np.float32)
