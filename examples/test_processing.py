"""
test_processing.py
------------------
Valida todos los módulos de procesamiento, la infraestructura de
acciones, sesión con undo, y el sistema de progreso.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np


def _make_test_image(h=200, w=200, n_stars=30, seed=42):
    """Genera una imagen RGB sintética con estrellas y gradiente de fondo."""
    rng = np.random.RandomState(seed)
    bg_level = 1000

    gradient = np.linspace(0, 200, w).reshape(1, -1) * np.ones((h, 1))
    r = rng.normal(bg_level, 30, (h, w)) + gradient
    g = rng.normal(bg_level, 30, (h, w)) + gradient * 0.8
    b = rng.normal(bg_level, 30, (h, w)) + gradient * 0.5

    for _ in range(n_stars):
        y, x = rng.randint(15, h-15), rng.randint(15, w-15)
        peak = rng.uniform(3000, 10000)
        sigma = rng.uniform(1.5, 3.0)
        yy, xx = np.mgrid[-10:11, -10:11]
        star = peak * np.exp(-(yy**2 + xx**2) / (2 * sigma**2))
        y0, x0 = max(0, y-10), max(0, x-10)
        y1, x1 = min(h, y+11), min(w, x+11)
        sy, sx = y0-(y-10), x0-(x-10)
        r[y0:y1, x0:x1] += star[sy:sy+(y1-y0), sx:sx+(x1-x0)]
        g[y0:y1, x0:x1] += star[sy:sy+(y1-y0), sx:sx+(x1-x0)] * 0.9
        b[y0:y1, x0:x1] += star[sy:sy+(y1-y0), sx:sx+(x1-x0)] * 0.8

    img = np.stack([r, g, b], axis=-1).astype(np.float32)
    return np.clip(img, 0, None)


def test_background():
    print("=== Test Extracción de Fondo (ABE) ===\n")
    from astro_belladev.background import extract_background_abe

    img = _make_test_image()
    corrected, background = extract_background_abe(img, grid_size=8, degree=3)

    assert corrected.shape == img.shape
    assert background.shape == img.shape
    assert corrected.min() >= 0

    border_mean_before = img[:, :20, :].mean()
    border_mean_after = corrected[:, :20, :].mean()
    center_mean_before = img[:, 180:, :].mean()
    center_mean_after = corrected[:, 180:, :].mean()

    gradient_before = abs(center_mean_before - border_mean_before)
    gradient_after = abs(center_mean_after - border_mean_after)

    print(f"  Gradiente antes: {gradient_before:.1f}")
    print(f"  Gradiente después: {gradient_after:.1f}")
    assert gradient_after < gradient_before, "ABE debe reducir el gradiente"
    print("  -> ABE: OK\n")


def test_denoise():
    print("=== Test Reducción de Ruido ===\n")
    from astro_belladev.denoise import denoise_image

    img = _make_test_image()

    for method in ["bilateral", "nlm", "selective"]:
        result = denoise_image(img, method=method, strength=0.5)
        assert result.shape == img.shape, f"{method}: shape cambió"
        noise_before = np.std(img[:50, :50, 0])
        noise_after = np.std(result[:50, :50, 0])
        print(f"  {method}: ruido {noise_before:.1f} -> {noise_after:.1f}")

    print("  -> Denoise: OK\n")


def test_sharpen():
    print("=== Test Nitidez ===\n")
    from astro_belladev.sharpen import sharpen_image

    img = _make_test_image()
    img_norm = img / np.max(img)

    result_usm = sharpen_image(img_norm, method="unsharp_mask",
                                radius=2.0, amount=1.0)
    assert result_usm.shape == img_norm.shape
    print(f"  USM: OK (shape={result_usm.shape})")

    gray = img_norm.mean(axis=-1)
    result_deconv = sharpen_image(gray, method="deconvolution",
                                   psf_sigma=1.5, iterations=5)
    assert result_deconv.shape == gray.shape
    print(f"  Deconvolution: OK (shape={result_deconv.shape})")

    print("  -> Sharpen: OK\n")


def test_color():
    print("=== Test Color ===\n")
    from astro_belladev.color import (white_balance_auto, white_balance_stars,
                                    adjust_saturation, adjust_saturation_selective)

    img = _make_test_image()

    wb = white_balance_auto(img)
    assert wb.shape == img.shape
    r_p = np.percentile(wb[..., 0], 95)
    g_p = np.percentile(wb[..., 1], 95)
    b_p = np.percentile(wb[..., 2], 95)
    print(f"  WB Auto: R={r_p:.0f}, G={g_p:.0f}, B={b_p:.0f}")

    wb_stars = white_balance_stars(img)
    assert wb_stars.shape == img.shape
    print(f"  WB Estrellas: OK")

    sat = adjust_saturation(img, factor=1.5)
    assert sat.shape == img.shape
    print(f"  Saturación x1.5: OK")

    sat_sel = adjust_saturation_selective(img, target_hue=0, factor=2.0)
    assert sat_sel.shape == img.shape
    print(f"  Saturación selectiva (rojos): OK")

    print("  -> Color: OK\n")


def test_curves():
    print("=== Test Curvas y Niveles ===\n")
    from astro_belladev.curves import adjust_levels, adjust_curves, get_histogram

    img = _make_test_image()

    leveled = adjust_levels(img, black=0.1, midtone=0.4, white=0.9)
    assert leveled.shape == img.shape
    print(f"  Niveles: OK")

    curved = adjust_curves(img, control_points=[
        (0, 0), (0.25, 0.15), (0.75, 0.85), (1, 1)
    ])
    assert curved.shape == img.shape
    print(f"  Curvas (S-curve): OK")

    hist = get_histogram(img)
    assert "R" in hist and "G" in hist and "B" in hist and "L" in hist
    assert len(hist["R"]) == 256
    print(f"  Histograma RGB+L: OK")

    hist_mono = get_histogram(img.mean(axis=-1))
    assert "counts" in hist_mono
    print(f"  Histograma mono: OK")

    print("  -> Curvas: OK\n")


def test_action_registry():
    print("=== Test Action Registry ===\n")
    from astro_belladev.actions import build_default_registry

    registry = build_default_registry()
    all_actions = registry.get_all()

    print(f"  Acciones registradas: {len(all_actions)}")
    assert len(all_actions) >= 15, f"Esperadas >=15, hay {len(all_actions)}"

    categories = set()
    for a in all_actions:
        categories.add(a.category.split(".")[0])
    print(f"  Categorías: {sorted(categories)}")

    stretch = registry.get("stretch_midtone")
    assert stretch is not None
    assert len(stretch.params) == 2
    defaults = stretch.get_defaults()
    assert "midtone" in defaults
    print(f"  stretch_midtone: params={list(defaults.keys())}")

    registry.list_actions()
    print("\n  -> Registry: OK\n")


def test_session():
    print("=== Test Sesión (paso a paso + undo) ===\n")
    from astro_belladev.session import Session
    from astro_belladev.actions import build_default_registry
    from astro_belladev.progress import SilentProgress

    registry = build_default_registry()
    session = Session(progress=SilentProgress(), max_undo=5)

    img = _make_test_image()
    session.load_image(img, source_info="test sintético")

    state = session.get_state_summary()
    assert state["loaded"]
    assert state["shape"] == img.shape
    print(f"  Imagen cargada: {state['shape']}")

    stretch_action = registry.get("stretch_midtone")
    session.apply(stretch_action, midtone=0.25, black_clip=-2.8)
    assert session.current_data.max() <= 1.0
    print(f"  Stretch aplicado: max={session.current_data.max():.3f}")

    sat_action = registry.get("saturation")
    session.apply(sat_action, factor=1.5)
    print(f"  Saturación aplicada")

    levels_action = registry.get("levels")
    session.apply(levels_action, black=0.05, midtone=0.5, white=0.95)
    print(f"  Niveles aplicados")

    assert session.undo_count() == 3
    print(f"  Undo disponibles: {session.undo_count()}")

    session.undo()
    assert session.undo_count() == 2
    print(f"  Undo ejecutado, quedan: {session.undo_count()}")

    session.undo()
    session.undo()
    assert session.undo_count() == 0
    assert np.allclose(session.current_data, img, atol=0.01)
    print(f"  3x Undo: vuelto al estado original")

    session.print_history()

    history_path = os.path.join(os.path.dirname(__file__), "_test_history.json")
    session.save_history(history_path)
    assert os.path.exists(history_path)
    os.remove(history_path)
    print(f"\n  Historial guardado y limpiado")

    print("  -> Sesión: OK\n")


def test_progress():
    print("=== Test Sistema de Progreso ===\n")
    from astro_belladev.progress import ConsoleProgress, SilentProgress, MultiProgress

    console = ConsoleProgress()
    console.start_pipeline("auto", 5)
    console.start_step("Test paso", step_number=1, total=5)
    for i in range(10):
        console.update(i + 1, 10, f"item {i+1}")
    console.end_step("10 items procesados")
    console.warning("Esto es un warning de prueba")
    console.end_pipeline(True, "Todo correcto")

    silent = SilentProgress()
    silent.start_pipeline("auto", 5)
    silent.log("Esto no se ve")

    multi = MultiProgress(console, silent)
    multi.log("Multi-callback test")

    print("\n  -> Progreso: OK\n")


if __name__ == "__main__":
    test_background()
    test_denoise()
    test_sharpen()
    test_color()
    test_curves()
    test_action_registry()
    test_session()
    test_progress()
    print("=" * 55)
    print("  TODOS LOS TESTS PASARON CORRECTAMENTE")
    print("=" * 55)
