"""
progress.py
-----------
Sistema de callbacks para reportar progreso de las operaciones.

En modo consola: imprime mensajes y barra de progreso textual.
En modo GUI (futuro): alimentará barras de progreso, logs y
notificaciones de la interfaz PyQt6.

Uso:
    progress = ConsoleProgress()
    progress.start_step("Calibrando", total=8)
    for i in range(8):
        progress.update(i + 1, f"Frame {i+1}/8")
    progress.end_step("8 frames calibrados")
"""

import time


class ProgressCallback:
    """Interfaz base para callbacks de progreso."""

    def start_pipeline(self, mode, total_steps):
        pass

    def end_pipeline(self, success, message=""):
        pass

    def start_step(self, step_name, step_number=0, total=0):
        pass

    def update(self, current, total=0, message=""):
        pass

    def end_step(self, message=""):
        pass

    def warning(self, message):
        pass

    def error(self, message):
        pass

    def log(self, message):
        pass


class ConsoleProgress(ProgressCallback):
    """Progreso por consola con barra textual."""

    def __init__(self, bar_width=30):
        self._bar_width = bar_width
        self._step_start = 0

    def start_pipeline(self, mode, total_steps):
        print("=" * 55)
        label = "Modo Automático" if mode == "auto" else "Modo Experto"
        print(f"  ASTRO SUITE — {label}")
        print(f"  {total_steps} pasos en el pipeline")
        print("=" * 55)

    def end_pipeline(self, success, message=""):
        if success:
            print(f"\n{'=' * 55}")
            print(f"  COMPLETADO: {message}")
            print(f"{'=' * 55}")
        else:
            print(f"\n  ERROR: {message}")

    def start_step(self, step_name, step_number=0, total=0):
        self._step_start = time.time()
        header = f"[{step_number}/{total}]" if total > 0 else ">>>"
        print(f"\n{header} {step_name}...")

    def update(self, current, total=0, message=""):
        if total > 0:
            pct = current / total
            filled = int(self._bar_width * pct)
            bar = "#" * filled + "-" * (self._bar_width - filled)
            print(f"\r  [{bar}] {current}/{total} {message}", end="", flush=True)
        elif message:
            print(f"  {message}")

    def end_step(self, message=""):
        elapsed = time.time() - self._step_start
        if message:
            print(f"\n  OK: {message} ({elapsed:.1f}s)")
        else:
            print(f"\n  OK: Completado ({elapsed:.1f}s)")

    def warning(self, message):
        print(f"  AVISO: {message}")

    def error(self, message):
        print(f"  ERROR: {message}")

    def log(self, message):
        print(f"  {message}")


class SilentProgress(ProgressCallback):
    """No imprime nada. Para tests y uso programático."""
    pass


class MultiProgress(ProgressCallback):
    """Reenvía eventos a múltiples callbacks."""

    def __init__(self, *callbacks):
        self._callbacks = list(callbacks)

    def add(self, callback):
        self._callbacks.append(callback)

    def start_pipeline(self, mode, total_steps):
        for cb in self._callbacks:
            cb.start_pipeline(mode, total_steps)

    def end_pipeline(self, success, message=""):
        for cb in self._callbacks:
            cb.end_pipeline(success, message)

    def start_step(self, step_name, step_number=0, total=0):
        for cb in self._callbacks:
            cb.start_step(step_name, step_number, total)

    def update(self, current, total=0, message=""):
        for cb in self._callbacks:
            cb.update(current, total, message)

    def end_step(self, message=""):
        for cb in self._callbacks:
            cb.end_step(message)

    def warning(self, message):
        for cb in self._callbacks:
            cb.warning(message)

    def error(self, message):
        for cb in self._callbacks:
            cb.error(message)

    def log(self, message):
        for cb in self._callbacks:
            cb.log(message)
