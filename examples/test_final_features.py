"""
test_final_features.py
----------------------
Valida: SCNR, LRGB, star effects (spikes!), CLAHE, heal, publish.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import cv2


def _make_test_image(h=200, w=200, seed=42):
    rng = np.random.RandomState(seed)
    img = np.stack([
        rng.normal(1000, 30, (h, w)),
        rng.normal(1200, 30, (h, w)),
        rng.normal(800, 30, (h, w)),
    ], axis=-1).astype(np.float32)
    for _ in range(20):
        y, x = rng.randint(15, h-15), rng.randint(15, w-15)
        peak = rng.uniform(3000, 10000)
        yy, xx = np.mgrid[-6:7, -6:7]
        star = peak * np.exp(-(yy**2 + xx**2) / 10)
        y0, x0 = max(0, y-6), max(0, x-6)
        y1, x1 = min(h, y+7), min(w, x+7)
        sy, sx = y0-(y-6), x0-(x-6)
        for c in range(3):
            img[y0:y1, x0:x1, c] += star[sy:sy+(y1-y0), sx:sx+(x1-x0)]
    return np.clip(img, 0, None)


def test_scnr():
    print("=== Test SCNR + LRGB ===\n")
    from astro_belladev.scnr import (
        scnr_average_neutral, scnr_maximum_mask, scnr_additive_mask,
        lrgb_combine, lrgb_combine_lab,
    )

    img = _make_test_image()
    g_before = img[..., 1].mean()

    for method_name, method in [
        ("Average Neutral", scnr_average_neutral),
        ("Maximum Mask", scnr_maximum_mask),
        ("Additive Mask", scnr_additive_mask),
    ]:
        result = method(img, amount=1.0)
        g_after = result[..., 1].mean()
        assert result.shape == img.shape
        assert g_after <= g_before
        print(f"  {method_name}: verde {g_before:.0f} -> {g_after:.0f}")

    lum = img.mean(axis=-1)
    rgb = img.copy()
    lrgb = lrgb_combine(lum, rgb, lum_weight=0.8)
    assert lrgb.shape == rgb.shape
    print(f"  LRGB combine: OK")

    lrgb_l = lrgb_combine_lab(lum, rgb, lum_weight=0.8)
    assert lrgb_l.shape == rgb.shape
    print(f"  LRGB Lab: OK")

    print("  -> SCNR + LRGB: OK\n")


def test_star_effects():
    print("=== Test Star Effects (Spikes!) ===\n")
    from astro_belladev.star_effects import star_reduction, diffraction_spikes

    img = _make_test_image()

    reduced = star_reduction(img, amount=0.5, iterations=2)
    assert reduced.shape == img.shape
    print(f"  Star reduction: OK")

    spiked_4 = diffraction_spikes(
        img, num_spikes=4, spike_length=0.1,
        spike_brightness=0.5, min_star_brightness=0.3,
    )
    assert spiked_4.shape == img.shape
    print(f"  Diffraction spikes 4 puntas: OK")

    spiked_6 = diffraction_spikes(
        img, num_spikes=6, spike_length=0.08,
        rotation_deg=15, spike_brightness=0.4,
        min_star_brightness=0.3,
    )
    assert spiked_6.shape == img.shape
    print(f"  Diffraction spikes 6 puntas (rot 15): OK")

    spiked_8 = diffraction_spikes(
        img, num_spikes=8, spike_length=0.12,
        spike_width=2.0, min_star_brightness=0.3,
    )
    assert spiked_8.shape == img.shape
    print(f"  Diffraction spikes 8 puntas: OK")

    print("  -> Star Effects: OK\n")


def test_local_enhance():
    print("=== Test CLAHE + Contraste Local ===\n")
    from astro_belladev.local_enhance import clahe, local_contrast

    img = _make_test_image()

    result_clahe = clahe(img, clip_limit=2.0, grid_size=8)
    assert result_clahe.shape == img.shape
    print(f"  CLAHE: OK")

    result_local = local_contrast(img, radius=30, strength=0.5)
    assert result_local.shape == img.shape
    print(f"  Contraste local: OK")

    mono = img.mean(axis=-1)
    result_clahe_mono = clahe(mono, clip_limit=3.0)
    assert result_clahe_mono.ndim == 2
    print(f"  CLAHE mono: OK")

    print("  -> CLAHE: OK\n")


def test_heal():
    print("=== Test Heal/Clone ===\n")
    from astro_belladev.heal import (
        remove_line, remove_hot_pixels, remove_dead_columns,
        heal_region, auto_detect_satellites,
    )

    img = _make_test_image()

    # Simular estela de satelite
    img_satellite = img.copy()
    cv2.line(
        img_satellite.mean(axis=-1).astype(np.uint8),
        (10, 10), (190, 190), 255, 2,
    )
    for c in range(3):
        img_satellite[10:190, 10:190, c] += np.eye(180) * 5000

    healed = remove_line(img_satellite, 10, 10, 190, 190, width=5)
    assert healed.shape == img.shape
    print(f"  Remove line (satelite): OK")

    # Hot pixels
    img_hot = img.copy()
    img_hot[50, 50] = 50000
    img_hot[100, 100] = 50000
    fixed = remove_hot_pixels(img_hot, threshold_sigma=5.0)
    assert fixed[50, 50, 0] < 50000
    print(f"  Remove hot pixels: OK")

    # Dead columns
    img_dead = img.copy()
    img_dead[:, 75, :] = 0
    fixed_cols = remove_dead_columns(img_dead)
    assert fixed_cols[:, 75, :].mean() > 0
    print(f"  Remove dead columns: OK")

    # Heal region
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    mask[80:120, 80:120] = 255
    healed_region = heal_region(img, mask)
    assert healed_region.shape == img.shape
    print(f"  Heal region: OK")

    # Auto-detect satellites
    lines = auto_detect_satellites(img)
    print(f"  Auto-detect satellites: {len(lines)} lineas detectadas")

    print("  -> Heal: OK\n")


def test_publish():
    print("=== Test Publicacion ===\n")
    from astro_belladev.publish import (
        add_watermark, add_border, prepare_for_social,
        create_comparison, create_timelapse_frames,
    )

    img = _make_test_image()

    watermarked = add_watermark(img, "Astro BellaDev 2026", position="bottom_right")
    assert watermarked.shape[:2] == img.shape[:2]
    print(f"  Watermark: OK")

    bordered = add_border(img, top=20, bottom=20, left=20, right=20)
    assert bordered.shape[0] == img.shape[0] + 40
    assert bordered.shape[1] == img.shape[1] + 40
    print(f"  Bordes: {img.shape[:2]} -> {bordered.shape[:2]}")

    for platform in ["instagram", "facebook", "instagram_portrait"]:
        social = prepare_for_social(img, platform=platform)
        h, w = social.shape[:2]
        print(f"  {platform}: {w}x{h}")

    before = img.copy()
    after = img * 0.5

    comparison = create_comparison(before, after, mode="side_by_side")
    assert comparison.shape[1] > img.shape[1]
    print(f"  Comparacion side_by_side: OK")

    slider = create_comparison(before, after, mode="slider")
    assert slider.shape[:2] == img.shape[:2]
    print(f"  Comparacion slider: OK")

    blink = create_comparison(before, after, mode="blink")
    assert len(blink) == 2
    print(f"  Comparacion blink: OK")

    frames = [img * (i / 5) for i in range(1, 6)]
    timelapse = create_timelapse_frames(frames)
    assert len(timelapse) == 5
    print(f"  Timelapse frames: {len(timelapse)}")

    print("  -> Publicacion: OK\n")


if __name__ == "__main__":
    test_scnr()
    test_star_effects()
    test_local_enhance()
    test_heal()
    test_publish()
    print("=" * 55)
    print("  TODOS LOS TESTS PASARON CORRECTAMENTE")
    print("=" * 55)
