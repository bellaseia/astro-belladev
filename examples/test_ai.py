"""
test_ai.py
----------
Valida todos los modulos AI: denoise avanzado, upscale,
clasificacion y auto-parametros.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np


def _make_test_image(h=100, w=100, seed=42, noise=50):
    rng = np.random.RandomState(seed)
    img = np.stack([
        rng.normal(1000, noise, (h, w)),
        rng.normal(800, noise, (h, w)),
        rng.normal(600, noise, (h, w)),
    ], axis=-1).astype(np.float32)
    for _ in range(15):
        y, x = rng.randint(10, h-10), rng.randint(10, w-10)
        peak = rng.uniform(3000, 8000)
        yy, xx = np.mgrid[-5:6, -5:6]
        star = peak * np.exp(-(yy**2 + xx**2) / 8)
        y0, x0 = max(0, y-5), max(0, x-5)
        y1, x1 = min(h, y+6), min(w, x+6)
        sy, sx = y0-(y-5), x0-(x-5)
        for c in range(3):
            img[y0:y1, x0:x1, c] += star[sy:sy+(y1-y0), sx:sx+(x1-x0)]
    return np.clip(img, 0, None)


def test_ai_denoise():
    print("=== Test AI Denoise ===\n")
    from astro_belladev.ai_denoise import (
        denoise_wavelet, denoise_bm3d_like, denoise_multiscale,
        NeuralDenoiseEngine,
    )

    img = _make_test_image(noise=80)
    noise_before = np.std(img[:20, :20, 0])

    # Wavelet
    result_wav = denoise_wavelet(img, strength=0.5, levels=4)
    assert result_wav.shape == img.shape
    noise_wav = np.std(result_wav[:20, :20, 0])
    print(f"  Wavelet: ruido {noise_before:.1f} -> {noise_wav:.1f}")

    # BM3D-like
    result_bm3d = denoise_bm3d_like(img, strength=0.5)
    assert result_bm3d.shape == img.shape
    noise_bm3d = np.std(result_bm3d[:20, :20, 0])
    print(f"  BM3D-like: ruido {noise_before:.1f} -> {noise_bm3d:.1f}")

    # Multiscale
    result_ms = denoise_multiscale(img, fine_strength=0.8, medium_strength=0.3)
    assert result_ms.shape == img.shape
    noise_ms = np.std(result_ms[:20, :20, 0])
    print(f"  Multiscale: ruido {noise_before:.1f} -> {noise_ms:.1f}")

    # Neural engine (sin modelo)
    engine = NeuralDenoiseEngine()
    print(f"  ONNX disponible: {engine.is_available}")
    models = engine.list_available_models()
    print(f"  Modelos disponibles: {len(models)}")
    for m in models:
        print(f"    {m['name']}: {m['description']} ({m['size_mb']}MB)")

    print("  -> AI Denoise: OK\n")


def test_ai_enhance():
    print("=== Test AI Enhance ===\n")
    from astro_belladev.ai_enhance import upscale_ai, enhance_detail

    img = _make_test_image(50, 50)

    # Upscale lanczos
    result = upscale_ai(img, scale=2, method="lanczos")
    assert result.shape == (100, 100, 3)
    print(f"  Upscale lanczos 2x: {img.shape[:2]} -> {result.shape[:2]}")

    # Upscale cubic+
    result2 = upscale_ai(img, scale=2, method="cubic_plus")
    assert result2.shape == (100, 100, 3)
    print(f"  Upscale cubic+ 2x: {img.shape[:2]} -> {result2.shape[:2]}")

    # Enhance detail
    for scale in ["fine", "medium", "coarse", "all"]:
        enhanced = enhance_detail(img, strength=0.5, scale=scale)
        assert enhanced.shape == img.shape
    print(f"  Enhance detail (fine/medium/coarse/all): OK")

    print("  -> AI Enhance: OK\n")


def test_ai_classify():
    print("=== Test AI Clasificacion ===\n")
    from astro_belladev.ai_classify import classify_object, print_classification

    # Imagen con muchas estrellas (campo estelar o cumulo)
    img = _make_test_image(200, 200)
    result = classify_object(img)

    print_classification(result)

    assert result.primary_type in [
        "Nebulosa de emision", "Galaxia", "Cumulo abierto",
        "Cumulo globular", "Nebulosa planetaria", "Campo estelar",
        "Remanente de supernova",
    ]
    assert 0 <= result.confidence <= 1
    assert len(result.all_scores) >= 5
    assert len(result.features) >= 5

    print(f"\n  Features extraidas: {list(result.features.keys())}")

    if result.processing_hints:
        print(f"  Hints de procesamiento: {list(result.processing_hints.keys())}")

    print("  -> AI Clasificacion: OK\n")


def test_ai_autoparams():
    print("=== Test AI Auto-Parametros ===\n")
    from astro_belladev.ai_autoparams import (
        predict_stretch_params, predict_denoise_params,
        predict_sharpen_params, predict_background_params,
        predict_all_params, print_predictions,
    )

    img = _make_test_image(noise=60)

    stretch = predict_stretch_params(img)
    print(f"  Stretch: midtone={stretch.params.get('midtone')}, "
          f"confidence={stretch.confidence:.0%}")
    print(f"    {stretch.reasoning}")

    denoise = predict_denoise_params(img)
    print(f"  Denoise: lum={denoise.params.get('lum_strength')}, "
          f"chrom={denoise.params.get('chrom_strength')}")
    print(f"    {denoise.reasoning}")

    sharpen = predict_sharpen_params(img)
    print(f"  Sharpen: {sharpen.action_id}")
    print(f"    {sharpen.reasoning}")

    bg = predict_background_params(img)
    print(f"  Background: grid={bg.params.get('grid_size')}, "
          f"degree={bg.params.get('degree')}")
    print(f"    {bg.reasoning}")

    # Plan completo
    all_predictions = predict_all_params(img, target_type="nebula")
    print(f"\n  Plan completo: {len(all_predictions)} operaciones")
    print_predictions(all_predictions)

    # Con imagen de alta SNR
    img_clean = _make_test_image(noise=5)
    clean_denoise = predict_denoise_params(img_clean)
    print(f"\n  Imagen limpia: denoise lum={clean_denoise.params['lum_strength']} "
          f"(vs ruidosa: {denoise.params['lum_strength']})")
    # La imagen limpia deberia tener menos denoise o al menos diferente razon
    assert clean_denoise.reasoning != denoise.reasoning

    print("  -> AI Auto-Parametros: OK\n")


if __name__ == "__main__":
    test_ai_denoise()
    test_ai_enhance()
    test_ai_classify()
    test_ai_autoparams()
    print("=" * 55)
    print("  TODOS LOS TESTS PASARON CORRECTAMENTE")
    print("=" * 55)
