"""
generate_test_data.py
----------------------
Genera frames FITS sintéticos (bias, dark, flat, light) para poder
probar el pipeline completo sin necesidad de tener fotos reales
todavía. Útil para verificar que la instalación funciona.
"""

import sys
from pathlib import Path

# Permite ejecutar este script directamente sin tener que configurar
# PYTHONPATH a mano: añadimos la raíz del proyecto al path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from astro_belladev import io_fits

np.random.seed(42)

HEIGHT, WIDTH = 200, 200
N_FRAMES = 8

OUT_DIR = Path("test_data")
(OUT_DIR / "bias").mkdir(parents=True, exist_ok=True)
(OUT_DIR / "dark").mkdir(parents=True, exist_ok=True)
(OUT_DIR / "flat").mkdir(parents=True, exist_ok=True)
(OUT_DIR / "lights").mkdir(parents=True, exist_ok=True)


def add_fake_stars(image, n_stars=15):
    for _ in range(n_stars):
        y = np.random.randint(10, HEIGHT - 10)
        x = np.random.randint(10, WIDTH - 10)
        brightness = np.random.uniform(500, 3000)
        yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH]
        star = brightness * np.exp(-(((xx - x) ** 2 + (yy - y) ** 2) / (2 * 2.0 ** 2)))
        image += star
    return image


# --- Bias: solo ruido de lectura, sin señal ---
for i in range(N_FRAMES):
    bias = np.random.normal(100, 5, (HEIGHT, WIDTH)).astype(np.float32)
    io_fits.save_fits(OUT_DIR / "bias" / f"bias_{i:02d}.fits", bias)

# --- Dark: bias + corriente de oscuridad ---
for i in range(N_FRAMES):
    dark = np.random.normal(100, 5, (HEIGHT, WIDTH)) + np.random.normal(20, 3, (HEIGHT, WIDTH))
    io_fits.save_fits(OUT_DIR / "dark" / f"dark_{i:02d}.fits", dark.astype(np.float32))

# --- Flat: iluminación uniforme con un leve viñeteo ---
yy, xx = np.mgrid[0:HEIGHT, 0:WIDTH]
center_y, center_x = HEIGHT / 2, WIDTH / 2
distance = np.sqrt((xx - center_x) ** 2 + (yy - center_y) ** 2)
vignette = 1 - 0.3 * (distance / distance.max())

for i in range(N_FRAMES):
    flat = (20000 * vignette) + np.random.normal(100, 5, (HEIGHT, WIDTH))
    io_fits.save_fits(OUT_DIR / "flat" / f"flat_{i:02d}.fits", flat.astype(np.float32))

# --- Lights: una única escena de cielo+estrellas, desplazada ligeramente
#     entre frames (simula error de seguimiento de la montura) ---
base_sky = np.full((HEIGHT, WIDTH), 300, dtype=np.float32)
base_sky = add_fake_stars(base_sky, n_stars=20)

for i in range(N_FRAMES):
    sky = base_sky.copy()

    shift_y, shift_x = np.random.randint(-3, 4, 2)
    sky = np.roll(sky, (shift_y, shift_x), axis=(0, 1))
    fill_value = 300.0
    if shift_y > 0:
        sky[:shift_y, :] = fill_value
    elif shift_y < 0:
        sky[shift_y:, :] = fill_value
    if shift_x > 0:
        sky[:, :shift_x] = fill_value
    elif shift_x < 0:
        sky[:, shift_x:] = fill_value

    sky *= vignette  # el flat afecta también a la luz real
    noise = np.random.normal(100, 5, (HEIGHT, WIDTH)) + np.random.normal(20, 3, (HEIGHT, WIDTH))
    light = sky + noise

    io_fits.save_fits(OUT_DIR / "lights" / f"light_{i:02d}.fits", light.astype(np.float32))

print(f"Datos de prueba generados en: {OUT_DIR.resolve()}")
