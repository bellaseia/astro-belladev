"""
scripts.py
----------
Sistema de scripts para Astro BellaDev.

Soporta dos formatos:
- .py (Python nativo): el usuario escribe Python real
  usando las funciones de astro_belladev.
- .abs (formato simple): una accion por linea con parametros.

Los scripts .py tienen acceso completo al motor:
    from astro_belladev.stretch import stretch_midtone
    from astro_belladev.denoise import denoise_image
    # etc.

Template de script .py:
    # -*- coding: utf-8 -*-
    # Nombre: Mi Script
    # Autor: Usuario
    # Descripcion: Mi procesamiento personalizado
    # Categoria: Custom

    def run(image, registry, progress):
        '''Funcion principal del script.
        image: numpy array de la imagen actual
        registry: ActionRegistry con todas las acciones
        progress: funcion para reportar progreso
        Devuelve: numpy array con el resultado
        '''
        from astro_belladev.stretch import stretch_midtone
        result = stretch_midtone(image, midtone=0.20)
        progress("Stretch aplicado")
        return result
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class ScriptInfo:
    name: str = ""
    author: str = ""
    description: str = ""
    category: str = "Other"
    requires: str = ""
    filename: str = ""
    path: str = ""
    script_type: str = "abs"  # "abs" o "py"
    steps: list = field(default_factory=list)


@dataclass
class ScriptStep:
    action_id: str
    params: dict = field(default_factory=dict)
    comment: str = ""


def parse_script(text, script_type="abs"):
    """Parsea el contenido de un script."""
    info = ScriptInfo(script_type=script_type)
    steps = []

    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("#"):
            meta = line[1:].strip()
            if ":" in meta and not meta.startswith("-"):
                key, value = meta.split(":", 1)
                key = key.strip().lower()
                value = value.strip()
                if key in ("nombre", "name"):
                    info.name = value
                elif key in ("autor", "author"):
                    info.author = value
                elif key in ("descripcion", "description"):
                    info.description = value
                elif key in ("categoria", "category"):
                    info.category = value
                elif key == "requires":
                    info.requires = value
            continue

        if script_type == "abs":
            parts = line.split()
            if not parts:
                continue
            action_id = parts[0]
            params = {}
            for part in parts[1:]:
                if "=" in part:
                    k, v = part.split("=", 1)
                    try:
                        if "." in v:
                            params[k] = float(v)
                        else:
                            params[k] = int(v)
                    except ValueError:
                        params[k] = v
            steps.append(ScriptStep(action_id=action_id, params=params))

    info.steps = steps
    return info


def generate_script(info):
    """Genera el texto de un script."""
    lines = []
    lines.append(f"# Nombre: {info.name}")
    if info.author:
        lines.append(f"# Autor: {info.author}")
    if info.description:
        lines.append(f"# Descripcion: {info.description}")
    if info.category:
        lines.append(f"# Categoria: {info.category}")
    lines.append(f"# Requires: astro_belladev >= 1.1.0")
    lines.append("")

    if info.script_type == "py":
        lines.append("def run(image, registry, progress):")
        lines.append("    '''Script principal.'''")
        for step in info.steps:
            params_str = ", ".join(
                f"{k}={repr(v)}" for k, v in step.params.items()
            )
            lines.append(
                f"    action = registry.get('{step.action_id}')"
            )
            if params_str:
                lines.append(
                    f"    image = action.execute(image, {params_str})"
                )
            else:
                lines.append(
                    f"    image = action.execute(image)"
                )
            lines.append(
                f"    progress('{step.action_id} aplicado')"
            )
        lines.append("    return image")
    else:
        for step in info.steps:
            params_str = " ".join(
                f"{k}={v}" for k, v in step.params.items()
            )
            line = step.action_id
            if params_str:
                line += " " + params_str
            lines.append(line)

    return "\n".join(lines)


def generate_py_template():
    """Genera un template de script .py para el usuario."""
    return '''# -*- coding: utf-8 -*-
# Nombre: Mi Script
# Autor: Usuario
# Descripcion: Descripcion de lo que hace
# Categoria: Custom

def run(image, registry, progress):
    """Funcion principal del script.

    Parametros:
        image: numpy array (la imagen actual)
        registry: ActionRegistry (102 acciones disponibles)
        progress: funcion para reportar progreso al log

    Devuelve:
        numpy array con el resultado

    Ejemplo de acciones disponibles:
        stretch_midtone, stretch_auto, stretch_asinh
        background_abe, denoise_selective, denoise_bilateral
        wb_auto, wb_stars, saturation, saturation_selective
        sharpen_usm, sharpen_deconv, clahe, local_contrast
        scnr_average, scnr_maximum, extract_starless
        diffraction_spikes, star_reduction, reduce_halos
        ai_denoise_wavelet, ai_denoise_bm3d, ai_enhance_detail

    Tambien puedes importar directamente:
        from astro_belladev.stretch import stretch_midtone
        from astro_belladev.denoise import denoise_image
        from astro_belladev.color import white_balance_stars
    """

    # Ejemplo: stretch + denoise + color
    progress("Aplicando stretch...")
    action = registry.get("stretch_midtone")
    image = action.execute(image, midtone=0.22, black_clip=-2.8)

    progress("Aplicando denoise...")
    action = registry.get("denoise_selective")
    image = action.execute(image, lum_strength=0.5, chrom_strength=0.3)

    progress("Balance de blancos...")
    action = registry.get("wb_stars")
    image = action.execute(image)

    progress("Completado!")
    return image
'''


def execute_script(script_info, session, registry, progress=None):
    """Ejecuta un script sobre la sesion actual."""
    if session.current_data is None:
        raise RuntimeError("No hay imagen cargada")

    def _progress(msg):
        if progress:
            progress.log(msg)
        print(msg)

    if script_info.script_type == "py" and script_info.path:
        return _execute_py_script(
            script_info, session, registry, _progress
        )

    # Ejecutar .abs (formato simple)
    total = len(script_info.steps)
    for i, step in enumerate(script_info.steps):
        action = registry.get(step.action_id)
        if action is None:
            _progress(f"  Accion '{step.action_id}' no encontrada")
            continue

        _progress(f"  [{i+1}/{total}] {step.action_id}")
        try:
            session.apply(action, **step.params)
        except Exception as e:
            _progress(f"  Error: {e}")

    return session.current_data


def _execute_py_script(script_info, session, registry, progress):
    """Ejecuta un script .py."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "user_script", script_info.path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, "run"):
        result = module.run(
            session.current_data.copy(),
            registry,
            progress,
        )
        if result is not None:
            import numpy as np
            session.current_data = result.astype(np.float32)
    else:
        raise RuntimeError(
            "El script .py debe tener una funcion run(image, registry, progress)"
        )

    return session.current_data


class ScriptManager:
    """Gestiona scripts .abs y .py."""

    def __init__(self, scripts_dirs=None):
        self._scripts = {}
        self._dirs = scripts_dirs or []

        if not self._dirs:
            # Solo usar carpeta del usuario (funciona en .exe)
            user_dir = Path.home() / ".astro_belladev" / "scripts"
            user_dir.mkdir(parents=True, exist_ok=True)
            self._dirs.append(str(user_dir))

            # Carpeta junto al modulo (solo en desarrollo)
            try:
                app_dir = Path(__file__).parent / "scripts"
                app_dir.mkdir(exist_ok=True)
                self._dirs.insert(0, str(app_dir))
            except (OSError, PermissionError):
                pass

    def scan(self):
        self._scripts.clear()
        for scripts_dir in self._dirs:
            d = Path(scripts_dir)
            if not d.exists():
                continue

            for ext in ["*.abs", "*.py"]:
                for f in d.glob(ext):
                    try:
                        text = f.read_text(encoding="utf-8")
                        stype = "py" if f.suffix == ".py" else "abs"
                        info = parse_script(text, stype)
                        info.filename = f.name
                        info.path = str(f)
                        info.script_type = stype
                        if not info.name:
                            info.name = f.stem
                        self._scripts[f.stem] = info
                    except Exception:
                        pass

    def get_all(self):
        return list(self._scripts.values())

    def get_by_category(self, category):
        return [s for s in self._scripts.values()
                if s.category == category]

    def get_categories(self):
        return sorted(set(
            s.category for s in self._scripts.values()
        ))

    def get(self, name):
        return self._scripts.get(name)

    def save_script(self, info, directory=None):
        if directory is None:
            directory = self._dirs[-1]

        if info.script_type == "py":
            ext = ".py"
        else:
            ext = ".abs"

        filename = info.filename or (
            info.name.lower().replace(" ", "_") + ext
        )
        path = Path(directory) / filename

        text = generate_script(info)
        path.write_text(text, encoding="utf-8")
        info.path = str(path)
        info.filename = filename

        return str(path)

    def save_py_template(self, directory=None):
        """Guarda el template .py para el usuario."""
        if directory is None:
            directory = self._dirs[-1]
        path = Path(directory) / "mi_script_template.py"
        path.write_text(generate_py_template(), encoding="utf-8")
        return str(path)

    def create_builtin_scripts(self):
        builtins = [
            ScriptInfo(
                name="OSC Preprocessing",
                author="BellaDev",
                description="Pipeline completo para camaras a color (OSC/DSLR)",
                category="Pre-procesamiento",
                steps=[
                    ScriptStep("stretch_auto"),
                    ScriptStep("background_abe", {"grid_size": 10, "degree": 3}),
                    ScriptStep("scnr_average", {"amount": 1.0}),
                    ScriptStep("denoise_selective", {"lum_strength": 0.5, "chrom_strength": 0.3}),
                    ScriptStep("wb_stars"),
                    ScriptStep("saturation", {"factor": 1.3}),
                    ScriptStep("sharpen_usm", {"radius": 2.0, "amount": 0.8}),
                ],
            ),
            ScriptInfo(
                name="Mono Preprocessing",
                author="BellaDev",
                description="Pipeline para camaras monocromaticas con filtro L",
                category="Pre-procesamiento",
                steps=[
                    ScriptStep("stretch_midtone", {"midtone": 0.25, "black_clip": -2.8}),
                    ScriptStep("background_abe", {"grid_size": 8, "degree": 3}),
                    ScriptStep("denoise_selective", {"lum_strength": 0.6, "chrom_strength": 0.1}),
                    ScriptStep("sharpen_deconv", {"psf_sigma": 1.5, "iterations": 15}),
                ],
            ),
            ScriptInfo(
                name="Seestar S30 Pro (Solo Lights)",
                author="BellaDev",
                description="Procesamiento directo para imagenes del Seestar S30 Pro. Solo necesita los lights apilados, sin calibracion.",
                category="Telescopios inteligentes",
                steps=[
                    ScriptStep("stretch_auto", {"target_type": ""}),
                    ScriptStep("background_abe", {"grid_size": 12, "degree": 4}),
                    ScriptStep("scnr_average", {"amount": 0.8}),
                    ScriptStep("denoise_selective", {"lum_strength": 0.5, "chrom_strength": 0.3}),
                    ScriptStep("wb_auto", {"percentile": 95}),
                    ScriptStep("saturation", {"factor": 1.4}),
                    ScriptStep("sharpen_usm", {"radius": 1.5, "amount": 0.7}),
                    ScriptStep("clahe", {"clip_limit": 1.5, "grid_size": 8}),
                ],
            ),
            ScriptInfo(
                name="Nebulosa Ha (Narrowband)",
                author="BellaDev",
                description="Procesamiento optimizado para imagenes Ha de nebulosas de emision",
                category="Narrowband",
                steps=[
                    ScriptStep("stretch_midtone", {"midtone": 0.18, "black_clip": -3.0}),
                    ScriptStep("background_abe", {"grid_size": 10, "degree": 3}),
                    ScriptStep("denoise_selective", {"lum_strength": 0.7, "chrom_strength": 0.2}),
                    ScriptStep("sharpen_usm", {"radius": 2.0, "amount": 1.0}),
                    ScriptStep("clahe", {"clip_limit": 2.0, "grid_size": 8}),
                ],
            ),
            ScriptInfo(
                name="Galaxia con Nucleo",
                author="BellaDev",
                description="Stretch suave para preservar detalle en nucleos brillantes de galaxias",
                category="Objetos",
                steps=[
                    ScriptStep("stretch_midtone", {"midtone": 0.30, "black_clip": -2.0}),
                    ScriptStep("background_abe", {"grid_size": 12, "degree": 4}),
                    ScriptStep("denoise_selective", {"lum_strength": 0.4, "chrom_strength": 0.2}),
                    ScriptStep("wb_stars"),
                    ScriptStep("saturation", {"factor": 1.2}),
                    ScriptStep("sharpen_deconv", {"psf_sigma": 1.5, "iterations": 10}),
                ],
            ),
            ScriptInfo(
                name="Campo Estelar Colores",
                author="BellaDev",
                description="Potencia los colores estelares en campos de estrellas",
                category="Objetos",
                steps=[
                    ScriptStep("stretch_asinh", {"a": 0.02, "black_clip": -2.8}),
                    ScriptStep("wb_stars"),
                    ScriptStep("saturation", {"factor": 1.6}),
                    ScriptStep("reduce_halos", {"halo_radius": 3, "strength": 0.5}),
                ],
            ),
            ScriptInfo(
                name="Quick Process (Rapido)",
                author="BellaDev",
                description="Procesamiento rapido en 3 pasos: stretch + denoise + WB",
                category="Rapido",
                steps=[
                    ScriptStep("stretch_auto"),
                    ScriptStep("denoise_selective", {"lum_strength": 0.4}),
                    ScriptStep("wb_auto"),
                ],
            ),
            ScriptInfo(
                name="SCNR (Eliminar Ruido Verde)",
                author="BellaDev",
                description="Equivalente al proceso SCNR de PixInsight. Elimina exceso de verde + denoise + WB.",
                category="Color",
                steps=[
                    ScriptStep("scnr_average", {"amount": 1.0}),
                    ScriptStep("denoise_selective", {"lum_strength": 0.3, "chrom_strength": 0.5}),
                    ScriptStep("wb_stars"),
                ],
            ),
            ScriptInfo(
                name="SCNR Agresivo + Color",
                author="BellaDev",
                description="SCNR maximum mask + WB + saturacion + denoise",
                category="Color",
                steps=[
                    ScriptStep("scnr_maximum", {"amount": 1.0}),
                    ScriptStep("wb_stars"),
                    ScriptStep("saturation", {"factor": 1.3}),
                    ScriptStep("denoise_selective", {"lum_strength": 0.4, "chrom_strength": 0.3}),
                ],
            ),
            ScriptInfo(
                name="Post-procesamiento Completo",
                author="BellaDev",
                description="Pipeline completo: stretch + ABE + SCNR + denoise + color + sharpen + CLAHE",
                category="Completo",
                steps=[
                    ScriptStep("stretch_midtone", {"midtone": 0.22, "black_clip": -2.8}),
                    ScriptStep("background_abe", {"grid_size": 10, "degree": 3}),
                    ScriptStep("scnr_average", {"amount": 0.8}),
                    ScriptStep("denoise_selective", {"lum_strength": 0.5, "chrom_strength": 0.3}),
                    ScriptStep("wb_stars"),
                    ScriptStep("saturation", {"factor": 1.3}),
                    ScriptStep("sharpen_usm", {"radius": 2.0, "amount": 0.8}),
                    ScriptStep("clahe", {"clip_limit": 1.5, "grid_size": 8}),
                ],
            ),
        ]

        for script in builtins:
            self.save_script(script, self._dirs[0])

        # Guardar template .py
        self.save_py_template(self._dirs[-1])

        self.scan()
