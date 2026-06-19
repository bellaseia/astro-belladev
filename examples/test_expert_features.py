"""
test_expert_features.py
-----------------------
Valida: PixelMath, anotaciones, drizzle y metadatos de sesion.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np


def _make_test_image(h=100, w=100, seed=42):
    rng = np.random.RandomState(seed)
    img = np.stack([
        rng.normal(1000, 30, (h, w)),
        rng.normal(800, 30, (h, w)),
        rng.normal(600, 30, (h, w)),
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


def test_pixelmath():
    print("=== Test PixelMath ===\n")
    from astro_belladev.pixelmath import PixelMathEngine, PRESET_EXPRESSIONS

    engine = PixelMathEngine()

    ha = np.random.rand(50, 50).astype(np.float32) * 1000
    oiii = np.random.rand(50, 50).astype(np.float32) * 500
    mask = (np.random.rand(50, 50) > 0.5).astype(np.float32)

    engine.set_image("Ha", ha)
    engine.set_image("OIII", oiii)
    engine.set_image("mask", mask)

    images = engine.list_images()
    assert len(images) == 3
    print(f"  Imagenes registradas: {list(images.keys())}")

    result = engine.evaluate("Ha * 0.7 + OIII * 0.3")
    assert result.shape == ha.shape
    print(f"  'Ha * 0.7 + OIII * 0.3': OK (shape={result.shape})")

    result2 = engine.evaluate("max(Ha, OIII)")
    assert np.all(result2 >= oiii)
    print(f"  'max(Ha, OIII)': OK")

    result3 = engine.evaluate("where(mask > 0.5, Ha, OIII)")
    print(f"  'where(mask > 0.5, Ha, OIII)': OK")

    result4 = engine.evaluate("normalize(Ha)")
    assert result4.min() >= 0 and result4.max() <= 1.0
    print(f"  'normalize(Ha)': OK (range {result4.min():.2f}-{result4.max():.2f})")

    result5 = engine.evaluate("sqrt(abs(Ha - median(Ha)))")
    print(f"  'sqrt(abs(Ha - median(Ha)))': OK")

    result6 = engine.evaluate("clip(Ha * 2.0, 0, 1500)")
    assert result6.max() <= 1500
    print(f"  'clip(Ha * 2.0, 0, 1500)': OK")

    rgb = engine.evaluate_to_rgb("Ha * 0.8", "OIII * 0.6", "OIII * 0.4")
    assert rgb.shape == (50, 50, 3)
    print(f"  evaluate_to_rgb: OK (shape={rgb.shape})")

    try:
        engine.evaluate("import os")
        assert False, "Deberia bloquear import"
    except ValueError as e:
        print(f"  Seguridad: 'import' bloqueado correctamente")

    try:
        engine.evaluate("nonexistent_var + 1")
        assert False
    except ValueError as e:
        assert "no encontrada" in str(e)
        print(f"  Variable inexistente: error correcto")

    history = engine.get_history()
    assert len(history) >= 6
    print(f"  Historial: {len(history)} expresiones")

    print(f"\n  Expresiones predefinidas: {len(PRESET_EXPRESSIONS)}")
    for name in PRESET_EXPRESSIONS:
        print(f"    {name}: {PRESET_EXPRESSIONS[name]}")

    print("\n  -> PixelMath: OK\n")


def test_annotate():
    print("=== Test Anotaciones ===\n")
    from astro_belladev.annotate import (
        annotate_circle, annotate_compass, annotate_scale_bar,
        annotate_text, annotate_objects_from_catalog, annotate_full
    )

    img = _make_test_image(200, 300)

    result = annotate_circle(img, 150, 100, 30, label="M42", color=(255, 200, 0))
    assert result.shape == (200, 300, 3)
    assert result.dtype == np.uint8
    print(f"  Circulo + etiqueta: OK")

    result2 = annotate_compass(result, rotation_deg=15)
    assert result2.shape == result.shape
    print(f"  Brujula N/E (rot=15): OK")

    result3 = annotate_scale_bar(result2, pixel_scale_arcsec=1.5, bar_length_arcmin=5)
    assert result3.shape == result2.shape
    print(f"  Barra de escala (5'): OK")

    result4 = annotate_text(result3, "Astro BellaDev v0.8", 10, 190)
    assert result4.shape == result3.shape
    print(f"  Texto con fondo: OK")

    fake_annotations = [
        {"x_px": 100, "y_px": 80, "size_px": 40, "label": "M42 (Orion)", "type": "Nebulosa de emision"},
        {"x_px": 200, "y_px": 120, "size_px": 20, "label": "NGC 1977", "type": "Nebulosa de reflexion"},
    ]
    result5 = annotate_objects_from_catalog(img, fake_annotations)
    assert result5.shape == (200, 300, 3)
    print(f"  Anotacion de catalogo (2 objetos): OK")

    print("  -> Anotaciones: OK\n")


def test_drizzle():
    print("=== Test Drizzle ===\n")
    from astro_belladev.drizzle import drizzle_quick, _detect_subpixel_offset

    rng = np.random.RandomState(42)
    frame1 = rng.normal(1000, 30, (50, 50)).astype(np.float32)

    frame2 = frame1.copy()
    frame3 = frame1.copy()

    frames = [frame1, frame2, frame3]

    result = drizzle_quick(frames, scale=2)
    assert result.shape == (100, 100)
    print(f"  Drizzle quick 2x: {frames[0].shape} -> {result.shape}")

    dy, dx = _detect_subpixel_offset(frame1, frame2)
    print(f"  Offset detectado: dy={dy:.3f}, dx={dx:.3f} (esperado ~0)")
    assert abs(dy) < 1 and abs(dx) < 1

    print("  -> Drizzle: OK\n")


def test_metadata():
    print("=== Test Metadatos de Sesion ===\n")
    from astro_belladev.metadata import (
        FrameMetadata, analyze_session_metadata,
        print_session_summary,
    )

    metadata_list = []
    for i in range(10):
        meta = FrameMetadata(
            index=i,
            filename=f"frame_{i:03d}.fits",
            timestamp=f"2026-06-18T22:{i*6:02d}:00",
            exposure_seconds=120.0,
            gain=100,
            sensor_temp_c=-10.0 + i * 0.5,
            filter_name="L",
            object_name="M42",
            fwhm=2.5 + i * 0.2,
            elongation=1.05 + i * 0.03,
            star_count=50 - i * 2,
        )
        metadata_list.append(meta)

    metadata_list[8].elongation = 2.5
    metadata_list[9].elongation = 3.0

    summary = analyze_session_metadata(metadata_list)
    print_session_summary(summary)

    assert summary["total_frames"] == 10
    assert summary["total_exposure_minutes"] == 20.0
    assert summary["object"] == "M42"
    assert len(summary["alerts"]) >= 1
    print(f"\n  Alertas generadas: {len(summary['alerts'])}")

    timeline = summary["timeline"]
    assert len(timeline["fwhm"]) == 10
    assert len(timeline["temperature"]) == 10
    print(f"  Timeline: {len(timeline['fwhm'])} puntos")

    d = metadata_list[0].to_dict()
    assert d["exposure"] == 120.0
    print(f"  Serializacion: OK")

    print("  -> Metadatos: OK\n")


if __name__ == "__main__":
    test_pixelmath()
    test_annotate()
    test_drizzle()
    test_metadata()
    print("=" * 55)
    print("  TODOS LOS TESTS PASARON CORRECTAMENTE")
    print("=" * 55)
