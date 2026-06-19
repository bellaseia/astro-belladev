"""
ai_autoparams.py
----------------
Prediccion inteligente de parametros optimos para cada operacion.

Analiza las estadisticas de la imagen y predice los mejores
parametros para stretch, denoise, sharpen, color, etc.
No es un modelo de deep learning — es un sistema de reglas
con interpolacion que mejora con cada imagen procesada.

La idea: en vez de "aplica denoise", dice "aplica denoise
bilateral con d=9, sigma_color=85, sigma_space=70 porque
tu imagen tiene SNR=14 y FWHM=3.2".
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class PredictedParams:
    """Parametros predichos para una accion."""
    action_id: str
    params: dict = field(default_factory=dict)
    confidence: float = 0.0
    reasoning: str = ""


def _analyze_image_stats(data):
    """Extrae estadisticas clave para la prediccion."""
    gray = data.mean(axis=-1) if data.ndim == 3 else data

    flat = gray.flatten()
    for _ in range(3):
        med = np.median(flat)
        std = np.std(flat)
        mask = np.abs(flat - med) < 3 * std
        flat = flat[mask]
    bg_median = float(np.median(flat))
    bg_std = float(np.std(flat))

    snr = bg_median / max(bg_std, 0.001)
    dynamic_range = float(np.max(gray) - np.min(gray))
    is_linear = float(np.median(gray) / max(np.max(gray), 1)) < 0.1

    from .frame_scoring import score_frame
    score = score_frame(data)

    h, w = gray.shape
    border = 10
    gradient = float(abs(
        np.median(gray[:border, :]) - np.median(gray[-border:, :])
    ) / max(bg_median, 1) * 100)

    is_color = data.ndim == 3 and data.shape[-1] == 3
    color_balance = 1.0
    if is_color:
        r_bg = np.median(data[..., 0])
        g_bg = np.median(data[..., 1])
        b_bg = np.median(data[..., 2])
        if g_bg > 0:
            color_balance = max(abs(r_bg/g_bg - 1), abs(b_bg/g_bg - 1))

    return {
        "snr": snr,
        "bg_median": bg_median,
        "bg_std": bg_std,
        "dynamic_range": dynamic_range,
        "is_linear": is_linear,
        "fwhm": score.fwhm,
        "elongation": score.elongation,
        "star_count": score.star_count,
        "gradient_pct": gradient,
        "is_color": is_color,
        "color_imbalance": color_balance,
        "width": w,
        "height": h,
    }


def predict_stretch_params(data, target_type=None):
    """Predice parametros optimos de stretch."""
    stats = _analyze_image_stats(data)

    if not stats["is_linear"]:
        return PredictedParams(
            action_id="stretch_midtone",
            params={},
            confidence=0.5,
            reasoning="La imagen ya parece estirada",
        )

    midtone = 0.25
    black_clip = -2.8

    if stats["snr"] < 10:
        midtone = 0.30
        black_clip = -2.0
        reason = f"SNR bajo ({stats['snr']:.1f}): stretch conservador"
    elif stats["snr"] > 30:
        midtone = 0.20
        black_clip = -3.0
        reason = f"SNR alto ({stats['snr']:.1f}): stretch agresivo"
    else:
        t = (stats["snr"] - 10) / 20
        midtone = 0.30 - t * 0.10
        black_clip = -2.0 - t * 1.0
        reason = f"SNR={stats['snr']:.1f}: stretch equilibrado"

    if target_type == "nebula":
        midtone *= 0.8
        reason += ", ajustado para nebulosa"
    elif target_type == "galaxy":
        midtone *= 1.1
        reason += ", ajustado para galaxia"

    return PredictedParams(
        action_id="stretch_midtone",
        params={"midtone": round(midtone, 3), "black_clip": round(black_clip, 2)},
        confidence=0.8,
        reasoning=reason,
    )


def predict_denoise_params(data):
    """Predice parametros optimos de denoise."""
    stats = _analyze_image_stats(data)

    if stats["snr"] > 30:
        lum = 0.2
        chrom = 0.1
        reason = f"SNR alto ({stats['snr']:.1f}): denoise minimo"
        confidence = 0.9
    elif stats["snr"] > 15:
        t = (stats["snr"] - 15) / 15
        lum = 0.7 - t * 0.5
        chrom = 0.35 - t * 0.25
        reason = f"SNR moderado ({stats['snr']:.1f}): denoise equilibrado"
        confidence = 0.8
    else:
        lum = min(0.5 + (15 - stats["snr"]) * 0.05, 1.0)
        chrom = lum * 0.5
        reason = f"SNR bajo ({stats['snr']:.1f}): denoise agresivo"
        confidence = 0.85

    return PredictedParams(
        action_id="denoise_selective",
        params={
            "lum_strength": round(lum, 2),
            "chrom_strength": round(chrom, 2),
            "base_method": "nlm",
        },
        confidence=confidence,
        reasoning=reason,
    )


def predict_sharpen_params(data):
    """Predice parametros optimos de sharpen."""
    stats = _analyze_image_stats(data)

    if stats["fwhm"] > 50:
        return PredictedParams(
            action_id="sharpen_usm",
            params={"radius": 2.0, "amount": 0.5, "threshold": 5},
            confidence=0.5,
            reasoning="No se detectaron estrellas claras para medir FWHM",
        )

    if stats["fwhm"] > 4.0:
        psf = stats["fwhm"] / 2.355
        iters = min(int(10 + stats["fwhm"]), 30)
        return PredictedParams(
            action_id="sharpen_deconv",
            params={"psf_sigma": round(psf, 2), "iterations": iters},
            confidence=0.8,
            reasoning=f"FWHM={stats['fwhm']:.1f}px: deconvolution recomendada",
        )

    return PredictedParams(
        action_id="sharpen_usm",
        params={
            "radius": max(stats["fwhm"] * 0.8, 1.0),
            "amount": 0.8,
            "threshold": 3,
        },
        confidence=0.8,
        reasoning=f"FWHM={stats['fwhm']:.1f}px: USM ligero suficiente",
    )


def predict_background_params(data):
    """Predice parametros optimos de ABE."""
    stats = _analyze_image_stats(data)

    if stats["gradient_pct"] < 3:
        return PredictedParams(
            action_id="background_abe",
            params={"grid_size": 6, "degree": 2},
            confidence=0.7,
            reasoning=f"Gradiente minimo ({stats['gradient_pct']:.1f}%): ABE ligero",
        )

    if stats["gradient_pct"] > 15:
        grid = min(int(8 + stats["gradient_pct"] / 5), 20)
        degree = min(int(2 + stats["gradient_pct"] / 10), 5)
        return PredictedParams(
            action_id="background_abe",
            params={"grid_size": grid, "degree": degree},
            confidence=0.85,
            reasoning=f"Gradiente fuerte ({stats['gradient_pct']:.1f}%): ABE agresivo",
        )

    return PredictedParams(
        action_id="background_abe",
        params={"grid_size": 8, "degree": 3},
        confidence=0.8,
        reasoning=f"Gradiente moderado ({stats['gradient_pct']:.1f}%)",
    )


def predict_all_params(data, target_type=None):
    """
    Predice parametros optimos para todas las operaciones.
    Devuelve un plan completo optimizado.
    """
    predictions = []

    bg = predict_background_params(data)
    if bg.params.get("grid_size", 0) > 6:
        predictions.append(bg)

    predictions.append(predict_stretch_params(data, target_type))
    predictions.append(predict_denoise_params(data))
    predictions.append(predict_sharpen_params(data))

    return predictions


def print_predictions(predictions):
    """Imprime las predicciones de parametros."""
    print(f"\n  AI AUTO-PARAMETROS")
    print(f"  {'=' * 55}")

    for p in predictions:
        print(f"\n  {p.action_id} (confianza: {p.confidence:.0%})")
        print(f"    {p.reasoning}")
        if p.params:
            for k, v in p.params.items():
                print(f"    {k} = {v}")
