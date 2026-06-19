"""
test_all_actions.py
-------------------
Valida todos los módulos nuevos: transform, export, masks,
y el registry completo con todas las acciones.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np


def _make_test_image(h=200, w=200, seed=42):
    rng = np.random.RandomState(seed)
    r = rng.normal(1000, 30, (h, w))
    g = rng.normal(1000, 30, (h, w))
    b = rng.normal(1000, 30, (h, w))

    for _ in range(20):
        y, x = rng.randint(15, h-15), rng.randint(15, w-15)
        peak = rng.uniform(3000, 10000)
        sigma = 2.5
        yy, xx = np.mgrid[-8:9, -8:9]
        star = peak * np.exp(-(yy**2 + xx**2) / (2 * sigma**2))
        y0, x0 = max(0, y-8), max(0, x-8)
        y1, x1 = min(h, y+9), min(w, x+9)
        sy, sx = y0-(y-8), x0-(x-8)
        r[y0:y1, x0:x1] += star[sy:sy+(y1-y0), sx:sx+(x1-x0)]
        g[y0:y1, x0:x1] += star[sy:sy+(y1-y0), sx:sx+(x1-x0)]
        b[y0:y1, x0:x1] += star[sy:sy+(y1-y0), sx:sx+(x1-x0)]

    return np.clip(np.stack([r, g, b], axis=-1), 0, None).astype(np.float32)


def test_transform():
    print("=== Test Transformaciones ===\n")
    from astro_belladev.transform import (
        crop, crop_percent, rotate, flip_horizontal,
        flip_vertical, binning, resize
    )

    img = _make_test_image()

    cropped = crop(img, 20, 20, 180, 180)
    assert cropped.shape == (160, 160, 3)
    print(f"  Crop: {img.shape[:2]} -> {cropped.shape[:2]}")

    cropped_pct = crop_percent(img, top=5, bottom=5, left=5, right=5)
    assert cropped_pct.shape[0] < img.shape[0]
    print(f"  Crop %: {img.shape[:2]} -> {cropped_pct.shape[:2]}")

    rot90 = rotate(img, 90)
    assert rot90.shape == (200, 200, 3)
    print(f"  Rotar 90: {rot90.shape[:2]}")

    rot45 = rotate(img, 45)
    assert rot45.shape[0] > 200
    print(f"  Rotar 45: {rot45.shape[:2]}")

    flipped_h = flip_horizontal(img)
    assert flipped_h.shape == img.shape
    assert np.allclose(flipped_h[:, 0], img[:, -1])
    print(f"  Flip H: OK")

    flipped_v = flip_vertical(img)
    assert flipped_v.shape == img.shape
    print(f"  Flip V: OK")

    binned = binning(img, factor=2, method="average")
    assert binned.shape == (100, 100, 3)
    print(f"  Binning 2x2: {img.shape[:2]} -> {binned.shape[:2]}")

    binned_sum = binning(img, factor=2, method="sum")
    assert binned_sum.mean() > binned.mean()
    print(f"  Binning sum > avg: OK")

    resized = resize(img, scale=0.5)
    assert resized.shape == (100, 100, 3)
    print(f"  Resize 0.5x: {resized.shape[:2]}")

    resized_w = resize(img, width=300)
    assert resized_w.shape[1] == 300
    print(f"  Resize width=300: {resized_w.shape[:2]}")

    print("  -> Transformaciones: OK\n")


def test_export():
    print("=== Test Exportacion ===\n")
    from astro_belladev.export import save_png, save_jpeg, save_image

    img = _make_test_image()
    img_norm = img / np.max(img)
    base = os.path.join(os.path.dirname(__file__), "_test_export")

    save_png(base + ".png", img_norm, bits=16)
    assert os.path.exists(base + ".png")
    size_png = os.path.getsize(base + ".png")
    print(f"  PNG 16-bit: {size_png // 1024} KB")
    os.remove(base + ".png")

    save_png(base + "_8.png", img_norm, bits=8)
    assert os.path.exists(base + "_8.png")
    print(f"  PNG 8-bit: {os.path.getsize(base + '_8.png') // 1024} KB")
    os.remove(base + "_8.png")

    save_jpeg(base + ".jpg", img_norm, quality=95)
    assert os.path.exists(base + ".jpg")
    size_jpg = os.path.getsize(base + ".jpg")
    print(f"  JPEG q95: {size_jpg // 1024} KB")
    os.remove(base + ".jpg")

    save_jpeg(base + "_web.jpg", img_norm, quality=75)
    size_web = os.path.getsize(base + "_web.jpg")
    print(f"  JPEG q75: {size_web // 1024} KB")
    assert size_web < size_jpg
    os.remove(base + "_web.jpg")

    save_image(base + ".png", img_norm)
    assert os.path.exists(base + ".png")
    os.remove(base + ".png")

    print("  -> Exportacion: OK\n")


def test_masks():
    print("=== Test Mascaras ===\n")
    from astro_belladev.masks import (
        mask_luminance, mask_range, mask_stars, mask_invert,
        apply_with_mask, extract_starless, combine_starless_stars,
        reduce_star_halos
    )

    img = _make_test_image()
    img_norm = img / np.max(img)

    lum_mask = mask_luminance(img_norm, shadows=0.1, highlights=0.9, softness=0.05)
    assert lum_mask.shape == img_norm.shape[:2]
    assert lum_mask.min() >= 0 and lum_mask.max() <= 1
    print(f"  Mascara luminancia: mean={lum_mask.mean():.3f}")

    range_mask = mask_range(img_norm, low=0.3, high=0.7)
    assert range_mask.shape == img_norm.shape[:2]
    print(f"  Mascara rango: mean={range_mask.mean():.3f}")

    star_m = mask_stars(img_norm, threshold_sigma=5.0, dilation_radius=3)
    assert star_m.shape == img_norm.shape[:2]
    star_pct = np.mean(star_m > 0.5) * 100
    print(f"  Mascara estrellas: {star_pct:.1f}% de la imagen")

    inv = mask_invert(star_m)
    assert np.allclose(star_m + inv, 1.0)
    print(f"  Mascara invertida: OK")

    processed = img_norm * 0.5
    blended = apply_with_mask(img_norm, processed, star_m)
    assert blended.shape == img_norm.shape
    print(f"  Aplicar con mascara: OK")

    starless, stars_only = extract_starless(img_norm, threshold_sigma=5.0)
    assert starless.shape == img_norm.shape
    assert stars_only.shape == img_norm.shape
    print(f"  Starless: OK (shape={starless.shape})")

    recombined = combine_starless_stars(starless, stars_only, blend=0.5)
    assert recombined.shape == img_norm.shape
    print(f"  Recombinar estrellas (50%): OK")

    dehalo = reduce_star_halos(img_norm, halo_radius=5, strength=0.7)
    assert dehalo.shape == img_norm.shape
    print(f"  Reducir halos: OK")

    print("  -> Mascaras: OK\n")


def test_full_registry():
    print("=== Test Registry Completo ===\n")
    from astro_belladev.actions import build_default_registry

    registry = build_default_registry()
    all_actions = registry.get_all()

    print(f"  Total acciones: {len(all_actions)}\n")

    categories = {}
    for a in all_actions:
        cat = a.category.split(".")[0]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(a)

    for cat in sorted(categories.keys()):
        actions = categories[cat]
        print(f"  [{cat.upper()}] ({len(actions)} acciones)")
        for a in actions:
            params_count = len(a.params)
            p_str = f" ({params_count} params)" if params_count > 0 else ""
            print(f"    - {a.name}{p_str}")
            print(f"      Menu: {a.menu_path}")
        print()

    expected_ids = [
        "create_master_bias", "create_master_dark", "create_master_flat",
        "calibrate_light", "debayer", "align_frames", "score_frames",
        "stack_frames",
        "stretch_auto", "stretch_midtone", "stretch_asinh",
        "background_abe", "background_dbe",
        "denoise_bilateral", "denoise_nlm", "denoise_selective",
        "sharpen_usm", "sharpen_deconv",
        "wb_auto", "wb_stars", "wb_manual",
        "saturation", "saturation_selective",
        "levels", "curves",
        "crop", "crop_percent", "rotate", "flip_h", "flip_v",
        "binning", "resize",
        "star_mask", "extract_starless", "reduce_halos",
        "mask_luminance", "mask_range",
        "export_png", "export_jpeg",
    ]

    registered_ids = {a.id for a in all_actions}
    missing = [eid for eid in expected_ids if eid not in registered_ids]
    if missing:
        print(f"  FALTAN: {missing}")
        assert False, f"Acciones no registradas: {missing}"

    print(f"  Todas las {len(expected_ids)} acciones esperadas estan registradas.")
    print("  -> Registry completo: OK\n")


if __name__ == "__main__":
    test_transform()
    test_export()
    test_masks()
    test_full_registry()
    print("=" * 55)
    print("  TODOS LOS TESTS PASARON CORRECTAMENTE")
    print("=" * 55)
