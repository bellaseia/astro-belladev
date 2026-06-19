"""
app.py — Punto de entrada de Astro BellaDev.
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from astro_belladev.gui.theme import build_stylesheet
from astro_belladev.gui.splash import create_splash


def _cleanup_temp():
    """Limpia temporales huerfanos de sesiones anteriores."""
    import tempfile
    import shutil
    from pathlib import Path
    temp = Path(tempfile.gettempdir())
    for d in temp.glob("astro_belladev_*"):
        if d.is_dir():
            try:
                shutil.rmtree(str(d), ignore_errors=True)
            except Exception:
                pass


def main():
    _cleanup_temp()
    app = QApplication(sys.argv)
    app.setApplicationName("Astro BellaDev")
    app.setApplicationVersion("1.1.0")
    app.setStyle("Fusion")
    app.setStyleSheet(build_stylesheet("dark"))

    splash = create_splash()
    splash.show()
    app.processEvents()

    # Icono de la app (taskbar + ventana)
    from pathlib import Path
    from PyQt6.QtGui import QIcon
    icon_path = Path(__file__).parent / "astro_belladev.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    else:
        icon_png = Path(__file__).parent / "astro_belladev.png"
        if icon_png.exists():
            app.setWindowIcon(QIcon(str(icon_png)))

    from astro_belladev.gui.main_window import MainWindow
    window = MainWindow()

    def finish_splash():
        splash.finish(window)
        window.show()

    QTimer.singleShot(1800, finish_splash)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
