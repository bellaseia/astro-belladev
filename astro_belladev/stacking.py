"""
stacking.py
-----------
Integracion (stacking) de varios frames ya alineados.
Optimizado para bajo consumo de memoria: procesa por bloques
(tiles) en vez de cargar todos los frames a la vez.

Metodos:
- "average": media simple
- "median": mediana (robusto)
- "sigma_clip": rechazo de outliers + media (el mejor)
"""

import numpy as np

TILE_SIZE = 256


def _process_tiles(frames, process_func, **kwargs):
    """
    Procesa frames por bloques (tiles) para ahorrar memoria.
    En vez de np.stack(todos), carga tile a tile.
    """
    h, w = frames[0].shape[:2]
    has_color = frames[0].ndim == 3
    n_channels = frames[0].shape[-1] if has_color else 1
    n_frames = len(frames)

    if has_color:
        result = np.zeros((h, w, n_channels), dtype=np.float32)
    else:
        result = np.zeros((h, w), dtype=np.float32)

    for y0 in range(0, h, TILE_SIZE):
        y1 = min(y0 + TILE_SIZE, h)
        for x0 in range(0, w, TILE_SIZE):
            x1 = min(x0 + TILE_SIZE, w)

            if has_color:
                tile_stack = np.zeros(
                    (n_frames, y1 - y0, x1 - x0, n_channels),
                    dtype=np.float32,
                )
            else:
                tile_stack = np.zeros(
                    (n_frames, y1 - y0, x1 - x0),
                    dtype=np.float32,
                )

            for i, frame in enumerate(frames):
                if has_color:
                    tile_stack[i] = frame[y0:y1, x0:x1, :]
                else:
                    tile_stack[i] = frame[y0:y1, x0:x1]

            tile_result = process_func(tile_stack, **kwargs)

            if has_color:
                result[y0:y1, x0:x1, :] = tile_result
            else:
                result[y0:y1, x0:x1] = tile_result

            del tile_stack

    return result


def _average_func(tile_stack, **kwargs):
    return np.mean(tile_stack, axis=0)


def _median_func(tile_stack, **kwargs):
    return np.median(tile_stack, axis=0)


def _sigma_clip_func(tile_stack, sigma=3.0, **kwargs):
    """Sigma clipping por tile sin astropy para ahorrar memoria."""
    n_frames = tile_stack.shape[0]
    if n_frames < 3:
        return np.mean(tile_stack, axis=0)

    for _ in range(3):
        median = np.median(tile_stack, axis=0, keepdims=True)
        std = np.std(tile_stack, axis=0, keepdims=True)
        std = np.where(std == 0, 1, std)

        mask = np.abs(tile_stack - median) > sigma * std
        tile_stack = np.where(mask, np.nan, tile_stack)

    with np.errstate(all='ignore'):
        result = np.nanmean(tile_stack, axis=0)

    result = np.nan_to_num(result, nan=0.0)
    return result.astype(np.float32)


def stack_average(frames):
    return _process_tiles(frames, _average_func)


def stack_median(frames):
    return _process_tiles(frames, _median_func)


def stack_sigma_clip(frames, sigma=3.0):
    return _process_tiles(
        frames, _sigma_clip_func, sigma=sigma
    )


def stack_frames(frames, method="sigma_clip", sigma=3.0):
    if len(frames) == 0:
        raise ValueError("No hay frames para apilar.")

    if len(frames) == 1:
        return frames[0]

    if method == "average":
        return stack_average(frames)
    elif method == "median":
        return stack_median(frames)
    elif method == "sigma_clip":
        return stack_sigma_clip(frames, sigma=sigma)
    else:
        raise ValueError(
            f"Metodo de stacking desconocido: {method}"
        )
