"""
pipeline.py
-----------
Orquesta el flujo completo de procesamiento de astrofotografía.

Dos modos de uso:
- Modo AUTO (mode="auto"): carga, calibra, puntúa frames, descarta
  los malos, debayerea, alinea, apila, estira y guarda. Sin tocar
  un solo parámetro.
- Modo EXPERTO (mode="expert"): cada paso es configurable, el usuario
  controla umbrales de descarte, método de stretch, patrón Bayer, etc.

Flujo completo:
  carga → calibración → scoring → descarte → debayer → alineación →
  apilamiento → stretch → guardado
"""

from pathlib import Path

from . import io_fits
from .io_tiff import save_tiff
from . import calibration
from . import alignment
from . import stacking
from .frame_scoring import score_all, print_scores
from .stretch import stretch_image


def run_pipeline(
    bias_dir=None,
    dark_dir=None,
    flat_dir=None,
    lights_dir=None,
    output_path="stacked_result.fits",
    mode="auto",
    stack_method="sigma_clip",
    debayer_pattern=None,
    auto_debayer=True,
    reject_percent=20,
    min_stars=5,
    stretch_method="auto",
    target_type=None,
    stretch_params=None,
    apply_stretch=True,
):
    """
    Parámetros
    ----------
    mode : str
        "auto" — el pipeline decide todo automáticamente.
        "expert" — el usuario controla cada parámetro.
    bias_dir, dark_dir, flat_dir : str o None
        Carpetas con los frames de calibración.
    lights_dir : str
        Carpeta con los light frames (obligatoria).
    output_path : str
        Ruta del archivo de salida (.fits, .tif, .tiff).
    stack_method : str
        "sigma_clip" (defecto), "average" o "median".
    debayer_pattern : str o None
        Fuerza un patrón Bayer. None = autodetección.
    auto_debayer : bool
        Aplicar debayer automáticamente (defecto True).
    reject_percent : int
        % máximo de frames a descartar por mala calidad (defecto 20).
    min_stars : int
        Mínimo de estrellas para aceptar un frame (defecto 5).
    stretch_method : str
        "auto", "midtone" o "asinh".
    target_type : str o None
        "nebula", "galaxy", "starfield", "planetary" o None (autodetectar).
    stretch_params : dict o None
        Parámetros para el stretch en modo experto (midtone, black_clip, a).
    apply_stretch : bool
        Si False, no aplica stretch (guarda el resultado lineal).
    """

    if mode == "auto":
        print("=" * 50)
        print("  ASTRO SUITE — Modo Automático")
        print("=" * 50)
    else:
        print("=" * 50)
        print("  ASTRO SUITE — Modo Experto")
        print("=" * 50)

    master_bias = None
    master_dark = None
    master_flat = None

    if bias_dir:
        print("\n[1/7] Cargando bias...")
        bias_frames, _ = io_fits.load_folder(bias_dir, auto_debayer=False)
        master_bias = calibration.create_master_bias(bias_frames)

    if dark_dir:
        print("\n[2/7] Cargando darks...")
        dark_frames, _ = io_fits.load_folder(dark_dir, auto_debayer=False)
        master_dark = calibration.create_master_dark(dark_frames, master_bias)

    if flat_dir:
        print("\n[3/7] Cargando flats...")
        flat_frames, _ = io_fits.load_folder(flat_dir, auto_debayer=False)
        master_flat = calibration.create_master_flat(flat_frames, master_bias)

    print("\n[4/7] Cargando light frames...")
    light_frames, light_paths = io_fits.load_folder(
        lights_dir, auto_debayer=False
    )
    print(f"  {len(light_frames)} light frames encontrados.")

    print("\n[4/7] Calibrando light frames...")
    calibrated_lights = [
        calibration.calibrate_light(light, master_bias, master_dark, master_flat)
        for light in light_frames
    ]

    # --- Scoring y descarte de frames ---
    print("\n[5/7] Evaluando calidad de frames...")
    scores = score_all(
        calibrated_lights,
        reject_percent=reject_percent,
        min_stars=min_stars,
    )
    print_scores(scores)

    accepted_indices = {s.index for s in scores if s.accepted}
    calibrated_lights = [
        calibrated_lights[s.index] for s in scores if s.accepted
    ]
    light_paths_filtered = [
        light_paths[s.index] for s in scores if s.accepted
    ] if light_paths else []

    if not calibrated_lights:
        raise RuntimeError(
            "Todos los frames fueron rechazados. Revisa la calidad de tus datos."
        )

    # --- Debayer ---
    if auto_debayer:
        from .debayer import debayer, detect_pattern

        debayered_lights = []
        for i, light in enumerate(calibrated_lights):
            if light.ndim == 2:
                pattern = debayer_pattern
                if pattern is None and light_paths_filtered:
                    path = light_paths_filtered[i]
                    if path.suffix.lower() in io_fits.FITS_EXTENSIONS:
                        _, header = io_fits.load_fits(path)
                        pattern = detect_pattern(header)
                    elif path.suffix.lower() in io_fits.RAW_EXTENSIONS:
                        from .io_raw import load_raw_bayer
                        _, pattern, _ = load_raw_bayer(path)

                if pattern is not None:
                    if i == 0:
                        print(f"\n  Debayer: patrón {pattern}")
                    debayered_lights.append(debayer(light, pattern=pattern))
                else:
                    debayered_lights.append(light)
            else:
                debayered_lights.append(light)

        calibrated_lights = debayered_lights

    # --- Alineación ---
    print("\n[5/7] Alineando light frames...")
    aligned_lights = alignment.align_all(calibrated_lights, reference_index=0)
    print(f"  {len(aligned_lights)} frames alineados correctamente.")

    # --- Apilamiento ---
    print(f"\n[6/7] Apilando con método '{stack_method}'...")
    result = stacking.stack_frames(aligned_lights, method=stack_method)

    # --- Stretch ---
    if apply_stretch:
        print(f"\n[7/7] Aplicando stretch...")
        params = stretch_params or {}
        result_stretched = stretch_image(
            result,
            method=stretch_method,
            target_type=target_type,
            **params,
        )
    else:
        print(f"\n[7/7] Stretch omitido (resultado lineal).")
        result_stretched = result

    # --- Guardado ---
    output_path_obj = Path(output_path)
    print(f"\nGuardando resultado en {output_path}")

    if output_path_obj.suffix.lower() in {".tif", ".tiff"}:
        save_tiff(output_path, result_stretched)
    else:
        io_fits.save_fits(output_path, result_stretched)

    # Guardar también el resultado lineal (sin stretch) como referencia
    if apply_stretch:
        linear_path = output_path_obj.with_name(
            output_path_obj.stem + "_linear" + output_path_obj.suffix
        )
        print(f"Guardando resultado lineal en {linear_path}")
        if linear_path.suffix.lower() in {".tif", ".tiff"}:
            save_tiff(str(linear_path), result)
        else:
            io_fits.save_fits(str(linear_path), result)

    print("\n¡Listo!")
    return result_stretched
