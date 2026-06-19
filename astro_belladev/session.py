"""
session.py
----------
Sesión de procesamiento paso a paso con historial y undo.

En la GUI futura, el usuario puede:
- Ejecutar un paso, ver el resultado, ajustar y re-ejecutar.
- Deshacer el último paso (Ctrl+Z) y volver al estado anterior.
- Ver el historial completo de operaciones aplicadas.
- Guardar/cargar la sesión para continuar después.

La sesión mantiene una pila de estados (snapshots) para cada paso,
de forma que el undo es simplemente volver al estado anterior sin
recalcular nada.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime
import json
from pathlib import Path

from .progress import ProgressCallback, ConsoleProgress


@dataclass
class StepRecord:
    """Registro de un paso ejecutado."""
    step_number: int
    action_id: str
    action_name: str
    params: dict
    timestamp: str = ""
    elapsed_seconds: float = 0.0
    input_shape: tuple = ()
    output_shape: tuple = ()
    notes: str = ""

    def to_dict(self):
        return {
            "step": self.step_number,
            "action": self.action_id,
            "name": self.action_name,
            "params": self.params,
            "timestamp": self.timestamp,
            "elapsed": self.elapsed_seconds,
            "input_shape": list(self.input_shape),
            "output_shape": list(self.output_shape),
            "notes": self.notes,
        }


class Session:
    """
    Sesión de procesamiento con historial y undo.

    Cada operación se ejecuta sobre el estado actual (self.current_data)
    y se guarda un snapshot del estado anterior para poder deshacer.
    """

    def __init__(self, progress=None, max_undo=10):
        self.progress = progress or ConsoleProgress()
        self._max_undo = max_undo
        self.current_data = None
        self._undo_stack = []
        self._history = []
        self._step_counter = 0
        self.metadata = {}

    def load_image(self, data, source_info=""):
        """Carga una imagen como punto de partida de la sesión."""
        self.current_data = data.copy()
        self.metadata["source"] = source_info
        self.metadata["original_shape"] = data.shape
        self.metadata["original_dtype"] = str(data.dtype)
        self.progress.log(f"Imagen cargada: {data.shape}, {data.dtype}")

    def apply(self, action, **kwargs):
        """
        Aplica una acción sobre la imagen actual.

        Parámetros
        ----------
        action : Action
            La acción del registro a ejecutar.
        **kwargs : dict
            Parámetros para la acción (sobreescriben los defaults).
        """
        import time

        if self.current_data is None:
            raise RuntimeError("No hay imagen cargada. Usa session.load_image() primero.")

        self._push_undo()

        self._step_counter += 1
        self.progress.start_step(
            action.name,
            step_number=self._step_counter,
        )

        start = time.time()
        input_shape = self.current_data.shape

        try:
            self.current_data = action.execute(self.current_data, **kwargs)
        except Exception as e:
            self._pop_undo()
            self._step_counter -= 1
            self.progress.error(f"{action.name} falló: {e}")
            raise

        elapsed = time.time() - start
        output_shape = self.current_data.shape

        record = StepRecord(
            step_number=self._step_counter,
            action_id=action.id,
            action_name=action.name,
            params=kwargs or action.get_defaults(),
            timestamp=datetime.now().isoformat(),
            elapsed_seconds=round(elapsed, 2),
            input_shape=input_shape,
            output_shape=output_shape,
        )
        self._history.append(record)

        self.progress.end_step(
            f"{input_shape} → {output_shape}"
        )

        return self.current_data

    def undo(self):
        """Deshace el último paso y vuelve al estado anterior."""
        if not self._undo_stack:
            self.progress.warning("No hay pasos para deshacer.")
            return None

        self.current_data = self._undo_stack.pop()
        self._step_counter -= 1

        if self._history:
            undone = self._history.pop()
            self.progress.log(f"Deshecho: {undone.action_name}")

        return self.current_data

    def undo_count(self):
        return len(self._undo_stack)

    def _push_undo(self):
        if self.current_data is not None:
            self._undo_stack.append(self.current_data.copy())
            if len(self._undo_stack) > self._max_undo:
                self._undo_stack.pop(0)

    def _pop_undo(self):
        if self._undo_stack:
            self.current_data = self._undo_stack.pop()

    def get_history(self):
        return list(self._history)

    def print_history(self):
        """Imprime el historial de operaciones."""
        if not self._history:
            print("  (sin operaciones)")
            return

        print(f"\n  Historial ({len(self._history)} pasos):")
        print(f"  {'#':>3} {'Operación':<30} {'Tiempo':>8} {'Shape'}")
        print(f"  {'-'*65}")

        for record in self._history:
            print(
                f"  {record.step_number:>3} {record.action_name:<30} "
                f"{record.elapsed_seconds:>6.2f}s "
                f"{record.input_shape} → {record.output_shape}"
            )

    def save_history(self, path):
        """Guarda el historial como JSON para poder reproducirlo."""
        data = {
            "metadata": {
                k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                for k, v in self.metadata.items()
            },
            "steps": [r.to_dict() for r in self._history],
        }
        Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def get_state_summary(self):
        """Resumen del estado actual para mostrar en la GUI."""
        if self.current_data is None:
            return {"loaded": False}

        return {
            "loaded": True,
            "shape": self.current_data.shape,
            "dtype": str(self.current_data.dtype),
            "min": float(np.min(self.current_data)),
            "max": float(np.max(self.current_data)),
            "mean": float(np.mean(self.current_data)),
            "steps_applied": len(self._history),
            "undo_available": len(self._undo_stack),
        }
