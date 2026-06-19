"""
test_advanced.py
----------------
Valida: catalogo astronomico, plate solving, narrowband y mosaico/HDR.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np


def _make_test_image(h=200, w=200, seed=42):
    rng = np.random.RandomState(seed)
    img = np.stack([
        rng.normal(1000, 30, (h, w)),
        rng.normal(1000, 30, (h, w)),
        rng.normal(1000, 30, (h, w)),
    ], axis=-1).astype(np.float32)
    return np.clip(img, 0, None)


def test_catalog():
    print("=== Test Catalogo Astronomico ===\n")
    from astro_belladev.catalog import AstroCatalog, print_catalog_summary

    cat = AstroCatalog()
    cat.load_builtin()

    stats = cat.get_stats()
    print(f"  Objetos totales: {stats['total_objects']}")
    assert stats["total_objects"] >= 140

    print_catalog_summary(cat)

    m42 = cat.get("M42")
    assert m42 is not None
    assert "Orion" in m42.common_name
    print(f"\n  M42: {m42.common_name}")
    print(f"    RA: {m42.ra_hms}, Dec: {m42.dec_dms}")
    print(f"    Magnitud: {m42.magnitude}, Tamano: {m42.size_arcmin}'")

    results = cat.search("andromeda")
    assert len(results) >= 1
    print(f"\n  Busqueda 'andromeda': {len(results)} resultados")
    for r in results:
        print(f"    {r.id}: {r.common_name or r.name}")

    galaxies = cat.filter_by_type("GX")
    print(f"\n  Galaxias en catalogo: {len(galaxies)}")
    assert len(galaxies) >= 30

    orion_objects = cat.search("ori")
    print(f"  Objetos con 'ori': {len(orion_objects)}")

    # Simular plate solving: campo alrededor de M42
    field = cat.objects_in_field(83.8, -5.4, 2.0)
    print(f"\n  Objetos en campo de M42 (2 grados): {len(field)}")
    for obj, dist in field:
        print(f"    {obj.id} ({obj.common_name or obj.name}) a {dist:.2f} grados")

    bright = cat.filter_by_magnitude(6.0)
    print(f"\n  Objetos con magnitud < 6.0: {len(bright)}")

    # Test identificacion de imagen
    identified = cat.identify_image(83.8, -5.4, 3.0, 2.0)
    print(f"\n  Objetos en imagen 3x2 grados centrada en M42: {len(identified)}")
    for item in identified:
        obj = item["object"]
        print(f"    {obj.id} en posicion ({item['x']:.2f}, {item['y']:.2f})")

    # Test persistencia
    test_path = os.path.join(os.path.dirname(__file__), "_test_catalog.json")
    cat.save_catalog(test_path)
    assert os.path.exists(test_path)

    cat2 = AstroCatalog()
    cat2.load_catalog(test_path)
    assert cat2.get("M42") is not None
    os.remove(test_path)
    print(f"\n  Persistencia JSON: OK")

    print("  -> Catalogo: OK\n")


def test_platesolve():
    print("=== Test Plate Solving ===\n")
    from astro_belladev.platesolve import (
        WCSolution, solve_from_header, solve_image, annotate_image
    )
    from astro_belladev.catalog import AstroCatalog

    wcs = WCSolution(
        ra_center=83.822, dec_center=-5.391,
        pixel_scale=1.5, rotation=0,
        width_px=2000, height_px=1500,
        solved=True,
    )

    print(f"  FOV: {wcs.fov_width_arcmin:.1f}' x {wcs.fov_height_arcmin:.1f}'")
    print(f"  FOV: {wcs.fov_width_deg:.2f} x {wcs.fov_height_deg:.2f} grados")

    ra, dec = wcs.pixel_to_radec(1000, 750)
    print(f"  Centro pixel -> RA={ra:.3f}, Dec={dec:.3f}")
    assert abs(ra - 83.822) < 0.01
    assert abs(dec - (-5.391)) < 0.01

    x, y = wcs.radec_to_pixel(83.822, -5.391)
    print(f"  Centro RA/Dec -> pixel ({x:.1f}, {y:.1f})")
    assert abs(x - 1000) < 1
    assert abs(y - 750) < 1

    cat = AstroCatalog()
    cat.load_builtin()
    img = _make_test_image()

    annotations = annotate_image(img, wcs, cat)
    print(f"\n  Objetos anotados: {len(annotations)}")
    for ann in annotations:
        print(f"    {ann['label']} en pixel ({ann['x_px']:.0f}, {ann['y_px']:.0f})")

    print("  -> Plate Solving: OK\n")


def test_narrowband():
    print("=== Test Narrowband ===\n")
    from astro_belladev.narrowband import (
        extract_channel, combine_channels, combine_palette,
        combine_custom, continuum_subtraction,
        blend_narrowband_rgb, normalize_channels,
    )

    rng = np.random.RandomState(42)
    ha = rng.normal(1000, 50, (100, 100)).astype(np.float32)
    oiii = rng.normal(500, 30, (100, 100)).astype(np.float32)
    sii = rng.normal(700, 40, (100, 100)).astype(np.float32)

    channels = {"Ha": ha, "OIII": oiii, "SII": sii}

    for palette in ["SHO", "HOO", "HOS", "natural"]:
        result = combine_palette(channels, palette=palette)
        assert result.shape == (100, 100, 3)
        print(f"  Paleta {palette}: OK (shape={result.shape})")

    custom = combine_custom(channels, "Ha", "SII", "OIII",
                            r_weight=1.2, g_weight=0.8, b_weight=1.0)
    assert custom.shape == (100, 100, 3)
    print(f"  Custom combine: OK")

    broadband = rng.normal(800, 40, (100, 100)).astype(np.float32)
    subtracted = continuum_subtraction(ha, broadband, factor=0.8)
    assert subtracted.shape == (100, 100)
    assert subtracted.min() >= 0
    print(f"  Continuum subtraction: OK")

    rgb = np.stack([ha, oiii, sii], axis=-1) / 1000.0
    blended = blend_narrowband_rgb(rgb, ha / 1000.0, blend_channel="R",
                                    blend_mode="screen", opacity=0.5)
    assert blended.shape == rgb.shape
    print(f"  Blend Ha+RGB: OK")

    norm = normalize_channels(channels)
    for name, data in norm.items():
        assert data.min() >= 0 and data.max() <= 1.0
    print(f"  Normalize channels: OK")

    test_rgb = _make_test_image(100, 100)
    r = extract_channel(test_rgb, "R")
    g = extract_channel(test_rgb, 1)
    l = extract_channel(test_rgb, "L")
    assert r.ndim == 2 and g.ndim == 2 and l.ndim == 2
    print(f"  Extract channels R/G/L: OK")

    print("  -> Narrowband: OK\n")


def test_mosaic_hdr():
    print("=== Test Mosaico + HDR ===\n")
    from astro_belladev.mosaic import hdr_combine

    rng = np.random.RandomState(42)
    short = rng.normal(500, 30, (100, 100, 3)).astype(np.float32)
    long_exp = rng.normal(1000, 50, (100, 100, 3)).astype(np.float32)

    short[40:60, 40:60] = 8000
    long_exp[40:60, 40:60] = 15000

    hdr = hdr_combine(short, long_exp, blend_width=0.1)
    assert hdr.shape == short.shape
    print(f"  HDR combine: OK (shape={hdr.shape})")

    center_hdr = hdr[45:55, 45:55].mean()
    center_long = long_exp[45:55, 45:55].mean()
    print(f"  Centro HDR: {center_hdr:.0f} (long: {center_long:.0f})")

    print("  -> Mosaico/HDR: OK\n")


if __name__ == "__main__":
    test_catalog()
    test_platesolve()
    test_narrowband()
    test_mosaic_hdr()
    print("=" * 55)
    print("  TODOS LOS TESTS PASARON CORRECTAMENTE")
    print("=" * 55)
