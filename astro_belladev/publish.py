"""
publish.py
----------
Herramientas de publicacion: watermark, plantillas para redes
sociales, timelapse/animacion y preparacion para impresion.

Para que el usuario no necesite abrir Photoshop para las ultimas
acciones antes de compartir su trabajo.
"""

import numpy as np
import cv2
from pathlib import Path


def add_watermark(data, text, position="bottom_right", font_scale=0.6,
                   opacity=0.5, color=(255, 255, 255), margin=20):
    """
    Anade un watermark de texto a la imagen.

    Parametros
    ----------
    text : str
        Texto del watermark (nombre, fecha, equipo...).
    position : str
        "bottom_right", "bottom_left", "top_right", "top_left", "center".
    opacity : float (0-1)
        Transparencia del watermark.
    """
    result = data.copy()
    h, w = result.shape[:2]

    dmax = np.max(result) if np.max(result) > 0 else 1.0
    img_uint8 = np.clip(result / dmax * 255, 0, 255).astype(np.uint8)
    if img_uint8.ndim == 2:
        img_uint8 = cv2.cvtColor(img_uint8, cv2.COLOR_GRAY2RGB)

    (tw, th), baseline = cv2.getTextSize(
        text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1
    )

    positions = {
        "bottom_right": (w - tw - margin, h - margin),
        "bottom_left": (margin, h - margin),
        "top_right": (w - tw - margin, th + margin),
        "top_left": (margin, th + margin),
        "center": ((w - tw) // 2, (h + th) // 2),
    }
    x, y = positions.get(position, positions["bottom_right"])

    overlay = img_uint8.copy()
    cv2.putText(overlay, text, (x + 1, y + 1),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(overlay, text, (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, 1, cv2.LINE_AA)

    blended = cv2.addWeighted(img_uint8, 1 - opacity * 0.3, overlay, opacity * 0.3 + (1 - opacity * 0.3), 0)
    # Solo aplicar watermark donde hay texto
    mask = np.any(overlay != img_uint8, axis=-1)
    result_uint8 = img_uint8.copy()
    result_uint8[mask] = overlay[mask]

    return result_uint8.astype(np.float32) / 255.0 * dmax


def add_border(data, top=0, bottom=0, left=0, right=0,
               color=(0, 0, 0)):
    """
    Anade bordes de color solido alrededor de la imagen.

    Parametros
    ----------
    top, bottom, left, right : int
        Pixeles de borde en cada lado.
    color : tuple
        Color del borde.
    """
    if data.ndim == 3:
        result = cv2.copyMakeBorder(
            data.astype(np.float32),
            top, bottom, left, right,
            cv2.BORDER_CONSTANT,
            value=color,
        )
    else:
        result = cv2.copyMakeBorder(
            data.astype(np.float32),
            top, bottom, left, right,
            cv2.BORDER_CONSTANT,
            value=color[0] if isinstance(color, tuple) else color,
        )
    return result.astype(np.float32)


def prepare_for_social(data, platform="instagram", background_color=(0, 0, 0)):
    """
    Prepara la imagen para una red social con el aspect ratio correcto.

    Parametros
    ----------
    platform : str
        "instagram" (1:1), "instagram_portrait" (4:5),
        "facebook" (16:9), "twitter" (16:9),
        "youtube_thumb" (16:9), "print_4x6" (3:2).
    """
    h, w = data.shape[:2]

    ratios = {
        "instagram": (1, 1),
        "instagram_portrait": (4, 5),
        "facebook": (16, 9),
        "twitter": (16, 9),
        "youtube_thumb": (16, 9),
        "print_4x6": (3, 2),
        "print_a4": (210, 297),
    }

    rw, rh = ratios.get(platform, (1, 1))
    target_ratio = rw / rh

    current_ratio = w / h

    if abs(current_ratio - target_ratio) < 0.01:
        return data.copy()

    if current_ratio > target_ratio:
        new_h = int(w / target_ratio)
        pad_top = (new_h - h) // 2
        pad_bottom = new_h - h - pad_top
        return add_border(data, top=pad_top, bottom=pad_bottom,
                          color=background_color)
    else:
        new_w = int(h * target_ratio)
        pad_left = (new_w - w) // 2
        pad_right = new_w - w - pad_left
        return add_border(data, left=pad_left, right=pad_right,
                          color=background_color)


def create_comparison(before, after, mode="side_by_side", label_before="Antes",
                       label_after="Despues"):
    """
    Crea una imagen de comparacion antes/despues.

    Parametros
    ----------
    mode : str
        "side_by_side" - Las dos imagenes juntas horizontalmente.
        "slider" - Division vertical con linea (para la GUI).
        "blink" - Devuelve ambas para alternar (GIF).
    """
    dmax_b = np.max(before) if np.max(before) > 0 else 1.0
    dmax_a = np.max(after) if np.max(after) > 0 else 1.0

    b_uint8 = np.clip(before / dmax_b * 255, 0, 255).astype(np.uint8)
    a_uint8 = np.clip(after / dmax_a * 255, 0, 255).astype(np.uint8)

    if b_uint8.ndim == 2:
        b_uint8 = cv2.cvtColor(b_uint8, cv2.COLOR_GRAY2RGB)
    if a_uint8.ndim == 2:
        a_uint8 = cv2.cvtColor(a_uint8, cv2.COLOR_GRAY2RGB)

    h1, w1 = b_uint8.shape[:2]
    h2, w2 = a_uint8.shape[:2]

    if mode == "blink":
        return [b_uint8, a_uint8]

    if mode == "slider":
        target_h = max(h1, h2)
        target_w = max(w1, w2)
        if b_uint8.shape[:2] != (target_h, target_w):
            b_uint8 = cv2.resize(b_uint8, (target_w, target_h))
        if a_uint8.shape[:2] != (target_h, target_w):
            a_uint8 = cv2.resize(a_uint8, (target_w, target_h))

        mid = target_w // 2
        result = a_uint8.copy()
        result[:, :mid] = b_uint8[:, :mid]
        cv2.line(result, (mid, 0), (mid, target_h), (255, 255, 255), 2)
        return result

    # side_by_side
    target_h = max(h1, h2)
    if h1 != target_h:
        scale = target_h / h1
        b_uint8 = cv2.resize(b_uint8, (int(w1 * scale), target_h))
    if h2 != target_h:
        scale = target_h / h2
        a_uint8 = cv2.resize(a_uint8, (int(w2 * scale), target_h))

    gap = 4
    separator = np.zeros((target_h, gap, 3), dtype=np.uint8)

    cv2.putText(b_uint8, label_before, (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(a_uint8, label_after, (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    result = np.concatenate([b_uint8, separator, a_uint8], axis=1)
    return result


def create_timelapse_frames(frames, add_frame_number=True):
    """
    Genera frames para un timelapse/animacion a partir de una
    lista de imagenes (por ejemplo, la evolucion del apilado).

    Devuelve
    --------
    list of numpy arrays uint8 listos para guardar como GIF/video.
    """
    result_frames = []

    for i, frame in enumerate(frames):
        dmax = np.max(frame) if np.max(frame) > 0 else 1.0
        img = np.clip(frame / dmax * 255, 0, 255).astype(np.uint8)
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

        if add_frame_number:
            cv2.putText(img, f"Frame {i+1}/{len(frames)}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        result_frames.append(img)

    return result_frames


def save_gif(frames, output_path, duration_ms=200):
    """
    Guarda una lista de frames como GIF animado.
    Requiere Pillow (PIL).
    """
    try:
        from PIL import Image
    except ImportError:
        raise ImportError("Para crear GIFs necesitas: pip install Pillow")

    pil_frames = []
    for frame in frames:
        if frame.ndim == 3 and frame.shape[-1] == 3:
            rgb = frame[..., ::-1] if frame.dtype == np.uint8 else frame
            rgb = frame
        else:
            rgb = frame

        pil_frames.append(Image.fromarray(rgb))

    pil_frames[0].save(
        str(output_path),
        save_all=True,
        append_images=pil_frames[1:],
        duration=duration_ms,
        loop=0,
    )
