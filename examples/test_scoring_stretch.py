"""
test_scoring_stretch.py
-----------------------
Valida el scoring de frames y el stretch con datos sintéticos.
Genera frames con distintas calidades y verifica que el scoring
los ordena correctamente y el stretch produce resultados válidos.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from astro_belladev.frame_scoring import score_frame, score_all, print_scores
from astro_belladev.stretch import (
    stretch_midtone, stretch_asinh, stretch_auto,
    stretch_image, _detect_target_type, TARGET_PROFILES,
)


def _make_star(y, x, fwhm=3.0, peak=5000, size=15):
    """Genera un parche gaussiano que simula una estrella."""
    yy, xx = np.mgrid[-size:size+1, -size:size+1]
    sigma = fwhm / 2.355
    star = peak * np.exp(-((yy)**2 + (xx)**2) / (2 * sigma**2))
    return star, y - size, x - size


def generate_frame(height=200, width=200, n_stars=30, fwhm=3.0,
                   elongation=1.0, noise_level=50, seed=None):
    """
    Genera un frame sintético con estrellas gaussianas y ruido.

    elongation > 1.0 simula trailing (estrellas alargadas).
    """
    rng = np.random.RandomState(seed)

    frame = rng.normal(1000, noise_level, (height, width)).astype(np.float32)

    for _ in range(n_stars):
        y = rng.randint(20, height - 20)
        x = rng.randint(20, width - 20)
        peak = rng.uniform(2000, 10000)
        star, y0, x0 = _make_star(y, x, fwhm=fwhm, peak=peak)

        if elongation > 1.0:
            yy, xx = np.mgrid[-15:16, -15:16]
            sigma_y = fwhm / 2.355 * elongation
            sigma_x = fwhm / 2.355
            star = peak * np.exp(-(yy**2 / (2*sigma_y**2) + xx**2 / (2*sigma_x**2)))

        sy = max(0, y0)
        sx = max(0, x0)
        ey = min(height, y0 + star.shape[0])
        ex = min(width, x0 + star.shape[1])

        star_sy = sy - y0
        star_sx = sx - x0
        star_ey = star_sy + (ey - sy)
        star_ex = star_sx + (ex - sx)

        frame[sy:ey, sx:ex] += star[star_sy:star_ey, star_sx:star_ex]

    frame = np.clip(frame, 0, None)
    return frame


def test_scoring():
    print("=== Test Frame Scoring ===\n")

    good_frame = generate_frame(
        n_stars=40, fwhm=2.5, noise_level=30, seed=42
    )
    medium_frame = generate_frame(
        n_stars=25, fwhm=4.0, noise_level=60, seed=43
    )
    bad_frame = generate_frame(
        n_stars=10, fwhm=6.0, elongation=2.0, noise_level=100, seed=44
    )
    terrible_frame = generate_frame(
        n_stars=2, fwhm=8.0, noise_level=200, seed=45
    )

    frames = [good_frame, medium_frame, bad_frame, terrible_frame]
    print(f"Generados {len(frames)} frames sintéticos con distintas calidades.")

    s_good = score_frame(good_frame, index=0)
    s_bad = score_frame(bad_frame, index=2)
    print(f"\n  Frame bueno:  FWHM={s_good.fwhm:.2f}, elong={s_good.elongation:.2f}, "
          f"ruido={s_good.background_noise:.1f}, estrellas={s_good.star_count}")
    print(f"  Frame malo:   FWHM={s_bad.fwhm:.2f}, elong={s_bad.elongation:.2f}, "
          f"ruido={s_bad.background_noise:.1f}, estrellas={s_bad.star_count}")

    assert s_good.background_noise < s_bad.background_noise, \
        "El frame bueno debe tener menos ruido"

    scores = score_all(frames, reject_percent=25, min_stars=5)
    print_scores(scores)

    assert scores[0].score >= scores[-1].score, \
        "Los scores deben estar ordenados de mejor a peor"

    rejected = [s for s in scores if not s.accepted]
    assert len(rejected) >= 1, "Al menos un frame debe ser rechazado"
    print(f"\n  Rechazados: {len(rejected)} frames")

    for s in rejected:
        print(f"    Frame #{s.index}: {s.rejection_reason}")

    print("\n  -> Scoring: OK\n")


def test_stretch_midtone():
    print("=== Test Stretch Midtone ===\n")

    frame = generate_frame(n_stars=30, fwhm=3.0, noise_level=30, seed=42)

    print(f"  Antes: min={frame.min():.0f}, max={frame.max():.0f}, "
          f"median={np.median(frame):.0f}")

    stretched = stretch_midtone(frame, midtone=0.25)

    print(f"  Después: min={stretched.min():.3f}, max={stretched.max():.3f}, "
          f"median={np.median(stretched):.3f}")

    assert stretched.min() >= 0.0, "El stretch no debe producir valores negativos"
    assert stretched.max() <= 1.0, "El stretch no debe superar 1.0"
    assert np.median(stretched) > 0.01, "El stretch debe subir la mediana del fondo"
    assert np.median(stretched) < 0.5, "El stretch no debe sobreexponer el fondo"

    print("  -> Stretch midtone: OK\n")


def test_stretch_asinh():
    print("=== Test Stretch Asinh ===\n")

    frame_rgb = np.stack([
        generate_frame(n_stars=30, fwhm=3.0, noise_level=30, seed=42),
        generate_frame(n_stars=30, fwhm=3.0, noise_level=30, seed=43),
        generate_frame(n_stars=30, fwhm=3.0, noise_level=30, seed=44),
    ], axis=-1)

    print(f"  Input RGB: shape={frame_rgb.shape}")
    stretched = stretch_asinh(frame_rgb, a=0.02)

    print(f"  Output: shape={stretched.shape}, "
          f"min={stretched.min():.3f}, max={stretched.max():.3f}")

    assert stretched.shape == frame_rgb.shape, "El shape debe preservarse"
    assert stretched.min() >= 0.0
    assert stretched.max() <= 1.0

    print("  -> Stretch asinh (RGB): OK\n")


def test_stretch_auto():
    print("=== Test Stretch Auto ===\n")

    frame = generate_frame(n_stars=30, fwhm=3.0, noise_level=30, seed=42)

    for target_type in TARGET_PROFILES:
        stretched = stretch_auto(frame, target_type=target_type)
        assert stretched.min() >= 0.0 and stretched.max() <= 1.0, \
            f"Perfil {target_type} produce valores fuera de rango"
        print(f"    Perfil '{target_type}': median={np.median(stretched):.3f}")

    print("\n  -> Stretch auto (todos los perfiles): OK\n")


def test_target_detection():
    print("=== Test Detección de Tipo de Target ===\n")

    starfield = generate_frame(
        n_stars=100, fwhm=2.5, noise_level=20, seed=42
    )
    detected = _detect_target_type(starfield)
    print(f"  100 estrellas -> detectado: '{detected}'")

    sparse = generate_frame(
        n_stars=5, fwhm=3.0, noise_level=50, seed=42
    )
    detected2 = _detect_target_type(sparse)
    print(f"  5 estrellas -> detectado: '{detected2}'")

    print("\n  -> Detección de target: OK\n")


def test_stretch_image_api():
    print("=== Test API stretch_image ===\n")

    frame = generate_frame(n_stars=30, fwhm=3.0, noise_level=30, seed=42)

    r1 = stretch_image(frame, method="auto")
    assert r1.min() >= 0.0 and r1.max() <= 1.0
    print(f"  method='auto': OK")

    r2 = stretch_image(frame, method="midtone", midtone=0.3)
    assert r2.min() >= 0.0 and r2.max() <= 1.0
    print(f"  method='midtone': OK")

    r3 = stretch_image(frame, method="asinh", a=0.05)
    assert r3.min() >= 0.0 and r3.max() <= 1.0
    print(f"  method='asinh': OK")

    try:
        stretch_image(frame, method="invalid")
        assert False, "Debería lanzar ValueError"
    except ValueError:
        print(f"  method='invalid': ValueError correctamente lanzado")

    print("\n  -> API stretch_image: OK\n")


if __name__ == "__main__":
    test_scoring()
    test_stretch_midtone()
    test_stretch_asinh()
    test_stretch_auto()
    test_target_detection()
    test_stretch_image_api()
    print("=" * 50)
    print("Todos los tests pasaron correctamente.")
