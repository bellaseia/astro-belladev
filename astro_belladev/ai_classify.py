"""
ai_classify.py
--------------
Clasificacion inteligente de objetos astronomicos por morfologia.

Analiza la imagen sin plate solving y determina que tipo de objeto
contiene, basandose en caracteristicas morfologicas:
- Distribucion de la senal (concentrada vs extendida)
- Simetria (circular, eliptica, irregular)
- Ratio senal/fondo
- Estructura de filamentos
- Color dominante

Tipos que puede detectar:
- Nebulosa de emision (Ha): senal extendida, irregular, roja
- Nebulosa planetaria: compacta, circular, a veces anular
- Galaxia espiral: eliptica, con estructura de brazos
- Galaxia eliptica: suave, simetrica, sin estructura
- Cumulo abierto: muchas estrellas agrupadas, sin nebulosa
- Cumulo globular: concentracion circular densa de estrellas
- Campo estelar: estrellas distribuidas uniformemente
- Remanente de supernova: filamentos curvos, forma de burbuja
"""

import numpy as np
import cv2
from dataclasses import dataclass, field


@dataclass
class ClassificationResult:
    """Resultado de la clasificacion."""
    primary_type: str
    confidence: float  # 0-1
    all_scores: dict = field(default_factory=dict)
    features: dict = field(default_factory=dict)
    description: str = ""
    processing_hints: dict = field(default_factory=dict)


def _extract_features(data):
    """Extrae caracteristicas morfologicas de la imagen."""
    gray = data.mean(axis=-1) if data.ndim == 3 else data.copy()
    h, w = gray.shape

    # Estadisticas de fondo
    flat = gray.flatten()
    for _ in range(3):
        med = np.median(flat)
        std = np.std(flat)
        mask = np.abs(flat - med) < 3 * std
        flat = flat[mask]
    bg_median = np.median(flat)
    bg_std = np.std(flat)

    # Senal sobre el fondo
    signal = gray - bg_median
    signal = np.clip(signal, 0, None)
    signal_mask = signal > (bg_std * 3)
    signal_fraction = np.mean(signal_mask)

    # Concentracion (centro vs bordes)
    center = gray[h//4:3*h//4, w//4:3*w//4]
    border = np.concatenate([
        gray[:h//4, :].flatten(),
        gray[3*h//4:, :].flatten(),
    ])
    center_signal = np.mean(center > (bg_median + bg_std * 3))
    border_signal = np.mean(border > (bg_median + bg_std * 3))
    concentration = center_signal / max(border_signal, 1e-10)

    # Simetria
    flipped_h = np.fliplr(gray)
    flipped_v = np.flipud(gray)
    symmetry_h = 1.0 - np.mean(np.abs(gray - flipped_h)) / max(bg_std, 1)
    symmetry_v = 1.0 - np.mean(np.abs(gray - flipped_v)) / max(bg_std, 1)
    symmetry = (symmetry_h + symmetry_v) / 2

    # Deteccion de estrellas
    binary = (signal > bg_std * 5).astype(np.uint8)
    from scipy.ndimage import label
    labeled, n_features = label(binary)

    small_objects = 0
    large_objects = 0
    for i in range(1, min(n_features + 1, 500)):
        area = np.sum(labeled == i)
        if area < 50:
            small_objects += 1
        else:
            large_objects += 1

    star_density = small_objects / (h * w / 10000)

    # Estructura filamentosa (bordes curvos)
    img_uint8 = np.clip(signal / max(np.max(signal), 1) * 255, 0, 255).astype(np.uint8)
    edges = cv2.Canny(img_uint8, 30, 100)
    filament_score = np.mean(edges > 0)

    # Color (si RGB)
    color_features = {"dominant": "neutral", "r_ratio": 1.0, "b_ratio": 1.0}
    if data.ndim == 3 and data.shape[-1] == 3:
        r_signal = np.mean(data[..., 0][signal_mask]) if np.any(signal_mask) else 0
        g_signal = np.mean(data[..., 1][signal_mask]) if np.any(signal_mask) else 0
        b_signal = np.mean(data[..., 2][signal_mask]) if np.any(signal_mask) else 0
        total = r_signal + g_signal + b_signal
        if total > 0:
            r_ratio = r_signal / total * 3
            b_ratio = b_signal / total * 3
            color_features["r_ratio"] = float(r_ratio)
            color_features["b_ratio"] = float(b_ratio)
            if r_ratio > 1.3:
                color_features["dominant"] = "red"
            elif b_ratio > 1.3:
                color_features["dominant"] = "blue"

    # Compacidad de la senal
    if np.any(signal_mask):
        ys, xs = np.where(signal_mask)
        if len(ys) > 10:
            spread_y = np.std(ys) / h
            spread_x = np.std(xs) / w
            compactness = 1.0 - min(spread_y + spread_x, 1.0)
        else:
            compactness = 0
    else:
        compactness = 0

    return {
        "signal_fraction": float(signal_fraction),
        "concentration": float(min(concentration, 100)),
        "symmetry": float(np.clip(symmetry, 0, 1)),
        "star_density": float(star_density),
        "filament_score": float(filament_score),
        "large_objects": large_objects,
        "small_objects": small_objects,
        "compactness": float(compactness),
        "color": color_features,
        "bg_snr": float(bg_median / max(bg_std, 1)),
    }


def classify_object(data):
    """
    Clasifica el objeto principal de la imagen.

    Devuelve
    --------
    ClassificationResult con el tipo detectado, confianza,
    todos los scores y sugerencias de procesamiento.
    """
    features = _extract_features(data)

    scores = {}

    # Nebulosa de emision
    em_score = 0
    if features["signal_fraction"] > 0.02:
        em_score += 20
    if features["filament_score"] > 0.005:
        em_score += 25
    if features["concentration"] < 5:
        em_score += 15
    if features["color"]["dominant"] == "red":
        em_score += 30
    if features["symmetry"] < 0.7:
        em_score += 10
    scores["Nebulosa de emision"] = min(em_score, 100)

    # Galaxia espiral
    gx_score = 0
    if features["concentration"] > 3:
        gx_score += 25
    if 0.01 < features["signal_fraction"] < 0.15:
        gx_score += 20
    if features["compactness"] > 0.3:
        gx_score += 20
    if features["filament_score"] > 0.003:
        gx_score += 15
    if features["symmetry"] > 0.5:
        gx_score += 10
    scores["Galaxia"] = min(gx_score, 100)

    # Cumulo abierto
    oc_score = 0
    if features["star_density"] > 3:
        oc_score += 35
    if features["small_objects"] > 20:
        oc_score += 25
    if features["large_objects"] < 3:
        oc_score += 15
    if features["signal_fraction"] < 0.05:
        oc_score += 15
    scores["Cumulo abierto"] = min(oc_score, 100)

    # Cumulo globular
    gc_score = 0
    if features["concentration"] > 8:
        gc_score += 30
    if features["symmetry"] > 0.7:
        gc_score += 25
    if features["compactness"] > 0.5:
        gc_score += 25
    if features["star_density"] > 5:
        gc_score += 20
    scores["Cumulo globular"] = min(gc_score, 100)

    # Nebulosa planetaria
    pn_score = 0
    if features["compactness"] > 0.6:
        pn_score += 25
    if features["symmetry"] > 0.7:
        pn_score += 20
    if features["signal_fraction"] < 0.02:
        pn_score += 20
    if features["color"]["dominant"] in ("blue", "neutral"):
        pn_score += 15
    if features["concentration"] > 5:
        pn_score += 15
    scores["Nebulosa planetaria"] = min(pn_score, 100)

    # Campo estelar
    sf_score = 0
    if features["star_density"] > 2:
        sf_score += 25
    if features["signal_fraction"] > 0.05:
        sf_score += 20
    if features["concentration"] < 2:
        sf_score += 20
    if features["large_objects"] < 2:
        sf_score += 15
    scores["Campo estelar"] = min(sf_score, 100)

    # Remanente de supernova
    snr_score = 0
    if features["filament_score"] > 0.008:
        snr_score += 30
    if features["signal_fraction"] > 0.01:
        snr_score += 15
    if features["symmetry"] < 0.6:
        snr_score += 15
    if features["color"]["dominant"] == "red":
        snr_score += 20
    scores["Remanente de supernova"] = min(snr_score, 100)

    # Resultado
    primary = max(scores, key=scores.get)
    max_score = scores[primary]
    total = sum(scores.values())
    confidence = max_score / max(total, 1) if max_score > 0 else 0

    # Sugerencias de procesamiento por tipo
    processing_hints = _get_processing_hints(primary)

    descriptions = {
        "Nebulosa de emision": "Nube de gas ionizado que emite luz propia (tipicamente en Ha/OIII)",
        "Galaxia": "Sistema estelar extragalactico con estructura espiral o eliptica",
        "Cumulo abierto": "Grupo de estrellas jovenes unidas gravitacionalmente",
        "Cumulo globular": "Agrupacion esferica densa de estrellas viejas",
        "Nebulosa planetaria": "Capa de gas expulsada por una estrella moribunda",
        "Campo estelar": "Region del cielo con estrellas distribuidas sin objeto dominante",
        "Remanente de supernova": "Restos de la explosion de una estrella masiva",
    }

    return ClassificationResult(
        primary_type=primary,
        confidence=confidence,
        all_scores=scores,
        features=features,
        description=descriptions.get(primary, ""),
        processing_hints=processing_hints,
    )


def _get_processing_hints(obj_type):
    """Sugerencias de procesamiento optimizadas por tipo de objeto."""
    hints = {
        "Nebulosa de emision": {
            "stretch": {"method": "midtone", "midtone": 0.18},
            "denoise": {"lum_strength": 0.6, "chrom_strength": 0.3},
            "color": "Potenciar rojos (Ha) con saturacion selectiva",
            "stars": "Considerar starless + recombinacion suave",
        },
        "Galaxia": {
            "stretch": {"method": "midtone", "midtone": 0.28},
            "denoise": {"lum_strength": 0.4, "chrom_strength": 0.2},
            "color": "Balance de blancos por estrellas, saturacion moderada",
            "sharpen": "Deconvolution suave para recuperar detalle en brazos",
        },
        "Cumulo abierto": {
            "stretch": {"method": "asinh", "a": 0.03},
            "denoise": {"lum_strength": 0.3, "chrom_strength": 0.15},
            "color": "Saturacion alta para resaltar colores estelares",
            "stars": "No eliminar estrellas, son el objeto principal",
        },
        "Cumulo globular": {
            "stretch": {"method": "midtone", "midtone": 0.30},
            "denoise": {"lum_strength": 0.3, "chrom_strength": 0.15},
            "sharpen": "Deconvolution para resolver estrellas individuales",
        },
        "Nebulosa planetaria": {
            "stretch": {"method": "midtone", "midtone": 0.22},
            "denoise": {"lum_strength": 0.5, "chrom_strength": 0.25},
            "color": "Balance de blancos neutro, saturacion moderada",
        },
        "Campo estelar": {
            "stretch": {"method": "asinh", "a": 0.02},
            "color": "Saturacion alta para colores estelares",
            "stars": "Reducir halos en estrellas brillantes",
        },
        "Remanente de supernova": {
            "stretch": {"method": "midtone", "midtone": 0.15},
            "denoise": {"lum_strength": 0.7, "chrom_strength": 0.35},
            "color": "Potenciar Ha, considerar paleta bicolor Ha+OIII",
            "stars": "Starless recomendado para resaltar filamentos",
        },
    }
    return hints.get(obj_type, {})


def print_classification(result):
    """Imprime el resultado de la clasificacion."""
    print(f"\n  CLASIFICACION AI")
    print(f"  {'=' * 50}")
    print(f"  Tipo detectado: {result.primary_type}")
    print(f"  Confianza: {result.confidence:.0%}")
    print(f"  {result.description}")

    print(f"\n  Scores por tipo:")
    for obj_type, score in sorted(result.all_scores.items(), key=lambda x: -x[1]):
        bar = "#" * (score // 5) + "-" * (20 - score // 5)
        print(f"    {obj_type:<25} [{bar}] {score}")

    if result.processing_hints:
        print(f"\n  Sugerencias de procesamiento:")
        for key, value in result.processing_hints.items():
            print(f"    {key}: {value}")
