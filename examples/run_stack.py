"""
run_stack.py
------------
Ejemplo de uso del pipeline en modo auto y experto.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from astro_belladev.pipeline import run_pipeline

# --- Modo AUTO: no necesitas configurar nada ---
run_pipeline(
    bias_dir="test_data/bias",
    dark_dir="test_data/dark",
    flat_dir="test_data/flat",
    lights_dir="test_data/lights",
    output_path="resultado_auto.fits",
    mode="auto",
)

# --- Modo EXPERTO: control total ---
# run_pipeline(
#     bias_dir="test_data/bias",
#     dark_dir="test_data/dark",
#     flat_dir="test_data/flat",
#     lights_dir="test_data/lights",
#     output_path="resultado_experto.fits",
#     mode="expert",
#     stack_method="sigma_clip",
#     reject_percent=30,         # descartar hasta el 30% de los peores frames
#     min_stars=10,              # mínimo 10 estrellas para aceptar un frame
#     stretch_method="midtone",  # "auto", "midtone" o "asinh"
#     target_type="nebula",      # "nebula", "galaxy", "starfield", "planetary"
#     stretch_params={"midtone": 0.20, "black_clip": -2.5},
# )
