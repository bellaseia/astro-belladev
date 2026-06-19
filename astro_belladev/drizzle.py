"""
drizzle.py
----------
Drizzle: super-resolucion por apilamiento con offsets subpixel.

Cuando apilas imagenes con pequenos desplazamientos fraccionales
entre ellas (que siempre existen por el tracking imperfecto),
puedes reconstruir una imagen con mayor resolucion que la del
sensor original.

Es como tener una camara con pixeles mas pequenos, gratis.
PixInsight y Siril lo implementan; es casi obligatorio para
el modo experto de cualquier programa serio.

Metodo:
  1. Detecta los offsets subpixel entre cada frame y la referencia.
  2. Crea una rejilla de salida con pixeles mas pequenos (2x o 3x).
  3. Coloca cada pixel de cada frame en la posicion correcta de la
     rejilla de alta resolucion, ponderado por un kernel "drop".
  4. Normaliza por la cobertura de cada pixel de salida.
"""

import numpy as np
import cv2


def _detect_subpixel_offset(source, target):
    """
    Detecta el offset subpixel entre dos imagenes usando
    correlacion cruzada en espacio de Fourier.
    Precision tipica: ~0.1 pixel.
    """
    src = source.mean(axis=-1) if source.ndim == 3 else source
    tgt = target.mean(axis=-1) if target.ndim == 3 else target

    src_f = np.fft.fft2(src)
    tgt_f = np.fft.fft2(tgt)

    cross_power = (src_f * np.conj(tgt_f))
    magnitude = np.abs(cross_power)
    magnitude[magnitude == 0] = 1
    cross_power = cross_power / magnitude

    correlation = np.fft.ifft2(cross_power).real

    h, w = correlation.shape
    peak_idx = np.unravel_index(np.argmax(correlation), (h, w))

    dy = peak_idx[0]
    dx = peak_idx[1]

    if dy > h // 2:
        dy -= h
    if dx > w // 2:
        dx -= w

    if abs(dy) < 3 and abs(dx) < 3:
        region_size = 3
        cy, cx = peak_idx
        y0 = max(0, cy - region_size)
        y1 = min(h, cy + region_size + 1)
        x0 = max(0, cx - region_size)
        x1 = min(w, cx + region_size + 1)

        region = correlation[y0:y1, x0:x1]
        if region.size > 0:
            total = np.sum(region)
            if total > 0:
                yy, xx = np.mgrid[y0:y1, x0:x1]
                dy_sub = np.sum(yy * region) / total - cy + dy
                dx_sub = np.sum(xx * region) / total - cx + dx
                if abs(dy_sub) < region_size and abs(dx_sub) < region_size:
                    dy = dy_sub
                    dx = dx_sub

    return float(dy), float(dx)


def drizzle_stack(frames, scale=2, drop_size=0.7, reference_index=0):
    """
    Apila frames con drizzle para super-resolucion.

    Parametros
    ----------
    frames : list of numpy arrays
        Frames alineados a apilar.
    scale : int
        Factor de super-resolucion (2 = doble resolucion, 3 = triple).
    drop_size : float (0-1)
        Tamano del "drop" (kernel). 0.7 es el valor clasico de Fruchter.
        Menor = mas resolucion pero mas ruido y huecos.
        Mayor = mas suave, menos huecos.
    reference_index : int
        Indice del frame de referencia.

    Devuelve
    --------
    drizzled : imagen de super-resolucion, shape original * scale.
    weight_map : mapa de cobertura (cuantos frames contribuyeron a cada pixel).
    """
    if not frames:
        raise ValueError("No hay frames para drizzle")

    if len(frames) == 1:
        result = cv2.resize(frames[0].astype(np.float32),
                             None, fx=scale, fy=scale,
                             interpolation=cv2.INTER_LANCZOS4)
        weights = np.ones(result.shape[:2], dtype=np.float32)
        return result, weights

    reference = frames[reference_index]
    h, w = reference.shape[:2]
    has_color = reference.ndim == 3
    n_channels = reference.shape[-1] if has_color else 1

    out_h = h * scale
    out_w = w * scale

    if has_color:
        accumulator = np.zeros((out_h, out_w, n_channels), dtype=np.float64)
    else:
        accumulator = np.zeros((out_h, out_w), dtype=np.float64)
    weight_map = np.zeros((out_h, out_w), dtype=np.float64)

    drop_radius = drop_size * scale / 2.0

    for i, frame in enumerate(frames):
        if i == reference_index:
            dy, dx = 0.0, 0.0
        else:
            dy, dx = _detect_subpixel_offset(frame, reference)

        frame_f = frame.astype(np.float64)

        for py in range(h):
            for px in range(w):
                out_y = (py + dy) * scale + scale / 2.0
                out_x = (px + dx) * scale + scale / 2.0

                oy_start = max(0, int(out_y - drop_radius))
                oy_end = min(out_h, int(out_y + drop_radius) + 1)
                ox_start = max(0, int(out_x - drop_radius))
                ox_end = min(out_w, int(out_x + drop_radius) + 1)

                if oy_start >= oy_end or ox_start >= ox_end:
                    continue

                if has_color:
                    accumulator[oy_start:oy_end, ox_start:ox_end] += frame_f[py, px]
                else:
                    accumulator[oy_start:oy_end, ox_start:ox_end] += frame_f[py, px]
                weight_map[oy_start:oy_end, ox_start:ox_end] += 1.0

    safe_weights = np.where(weight_map > 0, weight_map, 1.0)
    if has_color:
        for c in range(n_channels):
            accumulator[..., c] /= safe_weights
    else:
        accumulator /= safe_weights

    return accumulator.astype(np.float32), weight_map.astype(np.float32)


def drizzle_quick(frames, scale=2, reference_index=0):
    """
    Version rapida de drizzle usando interpolacion de OpenCV.
    Menos preciso que el drizzle completo pero mucho mas rapido.
    Bueno para previsualizar el resultado antes del drizzle real.
    """
    if not frames:
        raise ValueError("No hay frames para drizzle")

    reference = frames[reference_index]
    h, w = reference.shape[:2]

    out_h = h * scale
    out_w = w * scale

    upscaled_frames = []

    for i, frame in enumerate(frames):
        if i == reference_index:
            dy, dx = 0.0, 0.0
        else:
            dy, dx = _detect_subpixel_offset(frame, reference)

        upscaled = cv2.resize(frame.astype(np.float32),
                               (out_w, out_h),
                               interpolation=cv2.INTER_LANCZOS4)

        if abs(dy) > 0.01 or abs(dx) > 0.01:
            M = np.float32([
                [1, 0, dx * scale],
                [0, 1, dy * scale],
            ])
            upscaled = cv2.warpAffine(upscaled, M, (out_w, out_h))

        upscaled_frames.append(upscaled)

    stack = np.stack(upscaled_frames, axis=0)
    result = np.median(stack, axis=0)

    return result.astype(np.float32)
