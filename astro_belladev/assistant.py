"""
assistant.py
------------
Asistente inteligente de astrofotografia.

Analiza la imagen en cada paso del procesamiento y genera
sugerencias contextuales: que operacion aplicar, con que parametros,
y por que. Es como tener un mentor de astrofotografia integrado.

Funciona en dos niveles:
- Diagnostico: detecta problemas (gradiente, ruido, estrellas
  alargadas, fondo no neutro, saturacion baja...).
- Recomendacion: sugiere la accion concreta del registry con
  los parametros optimos para corregir cada problema.

Ejemplo de salida:
  [!] Gradiente detectado (diferencia 15% entre bordes)
      -> Recomendacion: ABE con grid_size=10, degree=3
  [!] Ruido alto en luminancia (SNR=12)
      -> Recomendacion: Denoise selectivo, lum_strength=0.7
  [i] Balance de color desviado (R/B ratio = 1.4)
      -> Recomendacion: Balance de blancos por estrellas
  [ok] Estrellas circulares (elongacion media: 1.05)
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class Suggestion:
    """Una sugerencia del asistente."""
    severity: str  # "critical", "warning", "info", "ok"
    category: str  # "gradient", "noise", "stars", "color", "stretch", etc
    title: str
    description: str
    action_id: str = ""
    action_params: dict = field(default_factory=dict)
    metric_name: str = ""
    metric_value: float = 0.0

    @property
    def icon(self):
        icons = {
            "critical": "[!!]",
            "warning": "[!]",
            "info": "[i]",
            "ok": "[ok]",
        }
        return icons.get(self.severity, "[?]")


def _estimate_background_stats(data):
    """Estadisticas robustas del fondo."""
    gray = data.mean(axis=-1) if data.ndim == 3 else data
    flat = gray.flatten()
    for _ in range(3):
        med = np.median(flat)
        std = np.std(flat)
        mask = np.abs(flat - med) < 3 * std
        flat = flat[mask]
    return float(np.median(flat)), float(np.std(flat))


def _measure_gradient(data):
    """Mide el gradiente de fondo (diferencia entre bordes)."""
    gray = data.mean(axis=-1) if data.ndim == 3 else data
    h, w = gray.shape

    border = 10
    top = np.median(gray[:border, :])
    bottom = np.median(gray[-border:, :])
    left = np.median(gray[:, :border])
    right = np.median(gray[:, -border:])

    bg_median, _ = _estimate_background_stats(data)
    if bg_median <= 0:
        return 0.0

    max_diff = max(abs(top - bottom), abs(left - right))
    return float(max_diff / bg_median * 100)


def _measure_snr(data):
    """Mide la relacion senal/ruido del fondo."""
    bg_median, bg_std = _estimate_background_stats(data)
    if bg_std <= 0:
        return 999.0
    return float(bg_median / bg_std)


def _measure_star_stats(data):
    """Mide estadisticas de estrellas (FWHM, elongacion, count)."""
    from .frame_scoring import score_frame
    score = score_frame(data)
    return score.fwhm, score.elongation, score.star_count


def _measure_color_balance(data):
    """Mide el balance de color (ratios entre canales)."""
    if data.ndim != 3 or data.shape[-1] != 3:
        return 1.0, 1.0, 1.0

    bg_r, _ = _estimate_background_stats(data[..., 0])
    bg_g, _ = _estimate_background_stats(data[..., 1])
    bg_b, _ = _estimate_background_stats(data[..., 2])

    if bg_g <= 0:
        return 1.0, 1.0, 1.0

    return float(bg_r / bg_g), 1.0, float(bg_b / bg_g)


def _measure_dynamic_range(data):
    """Mide el rango dinamico utilizado."""
    gray = data.mean(axis=-1) if data.ndim == 3 else data
    p01 = np.percentile(gray, 1)
    p99 = np.percentile(gray, 99)
    dmax = np.max(gray)
    if dmax <= 0:
        return 0.0
    return float((p99 - p01) / dmax * 100)


def _is_linear(data):
    """Detecta si la imagen todavia esta en formato lineal (sin stretch)."""
    gray = data.mean(axis=-1) if data.ndim == 3 else data
    median = np.median(gray)
    dmax = np.max(gray)
    if dmax <= 0:
        return True
    return float(median / dmax) < 0.1


def _measure_saturation(data):
    """Mide la saturacion media de la imagen."""
    if data.ndim != 3 or data.shape[-1] != 3:
        return 0.0

    import cv2
    dmax = np.max(data) if np.max(data) > 0 else 1.0
    normalized = np.clip(data / dmax * 255, 0, 255).astype(np.uint8)
    hsv = cv2.cvtColor(normalized, cv2.COLOR_RGB2HSV)
    return float(np.mean(hsv[..., 1]))


def analyze_image(data, stage="post_stack"):
    """
    Analiza la imagen y genera sugerencias.

    Parametros
    ----------
    data : numpy array
        La imagen a analizar.
    stage : str
        En que punto del pipeline estamos:
        "raw" - recien cargada
        "calibrated" - tras calibracion
        "post_stack" - tras apilar
        "post_stretch" - tras stretch
        "final" - procesamiento avanzado

    Devuelve
    --------
    Lista de Suggestion ordenadas por severidad.
    """
    suggestions = []

    # --- Gradiente ---
    gradient_pct = _measure_gradient(data)
    if gradient_pct > 20:
        suggestions.append(Suggestion(
            severity="critical",
            category="gradient",
            title=f"Gradiente severo detectado ({gradient_pct:.0f}%)",
            description="Gran diferencia de fondo entre bordes. Probablemente "
                        "contaminacion luminica o vineteo residual no corregido por flats.",
            action_id="background_abe",
            action_params={"grid_size": 12, "degree": 4},
            metric_name="gradient_percent",
            metric_value=gradient_pct,
        ))
    elif gradient_pct > 8:
        suggestions.append(Suggestion(
            severity="warning",
            category="gradient",
            title=f"Gradiente moderado ({gradient_pct:.0f}%)",
            description="Diferencia apreciable de fondo entre bordes.",
            action_id="background_abe",
            action_params={"grid_size": 8, "degree": 3},
            metric_name="gradient_percent",
            metric_value=gradient_pct,
        ))
    else:
        suggestions.append(Suggestion(
            severity="ok", category="gradient",
            title=f"Fondo uniforme ({gradient_pct:.1f}%)",
            description="No se detecta gradiente significativo.",
            metric_value=gradient_pct,
        ))

    # --- Ruido ---
    snr = _measure_snr(data)
    if snr < 5:
        suggestions.append(Suggestion(
            severity="critical",
            category="noise",
            title=f"Ruido muy alto (SNR={snr:.1f})",
            description="Relacion senal/ruido muy baja. Necesitas mas tiempo de "
                        "integracion o denoise agresivo.",
            action_id="denoise_selective",
            action_params={"lum_strength": 0.9, "chrom_strength": 0.5},
            metric_name="snr",
            metric_value=snr,
        ))
    elif snr < 15:
        suggestions.append(Suggestion(
            severity="warning",
            category="noise",
            title=f"Ruido apreciable (SNR={snr:.1f})",
            description="El fondo muestra ruido visible.",
            action_id="denoise_selective",
            action_params={"lum_strength": 0.5, "chrom_strength": 0.3},
            metric_name="snr",
            metric_value=snr,
        ))
    else:
        suggestions.append(Suggestion(
            severity="ok", category="noise",
            title=f"Ruido bajo (SNR={snr:.1f})",
            description="Buena relacion senal/ruido.",
            metric_value=snr,
        ))

    # --- Estrellas ---
    fwhm, elongation, star_count = _measure_star_stats(data)
    if elongation > 2.0:
        suggestions.append(Suggestion(
            severity="critical",
            category="stars",
            title=f"Estrellas muy alargadas (elongacion={elongation:.2f})",
            description="Trailing severo por tracking deficiente o viento. "
                        "Los frames peores deberian descartarse.",
            action_id="score_frames",
            action_params={"reject_percent": 30},
            metric_name="elongation",
            metric_value=elongation,
        ))
    elif elongation > 1.3:
        suggestions.append(Suggestion(
            severity="warning",
            category="stars",
            title=f"Estrellas ligeramente alargadas ({elongation:.2f})",
            description="Elongacion apreciable, posible tracking imperfecto.",
            metric_name="elongation",
            metric_value=elongation,
        ))
    else:
        suggestions.append(Suggestion(
            severity="ok", category="stars",
            title=f"Estrellas circulares ({elongation:.2f})",
            description="Buen tracking, estrellas puntuales.",
            metric_value=elongation,
        ))

    if fwhm > 6.0 and fwhm < 90:
        suggestions.append(Suggestion(
            severity="warning",
            category="focus",
            title=f"Estrellas anchas (FWHM={fwhm:.1f}px)",
            description="FWHM alto puede indicar desenfoque, seeing malo "
                        "o sobremuestreo. Considera deconvolution.",
            action_id="sharpen_deconv",
            action_params={"psf_sigma": fwhm / 2.355, "iterations": 15},
            metric_name="fwhm",
            metric_value=fwhm,
        ))

    # --- Color ---
    if data.ndim == 3 and data.shape[-1] == 3:
        r_ratio, _, b_ratio = _measure_color_balance(data)
        max_deviation = max(abs(r_ratio - 1.0), abs(b_ratio - 1.0))

        if max_deviation > 0.3:
            suggestions.append(Suggestion(
                severity="warning",
                category="color",
                title=f"Balance de color desviado (R/G={r_ratio:.2f}, B/G={b_ratio:.2f})",
                description="Los canales no estan equilibrados. "
                            "El fondo deberia ser neutro (gris).",
                action_id="wb_stars",
                metric_name="color_deviation",
                metric_value=max_deviation,
            ))
        else:
            suggestions.append(Suggestion(
                severity="ok", category="color",
                title=f"Color equilibrado (R/G={r_ratio:.2f}, B/G={b_ratio:.2f})",
                description="Buen balance de color.",
                metric_value=max_deviation,
            ))

        sat = _measure_saturation(data)
        if stage in ("post_stretch", "final") and sat < 20:
            suggestions.append(Suggestion(
                severity="info",
                category="saturation",
                title=f"Saturacion baja ({sat:.0f}/255)",
                description="La imagen podria beneficiarse de mas saturacion.",
                action_id="saturation",
                action_params={"factor": 1.5},
                metric_name="saturation",
                metric_value=sat,
            ))

    # --- Stretch ---
    if _is_linear(data) and stage != "raw":
        suggestions.append(Suggestion(
            severity="info",
            category="stretch",
            title="Imagen en formato lineal (sin stretch)",
            description="La imagen necesita un stretch no-lineal para "
                        "revelar las estructuras debiles.",
            action_id="stretch_auto",
        ))

    # --- Rango dinamico ---
    dr = _measure_dynamic_range(data)
    if stage in ("post_stretch", "final") and dr < 30:
        suggestions.append(Suggestion(
            severity="info",
            category="dynamic_range",
            title=f"Rango dinamico bajo ({dr:.0f}%)",
            description="Poco contraste. Ajusta niveles para expandir el rango.",
            action_id="levels",
            action_params={"black": 0.05, "midtone": 0.4, "white": 0.95},
            metric_name="dynamic_range",
            metric_value=dr,
        ))

    suggestions.sort(key=lambda s: {
        "critical": 0, "warning": 1, "info": 2, "ok": 3
    }.get(s.severity, 4))

    return suggestions


def get_next_recommended_action(data, stage="post_stack"):
    """
    Devuelve LA accion mas importante que el usuario deberia aplicar ahora.
    Para el modo auto simplificado.
    """
    suggestions = analyze_image(data, stage)

    for s in suggestions:
        if s.action_id and s.severity in ("critical", "warning"):
            return s

    for s in suggestions:
        if s.action_id and s.severity == "info":
            return s

    return None


def print_analysis(suggestions):
    """Imprime el analisis de forma legible."""
    print("\n  ASISTENTE DE ASTROFOTOGRAFIA")
    print("  " + "=" * 50)

    problems = [s for s in suggestions if s.severity in ("critical", "warning")]
    ok_items = [s for s in suggestions if s.severity == "ok"]
    info_items = [s for s in suggestions if s.severity == "info"]

    if problems:
        print("\n  Problemas detectados:")
        for s in problems:
            print(f"    {s.icon} {s.title}")
            print(f"       {s.description}")
            if s.action_id:
                params = ""
                if s.action_params:
                    params = " " + str(s.action_params)
                print(f"       -> Recomendacion: {s.action_id}{params}")
            print()

    if info_items:
        print("  Sugerencias:")
        for s in info_items:
            print(f"    {s.icon} {s.title}")
            if s.action_id:
                print(f"       -> {s.action_id}")
            print()

    if ok_items:
        print("  Todo correcto en:")
        for s in ok_items:
            print(f"    {s.icon} {s.title}")

    total = len(suggestions)
    ok = len(ok_items)
    print(f"\n  Resumen: {ok}/{total} metricas OK")


def generate_processing_plan(data, stage="post_stack"):
    """
    Genera un plan de procesamiento completo basado en el analisis.
    Devuelve una lista ordenada de (action_id, params, razon).
    """
    suggestions = analyze_image(data, stage)
    plan = []

    for s in suggestions:
        if s.action_id and s.severity in ("critical", "warning", "info"):
            plan.append({
                "action_id": s.action_id,
                "params": s.action_params,
                "reason": s.title,
                "severity": s.severity,
            })

    return plan
