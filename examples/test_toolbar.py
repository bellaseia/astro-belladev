"""
test_toolbar.py
---------------
Valida el sistema de toolbars personalizables, presets y macros.
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

    for _ in range(20):
        y, x = rng.randint(15, h-15), rng.randint(15, w-15)
        peak = rng.uniform(3000, 10000)
        yy, xx = np.mgrid[-8:9, -8:9]
        star = peak * np.exp(-(yy**2 + xx**2) / 12.5)
        y0, x0 = max(0, y-8), max(0, x-8)
        y1, x1 = min(h, y+9), min(w, x+9)
        sy, sx = y0-(y-8), x0-(x-8)
        for c in range(3):
            img[y0:y1, x0:x1, c] += star[sy:sy+(y1-y0), sx:sx+(x1-x0)]

    return np.clip(img, 0, None)


def test_toolbar_creation():
    print("=== Test Creacion de Toolbars ===\n")
    from astro_belladev.toolbar import Toolbar, ToolButton, MacroStep

    toolbar = Toolbar("Mi Toolbar", "test_bar")

    toolbar.add_button(ToolButton(
        id="btn1", label="Stretch",
        action_id="stretch_midtone",
        params={"midtone": 0.20},
        color="#FF6B6B",
    ))
    toolbar.add_button(ToolButton(
        id="btn2", label="Denoise",
        action_id="denoise_selective",
        params={"lum_strength": 0.5},
    ))
    toolbar.add_button(ToolButton(
        id="btn3", label="Macro Test",
        macro=[
            MacroStep("stretch_midtone", {"midtone": 0.25}),
            MacroStep("wb_auto", {"percentile": 95}),
            MacroStep("saturation", {"factor": 1.3}),
        ],
        color="#4ECDC4",
    ))

    assert len(toolbar.buttons) == 3
    assert toolbar.buttons[0].label == "Stretch"
    assert toolbar.buttons[2].is_macro
    assert len(toolbar.buttons[2].macro) == 3
    print(f"  Toolbar '{toolbar.name}': {len(toolbar.buttons)} botones")

    toolbar.move_button("btn2", 0)
    assert toolbar.buttons[0].id == "btn2"
    assert toolbar.buttons[1].id == "btn1"
    print(f"  Mover boton: btn2 ahora en posicion 0")

    toolbar.remove_button("btn2")
    assert len(toolbar.buttons) == 2
    print(f"  Eliminar boton: quedan {len(toolbar.buttons)}")

    print("  -> Creacion de toolbars: OK\n")


def test_toolbar_execution():
    print("=== Test Ejecucion de Botones ===\n")
    from astro_belladev.toolbar import Toolbar, ToolButton, MacroStep
    from astro_belladev.actions import build_default_registry
    from astro_belladev.session import Session
    from astro_belladev.progress import SilentProgress

    registry = build_default_registry()
    session = Session(progress=SilentProgress())
    img = _make_test_image()
    session.load_image(img)

    toolbar = Toolbar("Test")
    toolbar.add_button(ToolButton(
        id="btn_stretch", label="Stretch",
        action_id="stretch_midtone",
        params={"midtone": 0.25, "black_clip": -2.8},
    ))

    toolbar.execute_button("btn_stretch", session, registry)
    assert session.current_data.max() <= 1.0
    print(f"  Boton simple: stretch aplicado (max={session.current_data.max():.3f})")

    session.undo()

    toolbar.add_button(ToolButton(
        id="btn_macro", label="Macro",
        macro=[
            MacroStep("stretch_midtone", {"midtone": 0.25}),
            MacroStep("saturation", {"factor": 1.3}),
        ],
    ))

    initial_undo = session.undo_count()
    toolbar.execute_button("btn_macro", session, registry)
    assert session.undo_count() == initial_undo + 2
    print(f"  Macro (2 pasos): ejecutada, undo={session.undo_count()}")

    session.undo()
    session.undo()
    print(f"  2x undo tras macro: OK")

    print("  -> Ejecucion de botones: OK\n")


def test_presets():
    print("=== Test Presets ===\n")
    from astro_belladev.toolbar import ToolbarManager

    manager = ToolbarManager()

    manager.save_preset(
        "Mi Stretch",
        "stretch_midtone",
        {"midtone": 0.18, "black_clip": -3.0},
        "Stretch personalizado para M42",
    )

    preset = manager.get_preset("Mi Stretch")
    assert preset is not None
    assert preset["action_id"] == "stretch_midtone"
    assert preset["params"]["midtone"] == 0.18
    print(f"  Preset guardado: '{preset['name']}'")

    button = manager.create_button_from_preset("Mi Stretch", color="#FF0000")
    assert button.action_id == "stretch_midtone"
    assert button.params["midtone"] == 0.18
    print(f"  Boton desde preset: '{button.label}'")

    presets = manager.list_presets()
    assert len(presets) == 1
    print(f"  Lista: {len(presets)} preset(s)")

    manager.delete_preset("Mi Stretch")
    assert manager.get_preset("Mi Stretch") is None
    print(f"  Preset eliminado")

    print("  -> Presets: OK\n")


def test_persistence():
    print("=== Test Persistencia ===\n")
    from astro_belladev.toolbar import ToolbarManager, Toolbar, ToolButton

    config_path = os.path.join(os.path.dirname(__file__), "_test_toolbars.json")
    manager = ToolbarManager()

    toolbar = Toolbar("Test Save", "test_save")
    toolbar.add_button(ToolButton(
        id="btn1", label="Boton 1",
        action_id="stretch_auto",
        color="#FF0000",
    ))
    manager.add_toolbar(toolbar)
    manager.save_preset("Test Preset", "denoise_nlm", {"h": 15.0})

    manager.save_config(config_path)
    assert os.path.exists(config_path)
    print(f"  Config guardada en {config_path}")

    manager2 = ToolbarManager()
    loaded = manager2.load_config(config_path)
    assert loaded

    loaded_toolbar = manager2.get_toolbar("test_save")
    assert loaded_toolbar is not None
    assert len(loaded_toolbar.buttons) == 1
    assert loaded_toolbar.buttons[0].color == "#FF0000"
    print(f"  Config cargada: toolbar '{loaded_toolbar.name}' con {len(loaded_toolbar.buttons)} boton(es)")

    loaded_preset = manager2.get_preset("Test Preset")
    assert loaded_preset is not None
    assert loaded_preset["params"]["h"] == 15.0
    print(f"  Preset cargado: '{loaded_preset['name']}'")

    os.remove(config_path)
    print("  -> Persistencia: OK\n")


def test_default_toolbars():
    print("=== Test Toolbars por Defecto ===\n")
    from astro_belladev.toolbar import ToolbarManager, print_toolbar_summary

    manager = ToolbarManager()
    manager.create_default_toolbars()

    toolbars = manager.get_all_toolbars()
    total_buttons = sum(len(t.buttons) for t in toolbars)
    presets = manager.list_presets()

    print(f"  Toolbars: {len(toolbars)}")
    print(f"  Botones totales: {total_buttons}")
    print(f"  Presets: {len(presets)}")

    assert len(toolbars) == 4
    assert total_buttons >= 15
    assert len(presets) >= 6

    print_toolbar_summary(manager)

    macros_bar = manager.get_toolbar("macros")
    assert macros_bar is not None
    macro_btn = macros_bar.get_button("macro_nebula")
    assert macro_btn is not None
    assert macro_btn.is_macro
    assert len(macro_btn.macro) >= 5
    print(f"\n  Macro 'Nebulosa Completo': {len(macro_btn.macro)} pasos")

    print("  -> Toolbars por defecto: OK\n")


def test_macro_execution_full():
    print("=== Test Macro Completa con Sesion ===\n")
    from astro_belladev.toolbar import ToolbarManager
    from astro_belladev.actions import build_default_registry
    from astro_belladev.session import Session
    from astro_belladev.progress import SilentProgress

    registry = build_default_registry()
    session = Session(progress=SilentProgress())
    img = _make_test_image()
    session.load_image(img)

    manager = ToolbarManager()
    manager.create_default_toolbars()

    macros_bar = manager.get_toolbar("macros")
    macros_bar.execute_button("macro_starfield", session, registry)

    history = session.get_history()
    print(f"  Macro 'Campo Estelar' ejecutada: {len(history)} pasos en historial")
    for h in history:
        print(f"    {h.step_number}. {h.action_name} ({h.elapsed_seconds:.2f}s)")

    assert len(history) >= 3
    assert session.current_data is not None
    assert session.current_data.max() <= 1.5

    while session.undo_count() > 0:
        session.undo()

    assert np.allclose(session.current_data, img, atol=0.01)
    print(f"  Full undo tras macro: vuelto al original")

    print("  -> Macro completa: OK\n")


if __name__ == "__main__":
    test_toolbar_creation()
    test_toolbar_execution()
    test_presets()
    test_persistence()
    test_default_toolbars()
    test_macro_execution_full()
    print("=" * 55)
    print("  TODOS LOS TESTS PASARON CORRECTAMENTE")
    print("=" * 55)
