"""
narrowband.py
-------------
Procesamiento de imagenes narrowband (banda estrecha).

Las camaras astro con filtros narrowband capturan en longitudes
de onda especificas:
  - Ha (Hidrogeno alfa, 656nm): emision de nebulosas
  - OIII (Oxigeno III, 496/501nm): emision de planetarias y SNR
  - SII (Azufre II, 672nm): emision de regiones HII

Este modulo permite:
1. Separar/extraer canales individuales de imagenes RGB.
2. Combinar canales narrowband en paletas de color:
   - Hubble Palette (SHO): SII=R, Ha=G, OIII=B
   - HOO: Ha=R, OIII=G, OIII=B (bicolor popular)
   - Palette natural: Ha=R, (Ha+OIII)/2=G, OIII=B
   - Custom: el usuario asigna canales libremente.
3. Continuum subtraction: restar la emision del continuo estelar
   para aislar solo la senal nebular.
4. Blending de narrowband con broadband (RGB + Ha, etc.)

Flujo tipico:
  1. Capturar y apilar Ha, OIII, SII por separado
  2. Combinar con una paleta (SHO, HOO, etc.)
  3. Ajustar balance de color
  4. Opcionalmente, hacer blend con imagen broadband RGB
"""

import numpy as np


def extract_channel(data, channel):
    """
    Extrae un canal individual de una imagen RGB.

    Parametros
    ----------
    channel : int o str
        0/"R", 1/"G", 2/"B", o "L" para luminancia.
    """
    if data.ndim != 3:
        return data.copy()

    channel_map = {"R": 0, "G": 1, "B": 2, "r": 0, "g": 1, "b": 2}

    if isinstance(channel, str):
        if channel.upper() == "L":
            return data.mean(axis=-1).astype(np.float32)
        channel = channel_map.get(channel, 0)

    return data[..., channel].copy()


def combine_channels(r_data, g_data, b_data):
    """Combina tres canales mono en una imagen RGB."""
    return np.stack([
        r_data.astype(np.float32),
        g_data.astype(np.float32),
        b_data.astype(np.float32),
    ], axis=-1)


def combine_palette(channels, palette="SHO"):
    """
    Combina canales narrowband usando una paleta predefinida.

    Parametros
    ----------
    channels : dict
        Diccionario con los canales: {"Ha": array, "OIII": array, "SII": array}
        Cada array es 2D (mono).
    palette : str
        "SHO" (Hubble), "HOO" (bicolor), "natural", o "HOS".
    """
    ha = channels.get("Ha")
    oiii = channels.get("OIII")
    sii = channels.get("SII")

    palettes = {
        "SHO": {"R": sii, "G": ha, "B": oiii},
        "HOO": {"R": ha, "G": oiii, "B": oiii},
        "HOS": {"R": ha, "G": oiii, "B": sii},
        "OHS": {"R": oiii, "G": ha, "B": sii},
    }

    if palette == "natural":
        if ha is None or oiii is None:
            raise ValueError("Paleta 'natural' necesita al menos Ha y OIII")
        r = ha
        g = (ha * 0.5 + oiii * 0.5) if sii is None else (ha * 0.3 + sii * 0.3 + oiii * 0.4)
        b = oiii
        return combine_channels(r, g, b)

    if palette not in palettes:
        raise ValueError(
            f"Paleta desconocida: {palette}. "
            f"Usa: {list(palettes.keys()) + ['natural']}"
        )

    mapping = palettes[palette]

    for color, data in mapping.items():
        if data is None:
            raise ValueError(
                f"Paleta '{palette}' necesita el canal que falta para {color}"
            )

    return combine_channels(
        mapping["R"], mapping["G"], mapping["B"]
    )


def combine_custom(channels, r_channel, g_channel, b_channel,
                    r_weight=1.0, g_weight=1.0, b_weight=1.0):
    """
    Combinacion personalizada: el usuario elige que canal va a R, G, B
    y con que peso.

    Parametros
    ----------
    channels : dict
        {"Ha": array, "OIII": array, "SII": array, ...}
    r_channel, g_channel, b_channel : str
        Nombre del canal para cada color ("Ha", "OIII", "SII").
    r_weight, g_weight, b_weight : float
        Pesos para cada canal (0-2).
    """
    r = channels[r_channel].astype(np.float32) * r_weight
    g = channels[g_channel].astype(np.float32) * g_weight
    b = channels[b_channel].astype(np.float32) * b_weight

    return combine_channels(r, g, b)


def continuum_subtraction(narrowband, broadband, factor=1.0):
    """
    Resta el continuo estelar de una imagen narrowband.
    Aisla solo la emision nebular, eliminando las estrellas.

    Parametros
    ----------
    narrowband : numpy array
        Imagen narrowband (ej: Ha).
    broadband : numpy array
        Imagen broadband del mismo campo (ej: luminancia o R).
    factor : float
        Factor de escala para el broadband antes de restar.
        Ajustar hasta que las estrellas desaparezcan sin dejar
        artefactos negativos.
    """
    nb = narrowband.astype(np.float32)
    bb = broadband.astype(np.float32)

    if nb.shape != bb.shape:
        raise ValueError(
            f"Las imagenes deben tener el mismo tamano: "
            f"{nb.shape} vs {bb.shape}"
        )

    bb_median = np.median(bb)
    nb_median = np.median(nb)

    if bb_median > 0:
        bb_scaled = bb * (nb_median / bb_median) * factor
    else:
        bb_scaled = bb * factor

    result = nb - bb_scaled
    return np.clip(result, 0, None).astype(np.float32)


def blend_narrowband_rgb(rgb_data, narrowband_data, blend_channel="R",
                          blend_mode="screen", opacity=0.5):
    """
    Mezcla una imagen narrowband con una imagen broadband RGB.
    Tipico: anadir senal Ha al canal rojo de una imagen RGB.

    Parametros
    ----------
    rgb_data : numpy array (h, w, 3)
        Imagen broadband RGB.
    narrowband_data : numpy array (h, w)
        Imagen narrowband mono (ej: Ha).
    blend_channel : str
        "R", "G", "B" o "L" (luminancia).
    blend_mode : str
        "screen" (aditivo suave), "add" (suma directa),
        "max" (tomar el mayor).
    opacity : float (0-1)
        Opacidad de la mezcla.
    """
    result = rgb_data.astype(np.float32).copy()
    nb = narrowband_data.astype(np.float32)

    nb_max = np.max(nb) if np.max(nb) > 0 else 1.0
    rgb_max = np.max(result) if np.max(result) > 0 else 1.0

    nb_norm = nb / nb_max
    result_norm = result / rgb_max

    if blend_channel.upper() == "L":
        lum = result_norm.mean(axis=-1)
        if blend_mode == "screen":
            blended_lum = 1.0 - (1.0 - lum) * (1.0 - nb_norm * opacity)
        elif blend_mode == "add":
            blended_lum = lum + nb_norm * opacity
        else:
            blended_lum = np.maximum(lum, nb_norm * opacity)

        safe_lum = np.where(lum > 0, lum, 1.0)
        scale = blended_lum / safe_lum
        for c in range(3):
            result_norm[..., c] *= scale
    else:
        ch_idx = {"R": 0, "G": 1, "B": 2}[blend_channel.upper()]
        ch = result_norm[..., ch_idx]

        if blend_mode == "screen":
            blended = 1.0 - (1.0 - ch) * (1.0 - nb_norm * opacity)
        elif blend_mode == "add":
            blended = ch + nb_norm * opacity
        else:
            blended = np.maximum(ch, nb_norm * opacity)

        result_norm[..., ch_idx] = blended

    result_norm = np.clip(result_norm, 0, 1)
    return (result_norm * rgb_max).astype(np.float32)


def normalize_channels(channels):
    """
    Normaliza todos los canales narrowband al mismo rango.
    Importante antes de combinar con una paleta, para que
    ningun canal domine sobre los otros.
    """
    normalized = {}
    for name, data in channels.items():
        d = data.astype(np.float32)
        dmin = np.min(d)
        dmax = np.max(d)
        if dmax > dmin:
            normalized[name] = (d - dmin) / (dmax - dmin)
        else:
            normalized[name] = np.zeros_like(d)
    return normalized
