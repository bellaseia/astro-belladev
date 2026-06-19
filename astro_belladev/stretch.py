"""
stretch.py
----------
Estiramiento (stretch) de imágenes astronómicas.

Las imágenes apiladas salen en formato lineal: casi todo negro con
poquísima señal visible. El stretch aplica una curva no lineal para
revelar las estructuras débiles sin quemar las brillantes.

Modos de stretch disponibles:
- "auto": Statistical Stretch adaptativo, analiza la distribución
  de la imagen y elige los parámetros automáticamente.
- "midtone" (MTF): Midtone Transfer Function, el algoritmo clásico
  de PixInsight (STF/AutoStretch). Mapea un punto medio seleccionado
  al 50% de brillo usando una función hiperbólica.
- "asinh": Arcsinh stretch, preserva mejor los colores que el
  logarítmico. Usado en surveys astronómicos profesionales (SDSS).

Perfiles por tipo de target:
- "nebula": potencia señal débil, agresivo en las sombras.
- "galaxy": preserva detalle en el núcleo, stretch más suave.
- "starfield": control de saturación estelar, colores preservados.
- "planetary": máximo contraste en rango dinámico reducido.
"""

import numpy as np


TARGET_PROFILES = {
    "nebula": {
        "method": "midtone",
        "midtone": 0.20,
        "black_clip": -2.0,
        "description": "Nebulosas: potencia señal débil de emisión",
    },
    "galaxy": {
        "method": "midtone",
        "midtone": 0.30,
        "black_clip": -1.5,
        "description": "Galaxias: preserva detalle en núcleo brillante",
    },
    "starfield": {
        "method": "asinh",
        "asinh_a": 0.02,
        "black_clip": -2.0,
        "description": "Campos estelares: colores estelares preservados",
    },
    "planetary": {
        "method": "midtone",
        "midtone": 0.40,
        "black_clip": -1.0,
        "description": "Planetarias/planetas: máximo contraste fino",
    },
}


def _estimate_stats(data):
    """Estadísticas robustas del fondo con sigma-clipping."""
    flat = data.flatten()
    for _ in range(3):
        med = np.median(flat)
        std = np.std(flat)
        mask = np.abs(flat - med) < 3 * std
        flat = flat[mask]
    return float(np.median(flat)), float(np.std(flat))


def _normalize_to_01(data):
    """Normaliza datos a rango [0, 1]."""
    dmin = np.min(data)
    dmax = np.max(data)
    if dmax == dmin:
        return np.zeros_like(data, dtype=np.float32)
    return ((data - dmin) / (dmax - dmin)).astype(np.float32)


def _mtf(x, midtone):
    """
    Midtone Transfer Function (PixInsight STF).
    Mapea el valor x (0-1) usando el punto medio `midtone`.
    """
    if midtone == 0.0:
        return np.zeros_like(x)
    if midtone == 1.0:
        return np.ones_like(x)
    if midtone == 0.5:
        return x

    return ((midtone - 1.0) * x) / (
        (2.0 * midtone - 1.0) * x - midtone
    )


def stretch_midtone(data, midtone=0.25, black_clip=-2.8):
    """
    Stretch por Midtone Transfer Function.

    Parámetros
    ----------
    midtone : float (0-1)
        Punto medio del stretch. Valores más bajos = stretch más
        agresivo (más detalle en las sombras). 0.25 es un buen
        punto de partida para nebulosas.
    black_clip : float
        Múltiplo de sigma por debajo de la mediana para recortar
        el punto negro. -2.8 es el estándar de PixInsight.
    """
    result = data.astype(np.float32).copy()

    if result.ndim == 3:
        channels = []
        for c in range(result.shape[-1]):
            channels.append(stretch_midtone(result[..., c], midtone, black_clip))
        return np.stack(channels, axis=-1)

    bg_median, bg_std = _estimate_stats(result)
    black_point = bg_median + black_clip * bg_std
    black_point = max(0, black_point)

    result = result - black_point
    result = np.clip(result, 0, None)

    result = _normalize_to_01(result)

    result = _mtf(result, midtone)

    return np.clip(result, 0.0, 1.0)


def stretch_asinh(data, a=0.02, black_clip=-2.8):
    """
    Stretch por arcsinh (arcoseno hiperbólico).
    Preserva ratios de color mejor que el logarítmico.

    Parámetros
    ----------
    a : float
        Factor de suavizado. Valores menores = stretch más agresivo.
        0.02 es bueno para campos estelares, 0.1 para galaxias.
    """
    result = data.astype(np.float32).copy()

    if result.ndim == 3:
        luminance = result.mean(axis=-1)
        bg_median, bg_std = _estimate_stats(luminance)
        black_point = max(0, bg_median + black_clip * bg_std)

        result = result - black_point
        result = np.clip(result, 0, None)

        luminance = result.mean(axis=-1)
        lum_max = np.max(luminance)
        if lum_max > 0:
            luminance = luminance / lum_max

        stretched_lum = np.arcsinh(luminance / a) / np.arcsinh(1.0 / a)

        safe_lum = np.where(luminance > 0, luminance, 1.0)
        scale = stretched_lum / safe_lum

        result = result / lum_max if lum_max > 0 else result
        for c in range(result.shape[-1]):
            result[..., c] = result[..., c] * scale

        return np.clip(result, 0.0, 1.0)

    bg_median, bg_std = _estimate_stats(result)
    black_point = max(0, bg_median + black_clip * bg_std)
    result = result - black_point
    result = np.clip(result, 0, None)
    result = _normalize_to_01(result)

    result = np.arcsinh(result / a) / np.arcsinh(1.0 / a)

    return np.clip(result, 0.0, 1.0)


def stretch_auto(data, target_type=None):
    """
    Stretch automático: analiza la imagen y aplica el perfil óptimo.

    Si se especifica target_type ("nebula", "galaxy", "starfield",
    "planetary"), usa el perfil predefinido. Si no, detecta
    automáticamente el perfil más adecuado.

    Parámetros
    ----------
    data : numpy array float32
        Imagen apilada en formato lineal.
    target_type : str o None
        Tipo de objeto. Si None, se autodetecta.
    """
    if target_type is None:
        target_type = _detect_target_type(data)

    profile = TARGET_PROFILES[target_type]
    method = profile["method"]

    print(f"  Stretch: perfil '{target_type}' — {profile['description']}")

    if method == "midtone":
        return stretch_midtone(
            data,
            midtone=profile["midtone"],
            black_clip=profile["black_clip"],
        )
    elif method == "asinh":
        return stretch_asinh(
            data,
            a=profile["asinh_a"],
            black_clip=profile["black_clip"],
        )


def _detect_target_type(data):
    """
    Heurística para detectar el tipo de objeto en la imagen.

    Analiza la distribución de intensidades y la concentración
    espacial de la señal para distinguir entre nebulosas, galaxias,
    campos estelares y planetarias.
    """
    gray = data.mean(axis=-1) if data.ndim == 3 else data.copy()

    bg_median, bg_std = _estimate_stats(gray)

    threshold = bg_median + 5 * bg_std
    signal_mask = gray > threshold
    signal_fraction = np.mean(signal_mask)

    if signal_fraction < 0.001:
        return "nebula"

    if signal_fraction > 0.05:
        return "starfield"

    h, w = gray.shape
    center_region = gray[h//4:3*h//4, w//4:3*w//4]
    border_region = np.concatenate([
        gray[:h//4, :].flatten(),
        gray[3*h//4:, :].flatten(),
        gray[:, :w//4].flatten(),
        gray[:, 3*w//4:].flatten(),
    ])

    center_signal = np.mean(center_region > threshold)
    border_signal = np.mean(border_region > threshold)

    if center_signal > 0 and border_signal > 0:
        concentration = center_signal / max(border_signal, 1e-10)
    else:
        concentration = 1.0

    if concentration > 5.0:
        if signal_fraction < 0.01:
            return "planetary"
        return "galaxy"

    return "nebula"


def stretch_image(data, method="auto", target_type=None, **kwargs):
    """
    Punto de entrada principal para el stretch.

    Parámetros
    ----------
    method : str
        "auto" (defecto), "midtone", "asinh"
    target_type : str o None
        Para method="auto": tipo de target o None para autodetectar.
    **kwargs : dict
        Parámetros adicionales para el método específico (modo experto).
    """
    if method == "auto":
        return stretch_auto(data, target_type=target_type)
    elif method == "midtone":
        midtone = kwargs.get("midtone", 0.25)
        black_clip = kwargs.get("black_clip", -2.8)
        return stretch_midtone(data, midtone=midtone, black_clip=black_clip)
    elif method == "asinh":
        a = kwargs.get("a", 0.02)
        black_clip = kwargs.get("black_clip", -2.8)
        return stretch_asinh(data, a=a, black_clip=black_clip)
    else:
        raise ValueError(f"Método de stretch desconocido: {method}")
