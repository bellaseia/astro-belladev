"""
frame_scoring.py
----------------
Puntuación automática de calidad de cada frame antes del apilamiento.

Métricas evaluadas:
- FWHM (Full Width at Half Maximum): mide el seeing/enfoque.
  Valores bajos = estrellas más puntuales = mejor calidad.
- Elongación estelar: detecta trailing por tracking deficiente
  o viento. Ratio de los ejes de la elipse ajustada a cada estrella.
  1.0 = circular perfecto, >1.5 = trailing problemático.
- Ruido de fondo: desviación estándar del fondo. Valores altos
  indican nubes, contaminación lumínica variable o problemas.
- Nº de estrellas detectadas: un frame con muy pocas estrellas
  respecto a los demás probablemente tiene nubes, desenfoque
  extremo o un problema de seguimiento grave.

Cada métrica se normaliza a un score 0–100 relativo al conjunto
de frames de la sesión, y se combina en un score global.
"""

import numpy as np
from dataclasses import dataclass, field
from scipy.ndimage import label, find_objects
from scipy.optimize import least_squares


@dataclass
class FrameScore:
    index: int
    fwhm: float = 0.0
    elongation: float = 1.0
    background_noise: float = 0.0
    star_count: int = 0
    score: float = 0.0
    accepted: bool = True
    rejection_reason: str = ""


def _to_grayscale(data):
    if data.ndim == 3:
        return data.mean(axis=-1)
    return data


def _estimate_background(data):
    """Estimación robusta del fondo usando sigma-clipping iterativo."""
    flat = data.flatten()
    for _ in range(3):
        median = np.median(flat)
        std = np.std(flat)
        mask = np.abs(flat - median) < 3 * std
        flat = flat[mask]
    return np.median(flat), np.std(flat)


def _detect_stars(data, threshold_sigma=5.0, min_area=4, max_area=500):
    """
    Detecta estrellas como grupos de píxeles por encima del fondo.
    Devuelve una lista de (y_centro, x_centro, slice_region).
    """
    bg_median, bg_std = _estimate_background(data)
    threshold = bg_median + threshold_sigma * bg_std

    binary = data > threshold

    labeled, n_features = label(binary)
    if n_features == 0:
        return []

    regions = find_objects(labeled)
    stars = []

    for i, slc in enumerate(regions):
        if slc is None:
            continue

        region_mask = labeled[slc] == (i + 1)
        area = np.sum(region_mask)

        if area < min_area or area > max_area:
            continue

        region_data = data[slc] * region_mask

        total = np.sum(region_data)
        if total <= 0:
            continue

        ys, xs = np.mgrid[slc[0].start:slc[0].stop, slc[1].start:slc[1].stop]
        y_center = np.sum(ys * region_data) / total
        x_center = np.sum(xs * region_data) / total

        stars.append((y_center, x_center, slc, region_data, region_mask))

    return stars


def _measure_fwhm_single(star_data, star_mask):
    """Mide FWHM de una estrella individual por perfil radial."""
    masked = star_data * star_mask
    peak = np.max(masked)
    if peak <= 0:
        return None

    total = np.sum(masked)
    ys, xs = np.mgrid[0:star_data.shape[0], 0:star_data.shape[1]]
    y_c = np.sum(ys * masked) / total
    x_c = np.sum(xs * masked) / total

    distances = np.sqrt((ys - y_c)**2 + (xs - x_c)**2)

    half_max = peak / 2.0
    above_half = masked >= half_max
    if np.sum(above_half) < 2:
        return None

    fwhm = 2.0 * np.sqrt(np.sum(above_half) / np.pi)
    return fwhm


def _measure_elongation_single(star_data, star_mask):
    """Mide elongación como ratio de ejes de la elipse ajustada."""
    masked = star_data * star_mask
    total = np.sum(masked)
    if total <= 0:
        return 1.0

    ys, xs = np.mgrid[0:star_data.shape[0], 0:star_data.shape[1]]
    y_c = np.sum(ys * masked) / total
    x_c = np.sum(xs * masked) / total

    Myy = np.sum(masked * (ys - y_c)**2) / total
    Mxx = np.sum(masked * (xs - x_c)**2) / total
    Mxy = np.sum(masked * (ys - y_c) * (xs - x_c)) / total

    trace = Myy + Mxx
    det = Myy * Mxx - Mxy**2

    discriminant = (trace / 2)**2 - det
    if discriminant < 0:
        return 1.0

    sqrt_disc = np.sqrt(discriminant)
    lambda1 = trace / 2 + sqrt_disc
    lambda2 = trace / 2 - sqrt_disc

    if lambda2 <= 0:
        return 1.0

    return np.sqrt(lambda1 / lambda2)


def score_frame(data, index=0):
    """
    Evalúa la calidad de un frame individual.

    Devuelve un FrameScore con las métricas medidas (sin score
    normalizado — eso se calcula en score_all con el contexto
    de toda la sesión).
    """
    gray = _to_grayscale(data)
    bg_median, bg_std = _estimate_background(gray)

    stars = _detect_stars(gray)

    result = FrameScore(
        index=index,
        background_noise=float(bg_std),
        star_count=len(stars),
    )

    if len(stars) < 3:
        result.fwhm = 99.0
        result.elongation = 99.0
        return result

    fwhms = []
    elongations = []

    for y_c, x_c, slc, star_data, star_mask in stars:
        fwhm = _measure_fwhm_single(star_data, star_mask)
        if fwhm is not None and 1.0 < fwhm < 30.0:
            fwhms.append(fwhm)

        elong = _measure_elongation_single(star_data, star_mask)
        if 1.0 <= elong < 20.0:
            elongations.append(elong)

    result.fwhm = float(np.median(fwhms)) if fwhms else 99.0
    result.elongation = float(np.median(elongations)) if elongations else 99.0

    return result


def score_all(frames, reject_percent=20, min_stars=5):
    """
    Puntúa todos los frames de una sesión y marca los que se deben
    descartar.

    Parámetros
    ----------
    frames : list of numpy arrays
        Los frames a evaluar.
    reject_percent : int
        Porcentaje máximo de frames a descartar (0-100).
        En modo auto se usa 20%, en modo experto el usuario decide.
    min_stars : int
        Mínimo de estrellas para considerar un frame válido.

    Devuelve
    --------
    list of FrameScore, ordenada por score descendente (mejor primero).
    """
    scores = []
    for i, frame in enumerate(frames):
        s = score_frame(frame, index=i)
        scores.append(s)

    fwhms = np.array([s.fwhm for s in scores])
    elongs = np.array([s.elongation for s in scores])
    noises = np.array([s.background_noise for s in scores])
    star_counts = np.array([s.star_count for s in scores], dtype=float)

    def normalize_inverse(values):
        """Menor valor = mejor score (FWHM, elongación, ruido)."""
        vmin, vmax = values.min(), values.max()
        if vmax == vmin:
            return np.full_like(values, 100.0)
        return (1.0 - (values - vmin) / (vmax - vmin)) * 100.0

    def normalize_direct(values):
        """Mayor valor = mejor score (nº estrellas)."""
        vmin, vmax = values.min(), values.max()
        if vmax == vmin:
            return np.full_like(values, 100.0)
        return ((values - vmin) / (vmax - vmin)) * 100.0

    fwhm_scores = normalize_inverse(fwhms)
    elong_scores = normalize_inverse(elongs)
    noise_scores = normalize_inverse(noises)
    star_scores = normalize_direct(star_counts)

    # Pesos: FWHM y elongación son las métricas más importantes
    # para la calidad final del apilado.
    weights = {"fwhm": 0.35, "elongation": 0.30, "noise": 0.20, "stars": 0.15}

    for i, s in enumerate(scores):
        s.score = (
            weights["fwhm"] * fwhm_scores[i] +
            weights["elongation"] * elong_scores[i] +
            weights["noise"] * noise_scores[i] +
            weights["stars"] * star_scores[i]
        )

    scores.sort(key=lambda s: s.score, reverse=True)

    # Descarte: por pocas estrellas o por estar en el peor percentil
    max_reject = max(1, int(len(scores) * reject_percent / 100))
    rejected = 0

    for s in reversed(scores):
        if rejected >= max_reject:
            break

        if s.star_count < min_stars:
            s.accepted = False
            s.rejection_reason = f"Pocas estrellas ({s.star_count} < {min_stars})"
            rejected += 1
        elif s.score < 30:
            s.accepted = False
            s.rejection_reason = f"Score bajo ({s.score:.1f})"
            rejected += 1

    return scores


def print_scores(scores):
    """Imprime una tabla resumen de los scores."""
    print(f"\n{'Frame':>6} {'FWHM':>6} {'Elong':>6} {'Ruido':>8} "
          f"{'Estrellas':>9} {'Score':>6} {'Estado':>10}")
    print("-" * 60)

    for s in scores:
        status = "OK" if s.accepted else f"RECHAZADO"
        print(f"  #{s.index:<4} {s.fwhm:>6.2f} {s.elongation:>6.2f} "
              f"{s.background_noise:>8.1f} {s.star_count:>9} "
              f"{s.score:>6.1f} {status:>10}")

    accepted = sum(1 for s in scores if s.accepted)
    print(f"\n  {accepted}/{len(scores)} frames aceptados.")
