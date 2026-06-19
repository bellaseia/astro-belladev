"""
batch.py
--------
Procesamiento por lotes (batch): aplica la misma secuencia de
operaciones a multiples imagenes o sesiones.

Casos de uso:
- Procesar 15 noches de M31 con los mismos parametros.
- Aplicar una macro a todas las imagenes de una carpeta.
- Re-procesar con parametros diferentes sin repetir el pipeline.

El batch usa las macros del toolbar o un plan del asistente
y las ejecuta sobre cada imagen/sesion de forma autonoma.
"""

from pathlib import Path
from datetime import datetime
from .session import Session
from .progress import ConsoleProgress, SilentProgress
from .actions import build_default_registry
from .toolbar import MacroStep
from . import io_fits
from .export import save_image


def batch_process(input_paths, steps, output_dir, output_format=".fits",
                  progress=None, registry=None):
    """
    Procesa multiples imagenes con la misma secuencia de pasos.

    Parametros
    ----------
    input_paths : list of str/Path
        Rutas a las imagenes de entrada.
    steps : list of MacroStep o list of dict
        Secuencia de acciones a aplicar a cada imagen.
        Cada step tiene action_id y params.
    output_dir : str/Path
        Carpeta donde guardar los resultados.
    output_format : str
        ".fits", ".tiff", ".png" o ".jpg".
    progress : ProgressCallback o None
    registry : ActionRegistry o None
    """
    if registry is None:
        registry = build_default_registry()
    if progress is None:
        progress = ConsoleProgress()

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if steps and isinstance(steps[0], dict):
        steps = [MacroStep(s["action_id"], s.get("params", {})) for s in steps]

    total = len(input_paths)
    progress.start_pipeline("batch", total)
    results = []

    for idx, input_path in enumerate(input_paths):
        input_path = Path(input_path)
        progress.start_step(
            f"Procesando {input_path.name}",
            step_number=idx + 1,
            total=total,
        )

        try:
            session = Session(progress=SilentProgress())
            data, header = io_fits.load_image(str(input_path))
            session.load_image(data, source_info=str(input_path))

            for step in steps:
                if not step.enabled:
                    continue
                action = registry.get(step.action_id)
                if action is None:
                    progress.warning(
                        f"Accion '{step.action_id}' no encontrada, saltando"
                    )
                    continue
                session.apply(action, **step.params)

            output_name = input_path.stem + "_processed" + output_format
            output_path = output_dir / output_name
            save_image(str(output_path), session.current_data)

            results.append({
                "input": str(input_path),
                "output": str(output_path),
                "success": True,
                "steps_applied": len(session.get_history()),
            })

            progress.end_step(f"OK -> {output_name}")

        except Exception as e:
            results.append({
                "input": str(input_path),
                "output": None,
                "success": False,
                "error": str(e),
            })
            progress.error(f"{input_path.name}: {e}")

    success = sum(1 for r in results if r["success"])
    progress.end_pipeline(
        success == total,
        f"{success}/{total} imagenes procesadas correctamente"
    )

    return results


def batch_from_macro(input_dir, macro_button, output_dir,
                      output_format=".fits", file_pattern="*"):
    """
    Procesa todos los archivos de una carpeta usando un boton macro.

    Parametros
    ----------
    input_dir : str/Path
        Carpeta con las imagenes de entrada.
    macro_button : ToolButton
        Boton macro del toolbar con los pasos a aplicar.
    output_dir : str/Path
        Carpeta de salida.
    file_pattern : str
        Patron glob para filtrar archivos ("*.fits", "*.tiff", etc.)
    """
    input_dir = Path(input_dir)

    all_extensions = io_fits.ALL_EXTENSIONS
    input_paths = sorted([
        p for p in input_dir.iterdir()
        if p.suffix.lower() in all_extensions
    ])

    if not input_paths:
        raise FileNotFoundError(
            f"No se encontraron imagenes en {input_dir}"
        )

    if not macro_button.is_macro:
        steps = [MacroStep(macro_button.action_id, macro_button.params)]
    else:
        steps = macro_button.macro

    return batch_process(
        input_paths, steps, output_dir,
        output_format=output_format,
    )


def batch_from_plan(input_paths, plan, output_dir, output_format=".fits"):
    """
    Procesa imagenes usando un plan generado por el asistente.

    Parametros
    ----------
    plan : list of dict
        Plan del asistente (generate_processing_plan).
    """
    steps = [
        MacroStep(p["action_id"], p.get("params", {}))
        for p in plan
        if p.get("action_id")
    ]

    return batch_process(
        input_paths, steps, output_dir,
        output_format=output_format,
    )


def print_batch_results(results):
    """Imprime resumen de los resultados del batch."""
    print(f"\n  RESULTADOS DEL BATCH")
    print(f"  {'=' * 55}")

    for r in results:
        input_name = Path(r["input"]).name
        if r["success"]:
            output_name = Path(r["output"]).name
            print(f"    OK  {input_name} -> {output_name} "
                  f"({r['steps_applied']} pasos)")
        else:
            print(f"    ERR {input_name}: {r.get('error', 'desconocido')}")

    success = sum(1 for r in results if r["success"])
    total = len(results)
    print(f"\n  {success}/{total} procesadas correctamente")
