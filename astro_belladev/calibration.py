"""
calibration.py
---------------
Calibración clásica de astrofotografía: bias, dark y flat.

Recordatorio rápido de qué corrige cada frame de calibración:
- BIAS:  ruido electrónico fijo del sensor a exposición ~0s.
- DARK:  corriente de oscuridad (ruido térmico), depende de la
         exposición y la temperatura del sensor.
- FLAT:  desigualdades ópticas (viñeteo, polvo en el sensor/filtros).

Fórmula de calibración estándar:

    master_bias  = mediana(bias)
    master_dark  = mediana(dark) - master_bias
    master_flat  = mediana(flat) - master_bias
    master_flat_norm = master_flat / media(master_flat)

    light_calibrado = (light - master_bias - master_dark) / master_flat_norm

Esta es una versión simplificada (asume que darks y lights tienen
la misma exposición/temperatura, y que los flats no necesitan su
propio dark). Es exactamente el punto de partida que usan Siril y
PixInsight antes de añadir opciones más avanzadas (dark scaling,
flat-darks, etc.), que añadiremos más adelante.
"""

import numpy as np


def _stack_median(frames):
    """Combina una lista de frames por mediana, pixel a pixel."""
    stack = np.stack(frames, axis=0)
    return np.median(stack, axis=0)


def create_master_bias(bias_frames):
    if not bias_frames:
        return None
    return _stack_median(bias_frames)


def create_master_dark(dark_frames, master_bias=None):
    if not dark_frames:
        return None
    master_dark = _stack_median(dark_frames)
    if master_bias is not None:
        master_dark = master_dark - master_bias
    return master_dark


def create_master_flat(flat_frames, master_bias=None):
    if not flat_frames:
        return None
    master_flat = _stack_median(flat_frames)
    if master_bias is not None:
        master_flat = master_flat - master_bias

    # Normalizamos para que el flat no cambie el brillo global,
    # solo corrija las diferencias relativas entre píxeles.
    mean_value = np.mean(master_flat)
    if mean_value == 0:
        raise ValueError("El master flat tiene media 0, revisa los frames de entrada.")
    master_flat_norm = master_flat / mean_value
    return master_flat_norm


def calibrate_light(light, master_bias=None, master_dark=None, master_flat_norm=None):
    """
    Aplica bias/dark/flat a un light frame. Cualquiera de los tres
    master frames es opcional: si no lo tienes, simplemente se omite
    ese paso (por ejemplo, si todavía no tienes flats).
    """
    calibrated = light.astype(np.float32).copy()

    if master_bias is not None:
        calibrated = calibrated - master_bias

    if master_dark is not None:
        calibrated = calibrated - master_dark

    if master_flat_norm is not None:
        # Evitamos divisiones por cero en píxeles muertos/extremos del flat.
        safe_flat = np.where(master_flat_norm == 0, 1, master_flat_norm)
        calibrated = calibrated / safe_flat

    # No permitimos valores negativos: no tienen sentido físico
    # y rompen pasos posteriores (estiramiento, etc.).
    calibrated = np.clip(calibrated, 0, None)

    return calibrated
