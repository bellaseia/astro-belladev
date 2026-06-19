"""
alignment.py
------------
Alineación (registro) de imágenes: cada foto de la sesión tiene
ligeras diferencias de encuadre por el seguimiento de la montura,
el viento, flexiones del equipo, etc. Antes de apilar, hay que
alinear todas las imágenes sobre una de referencia.

Usamos la librería `astroalign`, que detecta patrones de estrellas
(asterismos) en cada imagen y calcula la transformación geométrica
necesaria para hacerlas coincidir. Es el mismo enfoque conceptual
que usan Siril y PixInsight para el registro de imágenes de campo
estelar.
"""

import numpy as np
import astroalign as aa


def align_frame(source, target):
    """
    Alinea `source` para que coincida con `target`.
    Devuelve la imagen alineada (mismo tamaño que target) o None
    si no se pudo encontrar suficientes estrellas en común.
    """
    try:
        if source.ndim == 3:
            # Para imágenes a color, calculamos la transformación
            # sobre un canal (luminancia aproximada) y la aplicamos
            # a los tres canales por igual.
            source_gray = source.mean(axis=-1)
            target_gray = target.mean(axis=-1) if target.ndim == 3 else target

            registered_gray, footprint = aa.register(source_gray, target_gray)
            transform, (_, _) = aa.find_transform(source_gray, target_gray)

            aligned_channels = []
            for c in range(source.shape[-1]):
                aligned_c, _ = aa.apply_transform(transform, source[..., c], target_gray)
                aligned_channels.append(aligned_c)
            aligned = np.stack(aligned_channels, axis=-1)
        else:
            aligned, footprint = aa.register(source, target)

        return aligned

    except aa.MaxIterError:
        return None


def align_all(frames, reference_index=0):
    """
    Alinea todos los frames de la lista respecto al de índice
    `reference_index`. Las imágenes que no se puedan alinear se
    descartan (con un aviso), en vez de romper todo el proceso.
    """
    reference = frames[reference_index]
    aligned_frames = [reference]

    for i, frame in enumerate(frames):
        if i == reference_index:
            continue

        aligned = align_frame(frame, reference)
        if aligned is None:
            print(f"  Aviso: no se pudo alinear el frame #{i}, se descarta.")
            continue

        aligned_frames.append(aligned)

    return aligned_frames
