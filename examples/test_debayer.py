"""
test_debayer.py
---------------
Genera una imagen Bayer sintética (RGGB) y valida que el debayer
produce una imagen RGB con las dimensiones y valores correctos.
También prueba la carga/guardado de TIFF.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
from astro_belladev.debayer import debayer, is_bayer, detect_pattern
from astro_belladev.io_tiff import save_tiff, load_tiff


def generate_synthetic_bayer(height=100, width=100, pattern="RGGB"):
    """
    Genera una imagen Bayer sintética donde cada canal tiene un valor
    distinto para poder verificar que el debayer los separa correctamente.

    Para RGGB:
      R  G1    fila par:    pixel par=R(1000), pixel impar=G(500)
      G2 B     fila impar:  pixel par=G(500),  pixel impar=B(200)
    """
    bayer = np.zeros((height, width), dtype=np.float32)

    if pattern == "RGGB":
        bayer[0::2, 0::2] = 1000.0  # R
        bayer[0::2, 1::2] = 500.0   # G1
        bayer[1::2, 0::2] = 500.0   # G2
        bayer[1::2, 1::2] = 200.0   # B
    elif pattern == "BGGR":
        bayer[0::2, 0::2] = 200.0   # B
        bayer[0::2, 1::2] = 500.0   # G1
        bayer[1::2, 0::2] = 500.0   # G2
        bayer[1::2, 1::2] = 1000.0  # R

    return bayer


def test_debayer():
    print("=== Test Debayer ===\n")

    bayer = generate_synthetic_bayer(200, 200, "RGGB")
    print(f"Imagen Bayer sintética: shape={bayer.shape}, "
          f"min={bayer.min():.0f}, max={bayer.max():.0f}")

    assert bayer.ndim == 2, "La imagen Bayer debe ser 2D"
    assert is_bayer(bayer), "is_bayer debe detectar imagen 2D como posible Bayer"

    rgb = debayer(bayer, pattern="RGGB", method="vng")
    print(f"Resultado debayer VNG: shape={rgb.shape}")

    assert rgb.ndim == 3, f"El resultado debe ser 3D, pero es {rgb.ndim}D"
    assert rgb.shape == (200, 200, 3), f"Shape esperado (200,200,3), obtenido {rgb.shape}"
    assert rgb.shape[-1] == 3, "El último eje debe ser 3 (RGB)"

    r_mean = rgb[50:150, 50:150, 0].mean()
    g_mean = rgb[50:150, 50:150, 1].mean()
    b_mean = rgb[50:150, 50:150, 2].mean()
    print(f"Valores medios centrales: R={r_mean:.1f}, G={g_mean:.1f}, B={b_mean:.1f}")

    assert r_mean > b_mean, "El canal R debe tener más señal que el B"
    assert r_mean > g_mean, "El canal R debe tener más señal que el G"

    print("  -> Debayer VNG: OK\n")

    rgb_bilinear = debayer(bayer, pattern="RGGB", method="bilinear")
    print(f"Resultado debayer bilinear: shape={rgb_bilinear.shape}")
    assert rgb_bilinear.shape == (200, 200, 3)
    print("  -> Debayer bilinear: OK\n")


def test_tiff():
    print("=== Test TIFF I/O ===\n")

    try:
        import tifffile
    except ImportError:
        print("  tifffile no instalado, saltando test TIFF.")
        return

    test_data = np.random.rand(100, 100, 3).astype(np.float32) * 1000
    test_path = os.path.join(os.path.dirname(__file__), "_test_output.tiff")

    save_tiff(test_path, test_data, bits=32)
    print(f"  Guardado TIFF 32-bit: {test_path}")

    loaded = load_tiff(test_path)
    print(f"  Cargado: shape={loaded.shape}, dtype={loaded.dtype}")

    assert loaded.shape == (100, 100, 3) or loaded.shape == (3, 100, 100), \
        f"Shape inesperado: {loaded.shape}"

    os.remove(test_path)

    save_tiff(test_path, test_data, bits=16)
    print(f"  Guardado TIFF 16-bit: {test_path}")

    loaded_16 = load_tiff(test_path)
    print(f"  Cargado 16-bit: shape={loaded_16.shape}, dtype={loaded_16.dtype}")

    os.remove(test_path)
    print("  -> TIFF I/O: OK\n")


def test_pattern_detection():
    print("=== Test detección de patrón ===\n")

    from astropy.io import fits as astropy_fits

    header = astropy_fits.Header()
    header["BAYERPAT"] = "RGGB"
    pattern = detect_pattern(header)
    assert pattern == "RGGB", f"Esperado RGGB, obtenido {pattern}"
    print(f"  BAYERPAT='RGGB' -> detectado: {pattern}")

    header2 = astropy_fits.Header()
    header2["COLORTYP"] = "BGGR"
    pattern2 = detect_pattern(header2)
    assert pattern2 == "BGGR", f"Esperado BGGR, obtenido {pattern2}"
    print(f"  COLORTYP='BGGR' -> detectado: {pattern2}")

    header3 = astropy_fits.Header()
    pattern3 = detect_pattern(header3)
    assert pattern3 is None, f"Esperado None, obtenido {pattern3}"
    print(f"  Sin keyword -> detectado: {pattern3}")

    print("  -> Detección de patrón: OK\n")


if __name__ == "__main__":
    test_debayer()
    test_tiff()
    test_pattern_detection()
    print("=" * 40)
    print("Todos los tests pasaron correctamente.")
