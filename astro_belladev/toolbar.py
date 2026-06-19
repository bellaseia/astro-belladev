"""
toolbar.py
----------
Sistema de barras de herramientas personalizables, inspirado en los
"Process Icons" de PixInsight.

El usuario puede:
- Crear botones personalizados con una accion + parametros prefijados.
- Organizar botones en barras de herramientas (toolbars).
- Guardar/cargar configuraciones de toolbar (perfiles).
- Encadenar varias acciones en un solo boton (macros).
- Arrastrar acciones del menu a la toolbar (drag & drop en la GUI).

Ejemplo:
    toolbar = Toolbar("Mi barra")
    toolbar.add_button(ToolButton(
        id="mi_stretch",
        label="Stretch Nebulosa",
        action_id="stretch_midtone",
        params={"midtone": 0.18, "black_clip": -3.0},
        icon="stretch",
        color="#FF6B6B",
        tooltip="Stretch agresivo para nebulosas de emision",
    ))

    # Macro: varias acciones en secuencia
    toolbar.add_button(ToolButton(
        id="post_nebula",
        label="Post Nebulosa",
        macro=[
            MacroStep("stretch_midtone", {"midtone": 0.18}),
            MacroStep("background_abe", {"grid_size": 10}),
            MacroStep("denoise_selective", {"lum_strength": 0.6}),
            MacroStep("saturation", {"factor": 1.4}),
        ],
        icon="macro",
        color="#4ECDC4",
        tooltip="Pipeline completo para nebulosas",
    ))
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class MacroStep:
    """Un paso dentro de una macro (accion + parametros)."""
    action_id: str
    params: dict = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self):
        return {
            "action_id": self.action_id,
            "params": self.params,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            action_id=data["action_id"],
            params=data.get("params", {}),
            enabled=data.get("enabled", True),
        )


@dataclass
class ToolButton:
    """
    Un boton personalizable de la toolbar.

    Puede ser:
    - Boton simple: una accion con parametros fijos.
    - Macro: secuencia de acciones que se ejecutan en orden.
    """
    id: str
    label: str
    action_id: str = ""
    params: dict = field(default_factory=dict)
    macro: list = field(default_factory=list)
    icon: str = ""
    color: str = "#4A90D9"
    tooltip: str = ""
    shortcut: str = ""
    visible: bool = True
    position: int = 0

    @property
    def is_macro(self):
        return len(self.macro) > 0

    def to_dict(self):
        data = {
            "id": self.id,
            "label": self.label,
            "action_id": self.action_id,
            "params": self.params,
            "icon": self.icon,
            "color": self.color,
            "tooltip": self.tooltip,
            "shortcut": self.shortcut,
            "visible": self.visible,
            "position": self.position,
        }
        if self.macro:
            data["macro"] = [step.to_dict() for step in self.macro]
        return data

    @classmethod
    def from_dict(cls, data):
        macro = [MacroStep.from_dict(s) for s in data.get("macro", [])]
        return cls(
            id=data["id"],
            label=data["label"],
            action_id=data.get("action_id", ""),
            params=data.get("params", {}),
            macro=macro,
            icon=data.get("icon", ""),
            color=data.get("color", "#4A90D9"),
            tooltip=data.get("tooltip", ""),
            shortcut=data.get("shortcut", ""),
            visible=data.get("visible", True),
            position=data.get("position", 0),
        )


class Toolbar:
    """
    Una barra de herramientas con botones personalizables.
    La GUI renderiza cada Toolbar como una fila/columna de botones.
    """

    def __init__(self, name="Principal", toolbar_id=None):
        self.name = name
        self.id = toolbar_id or name.lower().replace(" ", "_")
        self.buttons = []
        self.visible = True
        self.position = "top"  # top, bottom, left, right, floating

    def add_button(self, button):
        button.position = len(self.buttons)
        self.buttons.append(button)

    def remove_button(self, button_id):
        self.buttons = [b for b in self.buttons if b.id != button_id]
        for i, b in enumerate(self.buttons):
            b.position = i

    def move_button(self, button_id, new_position):
        button = self.get_button(button_id)
        if button is None:
            return
        self.buttons.remove(button)
        new_position = max(0, min(new_position, len(self.buttons)))
        self.buttons.insert(new_position, button)
        for i, b in enumerate(self.buttons):
            b.position = i

    def get_button(self, button_id):
        for b in self.buttons:
            if b.id == button_id:
                return b
        return None

    def execute_button(self, button_id, session, registry):
        """
        Ejecuta un boton sobre la sesion actual.
        Para macros, ejecuta cada paso en secuencia.
        """
        button = self.get_button(button_id)
        if button is None:
            raise ValueError(f"Boton '{button_id}' no encontrado")

        if button.is_macro:
            results = []
            for step in button.macro:
                if not step.enabled:
                    continue
                action = registry.get(step.action_id)
                if action is None:
                    raise ValueError(
                        f"Macro '{button.label}': accion '{step.action_id}' no existe"
                    )
                result = session.apply(action, **step.params)
                results.append(result)
            return results[-1] if results else session.current_data
        else:
            action = registry.get(button.action_id)
            if action is None:
                raise ValueError(
                    f"Boton '{button.label}': accion '{button.action_id}' no existe"
                )
            return session.apply(action, **button.params)

    def to_dict(self):
        return {
            "name": self.name,
            "id": self.id,
            "visible": self.visible,
            "position": self.position,
            "buttons": [b.to_dict() for b in self.buttons],
        }

    @classmethod
    def from_dict(cls, data):
        toolbar = cls(name=data["name"], toolbar_id=data.get("id"))
        toolbar.visible = data.get("visible", True)
        toolbar.position = data.get("position", "top")
        for btn_data in data.get("buttons", []):
            toolbar.add_button(ToolButton.from_dict(btn_data))
        return toolbar


class ToolbarManager:
    """
    Gestiona multiples toolbars y perfiles de configuracion.
    Persiste la configuracion en un archivo JSON.
    """

    def __init__(self, config_dir=None):
        self.toolbars = {}
        self.presets = {}
        self._config_dir = Path(config_dir) if config_dir else None

    def add_toolbar(self, toolbar):
        self.toolbars[toolbar.id] = toolbar

    def remove_toolbar(self, toolbar_id):
        self.toolbars.pop(toolbar_id, None)

    def get_toolbar(self, toolbar_id):
        return self.toolbars.get(toolbar_id)

    def get_all_toolbars(self):
        return list(self.toolbars.values())

    # --- Presets: acciones con parametros guardados ---

    def save_preset(self, name, action_id, params, description=""):
        """
        Guarda un preset (accion + parametros con nombre).
        Los presets se pueden reutilizar en botones y macros.
        """
        self.presets[name] = {
            "name": name,
            "action_id": action_id,
            "params": params,
            "description": description,
            "created": datetime.now().isoformat(),
        }

    def get_preset(self, name):
        return self.presets.get(name)

    def delete_preset(self, name):
        self.presets.pop(name, None)

    def list_presets(self):
        return list(self.presets.values())

    def create_button_from_preset(self, preset_name, label=None,
                                   color="#4A90D9"):
        """Crea un ToolButton a partir de un preset guardado."""
        preset = self.presets.get(preset_name)
        if preset is None:
            raise ValueError(f"Preset '{preset_name}' no encontrado")

        return ToolButton(
            id=f"preset_{preset_name}",
            label=label or preset["name"],
            action_id=preset["action_id"],
            params=preset["params"],
            tooltip=preset.get("description", ""),
            color=color,
        )

    # --- Persistencia ---

    def save_config(self, path=None):
        """Guarda toda la configuracion de toolbars y presets."""
        if path is None and self._config_dir:
            path = self._config_dir / "toolbars.json"
        if path is None:
            raise ValueError("No se especifico ruta para guardar")

        data = {
            "version": 1,
            "toolbars": {
                tid: t.to_dict() for tid, t in self.toolbars.items()
            },
            "presets": self.presets,
        }

        Path(path).write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def load_config(self, path=None):
        """Carga configuracion de toolbars y presets."""
        if path is None and self._config_dir:
            path = self._config_dir / "toolbars.json"
        if path is None or not Path(path).exists():
            return False

        data = json.loads(Path(path).read_text(encoding="utf-8"))

        self.toolbars = {}
        for tid, tdata in data.get("toolbars", {}).items():
            self.toolbars[tid] = Toolbar.from_dict(tdata)

        self.presets = data.get("presets", {})
        return True

    # --- Perfiles predefinidos ---

    def create_default_toolbars(self):
        """Crea las toolbars por defecto para un usuario nuevo."""

        # --- Toolbar principal ---
        main = Toolbar("Principal", "main")
        main.add_button(ToolButton(
            id="btn_open", label="Abrir",
            icon="open", color="#6C757D",
            tooltip="Abrir imagen o carpeta",
        ))
        main.add_button(ToolButton(
            id="btn_save", label="Guardar",
            icon="save", color="#6C757D",
            tooltip="Guardar imagen",
        ))
        main.add_button(ToolButton(
            id="btn_undo", label="Deshacer",
            icon="undo", color="#6C757D",
            tooltip="Deshacer ultimo paso", shortcut="Ctrl+Z",
        ))
        main.add_button(ToolButton(
            id="btn_auto", label="Auto",
            icon="auto", color="#28A745",
            tooltip="Ejecutar pipeline automatico completo",
        ))
        self.add_toolbar(main)

        # --- Toolbar de pre-procesamiento ---
        preproc = Toolbar("Pre-procesamiento", "preprocessing")
        preproc.add_button(ToolButton(
            id="btn_calibrate", label="Calibrar",
            action_id="calibrate_light",
            icon="calibrate", color="#17A2B8",
            tooltip="Calibrar con bias/dark/flat",
        ))
        preproc.add_button(ToolButton(
            id="btn_score", label="Scoring",
            action_id="score_frames",
            params={"reject_percent": 20, "min_stars": 5},
            icon="score", color="#17A2B8",
            tooltip="Evaluar calidad de frames",
        ))
        preproc.add_button(ToolButton(
            id="btn_debayer", label="Debayer",
            action_id="debayer",
            params={"pattern": "RGGB"},
            icon="debayer", color="#17A2B8",
            tooltip="Debayer CFA a RGB",
        ))
        preproc.add_button(ToolButton(
            id="btn_align", label="Alinear",
            action_id="align_frames",
            icon="align", color="#17A2B8",
            tooltip="Alinear frames por estrellas",
        ))
        preproc.add_button(ToolButton(
            id="btn_stack", label="Apilar",
            action_id="stack_frames",
            params={"method": "sigma_clip"},
            icon="stack", color="#17A2B8",
            tooltip="Apilar frames",
        ))
        self.add_toolbar(preproc)

        # --- Toolbar de procesamiento ---
        proc = Toolbar("Procesamiento", "processing")
        proc.add_button(ToolButton(
            id="btn_stretch", label="Stretch",
            action_id="stretch_auto",
            icon="stretch", color="#E83E8C",
            tooltip="Stretch automatico",
        ))
        proc.add_button(ToolButton(
            id="btn_abe", label="ABE",
            action_id="background_abe",
            params={"grid_size": 8, "degree": 3},
            icon="background", color="#E83E8C",
            tooltip="Extraccion de fondo automatica",
        ))
        proc.add_button(ToolButton(
            id="btn_denoise", label="Denoise",
            action_id="denoise_selective",
            params={"lum_strength": 0.5, "chrom_strength": 0.3},
            icon="denoise", color="#E83E8C",
            tooltip="Reduccion de ruido selectiva",
        ))
        proc.add_button(ToolButton(
            id="btn_sharpen", label="Sharpen",
            action_id="sharpen_usm",
            params={"radius": 2.0, "amount": 1.0},
            icon="sharpen", color="#E83E8C",
            tooltip="Nitidez (Unsharp Mask)",
        ))
        proc.add_button(ToolButton(
            id="btn_wb", label="WB",
            action_id="wb_auto",
            icon="color", color="#E83E8C",
            tooltip="Balance de blancos automatico",
        ))
        proc.add_button(ToolButton(
            id="btn_sat", label="Color+",
            action_id="saturation",
            params={"factor": 1.3},
            icon="saturation", color="#E83E8C",
            tooltip="Aumentar saturacion",
        ))
        proc.add_button(ToolButton(
            id="btn_levels", label="Niveles",
            action_id="levels",
            icon="levels", color="#E83E8C",
            tooltip="Ajuste de niveles",
        ))
        proc.add_button(ToolButton(
            id="btn_starless", label="Starless",
            action_id="extract_starless",
            icon="stars", color="#E83E8C",
            tooltip="Eliminar estrellas",
        ))
        self.add_toolbar(proc)

        # --- Toolbar de macros (ejemplos) ---
        macros = Toolbar("Macros", "macros")
        macros.add_button(ToolButton(
            id="macro_nebula",
            label="Nebulosa Completo",
            macro=[
                MacroStep("stretch_midtone", {"midtone": 0.18, "black_clip": -3.0}),
                MacroStep("background_abe", {"grid_size": 10, "degree": 3}),
                MacroStep("denoise_selective", {"lum_strength": 0.6, "chrom_strength": 0.3}),
                MacroStep("wb_auto", {"percentile": 95}),
                MacroStep("saturation_selective", {"target_hue": 0, "factor": 1.8, "hue_range": 20}),
                MacroStep("sharpen_usm", {"radius": 2.0, "amount": 0.8}),
            ],
            icon="macro", color="#4ECDC4",
            tooltip="Pipeline completo para nebulosas de emision",
        ))
        macros.add_button(ToolButton(
            id="macro_galaxy",
            label="Galaxia Completo",
            macro=[
                MacroStep("stretch_midtone", {"midtone": 0.28, "black_clip": -2.5}),
                MacroStep("background_abe", {"grid_size": 12, "degree": 4}),
                MacroStep("denoise_selective", {"lum_strength": 0.4, "chrom_strength": 0.2}),
                MacroStep("wb_stars"),
                MacroStep("saturation", {"factor": 1.2}),
                MacroStep("sharpen_deconv", {"psf_sigma": 1.5, "iterations": 10}),
            ],
            icon="macro", color="#4ECDC4",
            tooltip="Pipeline completo para galaxias",
        ))
        macros.add_button(ToolButton(
            id="macro_starfield",
            label="Campo Estelar",
            macro=[
                MacroStep("stretch_asinh", {"a": 0.02, "black_clip": -2.8}),
                MacroStep("wb_stars"),
                MacroStep("saturation", {"factor": 1.5}),
                MacroStep("reduce_halos", {"halo_radius": 3, "strength": 0.5}),
            ],
            icon="macro", color="#4ECDC4",
            tooltip="Pipeline para campos estelares con colores",
        ))
        self.add_toolbar(macros)

        # --- Presets por defecto ---
        self.save_preset(
            "Stretch Nebulosa Ha",
            "stretch_midtone",
            {"midtone": 0.15, "black_clip": -3.0},
            "Stretch agresivo para nebulosas de emision (Ha/SII)",
        )
        self.save_preset(
            "Stretch Galaxia Suave",
            "stretch_midtone",
            {"midtone": 0.30, "black_clip": -2.0},
            "Stretch suave que preserva el nucleo de galaxias",
        )
        self.save_preset(
            "Denoise Agresivo",
            "denoise_selective",
            {"lum_strength": 0.9, "chrom_strength": 0.5, "base_method": "nlm"},
            "Reduccion de ruido fuerte para datos con poco tiempo de exposicion",
        )
        self.save_preset(
            "Denoise Suave",
            "denoise_selective",
            {"lum_strength": 0.3, "chrom_strength": 0.2, "base_method": "nlm"},
            "Reduccion de ruido ligera para datos limpios",
        )
        self.save_preset(
            "Saturar Rojos (Ha)",
            "saturation_selective",
            {"target_hue": 0, "hue_range": 20, "factor": 2.0},
            "Potenciar la senal de hidrogeno alfa (rojo)",
        )
        self.save_preset(
            "Saturar Azules (OIII)",
            "saturation_selective",
            {"target_hue": 110, "hue_range": 25, "factor": 1.8},
            "Potenciar la senal de oxigeno III (azul-verde)",
        )


def print_toolbar_summary(manager):
    """Imprime un resumen de todas las toolbars y presets."""
    print("\n  TOOLBARS CONFIGURADAS")
    print("  " + "=" * 50)

    for toolbar in manager.get_all_toolbars():
        vis = "" if toolbar.visible else " [oculta]"
        print(f"\n  [{toolbar.name}]{vis} ({toolbar.position})")
        for btn in toolbar.buttons:
            if btn.is_macro:
                steps = len([s for s in btn.macro if s.enabled])
                print(f"    [{btn.label}] macro ({steps} pasos) {btn.color}")
            elif btn.action_id:
                params_str = ""
                if btn.params:
                    params_str = " " + str(btn.params)
                print(f"    [{btn.label}] -> {btn.action_id}{params_str}")
            else:
                print(f"    [{btn.label}] (sin accion)")
            if btn.tooltip:
                print(f"       {btn.tooltip}")

    presets = manager.list_presets()
    if presets:
        print(f"\n  PRESETS ({len(presets)})")
        print("  " + "-" * 50)
        for p in presets:
            print(f"    {p['name']}: {p['action_id']} {p['params']}")
            if p.get("description"):
                print(f"       {p['description']}")
