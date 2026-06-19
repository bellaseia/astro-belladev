"""
test_assistant_planner.py
-------------------------
Valida: asistente inteligente, planificador de sesion,
perfiles de equipo y batch processing.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np


def _make_test_image(h=200, w=200, seed=42, gradient=True, noise=50):
    rng = np.random.RandomState(seed)
    bg = 1000
    grad = np.linspace(0, 300, w).reshape(1, -1) * np.ones((h, 1)) if gradient else 0
    img = np.stack([
        rng.normal(bg, noise, (h, w)) + grad,
        rng.normal(bg, noise, (h, w)) + grad * 0.7,
        rng.normal(bg, noise, (h, w)) + grad * 0.4,
    ], axis=-1).astype(np.float32)

    for _ in range(20):
        y, x = rng.randint(15, h-15), rng.randint(15, w-15)
        peak = rng.uniform(3000, 10000)
        yy, xx = np.mgrid[-8:9, -8:9]
        star = peak * np.exp(-(yy**2 + xx**2) / 12.5)
        y0, x0 = max(0, y-8), max(0, x-8)
        y1, x1 = min(h, y+9), min(w, x+9)
        sy, sx = y0-(y-8), x0-(x-8)
        for c in range(3):
            img[y0:y1, x0:x1, c] += star[sy:sy+(y1-y0), sx:sx+(x1-x0)]

    return np.clip(img, 0, None)


def test_assistant():
    print("=== Test Asistente Inteligente ===\n")
    from astro_belladev.assistant import (
        analyze_image, get_next_recommended_action,
        print_analysis, generate_processing_plan,
    )

    # Imagen con problemas: gradiente + ruido + color desbalanceado
    img_bad = _make_test_image(gradient=True, noise=80)
    suggestions = analyze_image(img_bad, stage="post_stack")

    print_analysis(suggestions)

    problems = [s for s in suggestions if s.severity in ("critical", "warning")]
    print(f"\n  Problemas detectados: {len(problems)}")
    assert len(problems) >= 1, "Deberia detectar al menos 1 problema"

    has_gradient = any(s.category == "gradient" for s in suggestions
                       if s.severity in ("critical", "warning"))
    print(f"  Gradiente detectado: {has_gradient}")

    next_action = get_next_recommended_action(img_bad, "post_stack")
    if next_action:
        print(f"\n  Siguiente accion recomendada: {next_action.action_id}")
        print(f"    Razon: {next_action.title}")

    plan = generate_processing_plan(img_bad, "post_stack")
    print(f"\n  Plan de procesamiento: {len(plan)} pasos")
    for p in plan:
        print(f"    [{p['severity']}] {p['action_id']}: {p['reason']}")

    # Imagen limpia
    print("\n  --- Imagen limpia ---")
    img_good = _make_test_image(gradient=False, noise=20)
    suggestions_good = analyze_image(img_good, stage="post_stack")
    problems_good = [s for s in suggestions_good if s.severity in ("critical", "warning")]
    ok_good = [s for s in suggestions_good if s.severity == "ok"]
    print(f"  Problemas: {len(problems_good)}, OK: {len(ok_good)}")

    print("\n  -> Asistente: OK\n")


def test_planner():
    print("=== Test Planificador de Sesion ===\n")
    from astro_belladev.planner import (
        EquipmentProfile, ObserverLocation,
        calculate_visibility, suggest_targets,
        get_bortle_processing_hints, print_session_plan,
    )
    from astro_belladev.catalog import AstroCatalog

    cat = AstroCatalog()
    cat.load_builtin()

    # Ubicacion: Murcia, Espana
    location = ObserverLocation(
        latitude=38.0,
        longitude=-1.13,
        altitude_m=200,
        timezone_offset=2,
        name="Murcia, Espana",
    )

    equipment = EquipmentProfile(
        name="Newton 200/800 + ASI2600MC",
        telescope_focal_mm=800,
        telescope_aperture_mm=200,
        camera_pixel_um=3.76,
        camera_width_px=6248,
        camera_height_px=4176,
        bortle_class=5,
    )

    print(f"  Equipo: {equipment.name}")
    print(f"    Pixel scale: {equipment.pixel_scale_arcsec:.2f}\"/px")
    print(f"    FOV: {equipment.fov_width_arcmin:.0f}' x {equipment.fov_height_arcmin:.0f}'")
    print(f"    f/{equipment.focal_ratio:.1f}")
    print(f"    Muestreo: {equipment.resolution_rating}")
    print(f"    Exposicion sugerida: {equipment.suggested_exposure()}s")

    windows = calculate_visibility(cat, location, min_altitude=30)
    print(f"\n  Objetos visibles (>30 grados): {len(windows)}")
    assert len(windows) >= 20

    targets = suggest_targets(cat, location, equipment, top_n=15)
    print(f"  Top 15 targets recomendados:")

    print_session_plan(targets, equipment, location)

    for bortle in [1, 5, 9]:
        hints = get_bortle_processing_hints(bortle)
        print(f"\n  Bortle {bortle}: {hints['description']}")
        print(f"    ABE grid={hints['abe_grid']}, degree={hints['abe_degree']}")
        print(f"    Denoise lum={hints['denoise_lum']}")
        print(f"    Stretch midtone={hints['stretch_midtone']}")

    print("\n  -> Planificador: OK\n")


def test_equipment_profiles():
    print("=== Test Perfiles de Equipo ===\n")
    from astro_belladev.planner import EquipmentProfile

    profiles = [
        EquipmentProfile(
            name="Refractor 72/400 + Canon 6D",
            telescope_focal_mm=400,
            telescope_aperture_mm=72,
            camera_pixel_um=6.54,
            camera_width_px=5472,
            camera_height_px=3648,
            bortle_class=4,
        ),
        EquipmentProfile(
            name="SCT 8\" 2032mm + ASI294MC",
            telescope_focal_mm=2032,
            telescope_aperture_mm=203,
            camera_pixel_um=4.63,
            camera_width_px=4144,
            camera_height_px=2822,
            bortle_class=6,
        ),
        EquipmentProfile(
            name="Samyang 135mm + ASI533MC",
            telescope_focal_mm=135,
            telescope_aperture_mm=68,
            camera_pixel_um=3.76,
            camera_width_px=3008,
            camera_height_px=3008,
            bortle_class=3,
        ),
    ]

    for p in profiles:
        print(f"  {p.name}")
        print(f"    PS: {p.pixel_scale_arcsec:.2f}\"/px | "
              f"FOV: {p.fov_width_deg:.1f} x {p.fov_height_deg:.1f} deg | "
              f"f/{p.focal_ratio:.1f} | "
              f"Exp: {p.suggested_exposure()}s | "
              f"{p.resolution_rating}")

        d = p.to_dict()
        p2 = EquipmentProfile.from_dict(d)
        assert p2.name == p.name
        assert abs(p2.pixel_scale_arcsec - p.pixel_scale_arcsec) < 0.01

    print("\n  -> Perfiles: OK\n")


def test_batch():
    print("=== Test Batch Processing ===\n")
    from astro_belladev.batch import batch_process, print_batch_results
    from astro_belladev.toolbar import MacroStep
    from astro_belladev.io_fits import save_fits

    test_dir = os.path.join(os.path.dirname(__file__), "_test_batch")
    input_dir = os.path.join(test_dir, "input")
    output_dir = os.path.join(test_dir, "output")
    os.makedirs(input_dir, exist_ok=True)

    for i in range(3):
        img = _make_test_image(seed=42+i, gradient=True)
        save_fits(os.path.join(input_dir, f"test_{i}.fits"), img)

    input_paths = [
        os.path.join(input_dir, f"test_{i}.fits") for i in range(3)
    ]

    steps = [
        MacroStep("stretch_midtone", {"midtone": 0.25, "black_clip": -2.8}),
        MacroStep("saturation", {"factor": 1.3}),
    ]

    results = batch_process(
        input_paths, steps, output_dir,
        output_format=".fits",
    )

    print_batch_results(results)

    success = sum(1 for r in results if r["success"])
    assert success == 3, f"Esperados 3 exitos, obtenidos {success}"

    import shutil
    shutil.rmtree(test_dir)
    print("\n  -> Batch: OK\n")


if __name__ == "__main__":
    test_assistant()
    test_planner()
    test_equipment_profiles()
    test_batch()
    print("=" * 55)
    print("  TODOS LOS TESTS PASARON CORRECTAMENTE")
    print("=" * 55)
