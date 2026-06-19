"""
ai_enhance.py
-------------
AI Upscale y mejora de imagen con super-resolucion neuronal.

Usa los modelos de super-resolucion incluidos en OpenCV DNN:
- EDSR (Enhanced Deep Super-Resolution): mejor calidad.
- ESPCN (Efficient Sub-Pixel CNN): mas rapido.
- Fallback lanczos: si no hay modelos disponibles.

Equivalente gratuito a Topaz Gigapixel AI para astrofotografia.
"""

import numpy as np
import cv2


def upscale_ai(data, scale=2, method="lanczos"):
    """
    Super-resolucion con AI o interpolacion avanzada.

    Parametros
    ----------
    scale : int
        Factor de ampliacion (2, 3 o 4).
    method : str
        "edsr" - Red neuronal EDSR (mejor calidad, requiere modelo).
        "espcn" - Red neuronal ESPCN (rapido, requiere modelo).
        "lanczos" - Interpolacion Lanczos4 (siempre disponible).
        "cubic_plus" - Bicubica mejorada con sharpening adaptativo.
    """
    if method in ("edsr", "espcn"):
        return _upscale_dnn(data, scale, method)
    elif method == "cubic_plus":
        return _upscale_cubic_enhanced(data, scale)
    else:
        return _upscale_lanczos(data, scale)


def _upscale_lanczos(data, scale):
    """Upscale con Lanczos4 (alta calidad sin AI)."""
    h, w = data.shape[:2]
    new_h, new_w = h * scale, w * scale

    result = cv2.resize(
        data.astype(np.float32), (new_w, new_h),
        interpolation=cv2.INTER_LANCZOS4,
    )
    return result.astype(np.float32)


def _upscale_cubic_enhanced(data, scale):
    """
    Upscale cubico mejorado: bicubico + sharpening adaptativo
    que refuerza bordes sin amplificar ruido.
    """
    h, w = data.shape[:2]
    new_h, new_w = h * scale, w * scale

    upscaled = cv2.resize(
        data.astype(np.float32), (new_w, new_h),
        interpolation=cv2.INTER_CUBIC,
    )

    if upscaled.ndim == 3:
        gray = upscaled.mean(axis=-1)
    else:
        gray = upscaled

    blurred = cv2.GaussianBlur(gray, (3, 3), 0.8)
    detail = gray - blurred

    noise_level = np.std(detail)
    if noise_level > 0:
        strength_map = np.abs(detail) / (noise_level * 3)
        strength_map = np.clip(strength_map, 0, 1)
    else:
        strength_map = np.ones_like(detail)

    if upscaled.ndim == 3:
        for c in range(upscaled.shape[-1]):
            ch_blurred = cv2.GaussianBlur(upscaled[..., c], (3, 3), 0.8)
            ch_detail = upscaled[..., c] - ch_blurred
            upscaled[..., c] += ch_detail * strength_map * 0.5
    else:
        upscaled += detail * strength_map * 0.5

    return np.clip(upscaled, 0, None).astype(np.float32)


def _upscale_dnn(data, scale, method):
    """Upscale con modelos DNN de OpenCV (si estan disponibles)."""
    try:
        sr = cv2.dnn_superres.DnnSuperResImpl_create()
    except AttributeError:
        print(f"  OpenCV DNN SuperRes no disponible, usando lanczos")
        return _upscale_lanczos(data, scale)

    model_names = {
        "edsr": f"EDSR_x{scale}.pb",
        "espcn": f"ESPCN_x{scale}.pb",
    }

    model_file = model_names.get(method, "")

    from pathlib import Path
    model_path = Path(__file__).parent / "models" / model_file

    if not model_path.exists():
        print(f"  Modelo {model_file} no encontrado, usando lanczos")
        return _upscale_lanczos(data, scale)

    sr.readModel(str(model_path))
    sr.setModel(method, scale)

    original_max = np.max(data) if np.max(data) > 0 else 1.0
    normalized = np.clip(data / original_max * 255, 0, 255).astype(np.uint8)

    if normalized.ndim == 2:
        normalized = cv2.cvtColor(normalized, cv2.COLOR_GRAY2BGR)
        result = sr.upsample(normalized)
        result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
    else:
        bgr = normalized[..., ::-1]
        result = sr.upsample(bgr)
        result = result[..., ::-1]

    return result.astype(np.float32) / 255.0 * original_max


def enhance_detail(data, strength=0.5, scale="fine"):
    """
    Mejora de detalle adaptativa por escalas.
    Potencia detalles finos sin amplificar ruido.

    Parametros
    ----------
    strength : float (0-1)
    scale : str
        "fine" - detalles finos (estrellas, filamentos).
        "medium" - detalles medios (estructura nebular).
        "coarse" - detalles gruesos (brazos de galaxia).
        "all" - todas las escalas.
    """
    scale_params = {
        "fine": (3, 0.8),
        "medium": (7, 1.5),
        "coarse": (15, 3.0),
    }

    if scale == "all":
        result = data.copy()
        for s in ["coarse", "medium", "fine"]:
            result = enhance_detail(result, strength * 0.7, s)
        return result

    ksize, sigma = scale_params.get(scale, (5, 1.0))

    if data.ndim == 3:
        original_max = np.max(data) if np.max(data) > 0 else 1.0
        normalized = np.clip(data / original_max, 0, 1)
        img_uint8 = (normalized * 255).astype(np.uint8)

        lab = cv2.cvtColor(img_uint8, cv2.COLOR_RGB2Lab)
        l_channel = lab[..., 0].astype(np.float32)

        blurred = cv2.GaussianBlur(l_channel, (ksize, ksize), sigma)
        detail = l_channel - blurred

        noise = np.std(detail)
        if noise > 0:
            mask = np.clip(np.abs(detail) / (noise * 2), 0, 1)
        else:
            mask = np.ones_like(detail)

        l_enhanced = l_channel + detail * strength * mask
        lab[..., 0] = np.clip(l_enhanced, 0, 255).astype(np.uint8)

        rgb = cv2.cvtColor(lab, cv2.COLOR_Lab2RGB)
        return rgb.astype(np.float32) / 255.0 * original_max

    blurred = cv2.GaussianBlur(data.astype(np.float32), (ksize, ksize), sigma)
    detail = data - blurred

    noise = np.std(detail)
    if noise > 0:
        mask = np.clip(np.abs(detail) / (noise * 2), 0, 1)
    else:
        mask = np.ones_like(detail)

    enhanced = data + detail * strength * mask
    return np.clip(enhanced, 0, None).astype(np.float32)
