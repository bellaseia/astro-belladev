"""
main_window.py
--------------
Ventana principal de Astro BellaDev.
Idioma y tema en menu Vista, toolbar cromatica, panel de params
con sliders, click en toolbar abre params antes de aplicar.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QToolBar, QLabel, QPushButton,
    QFileDialog, QMessageBox, QProgressBar,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QActionGroup, QKeySequence

from ..actions import build_default_registry
from ..session import Session
from ..progress import ProgressCallback
from ..toolbar import ToolbarManager
from .image_viewer import ImageViewer
from .params_panel import ParamsPanel
from .steps_panel import StepsPanel
from .histogram_widget import HistogramWidget
from .icons import get_icon
from .theme import build_stylesheet, get_theme
from .i18n import tr, set_language, available_languages, get_language
from .process_icons import ProcessIconsBar
from .assistant_panel import AssistantPanel
from .equipment_dialog import EquipmentDialog
from .planner_dialog import PlannerDialog
from .about_dialog import AboutDialog
from .wizard_panel import WizardPanel
from .scripts_dialog import ScriptsDialog
from .preprocess_dialog import PreprocessDialog
from .multi_input_dialog import HDRDialog, PixelMathDialog, NarrowbandDialog
from .log_panel import LogPanel


GROUP_COLORS = {
    "file": "#7E8FA6",
    "preprocess": "#4A9BD9",
    "process": "#4CAF6E",
    "ai": "#E6A817",
    "tools": "#AB7BD6",
    "macro": "#E07B4C",
}


class GuiProgress(ProgressCallback):
    def __init__(self, progress_bar, status_label):
        self._bar = progress_bar
        self._label = status_label

    def start_pipeline(self, mode, total_steps):
        self._bar.setMaximum(total_steps)
        self._bar.setValue(0)

    def end_pipeline(self, success, message=""):
        self._bar.setValue(self._bar.maximum())
        self._label.setText(message or tr("Completado"))

    def start_step(self, step_name, step_number=0, total=0):
        if total > 0:
            self._bar.setMaximum(total)
            self._bar.setValue(step_number)
        self._label.setText(step_name)

    def update(self, current, total=0, message=""):
        if total > 0:
            self._bar.setMaximum(total)
            self._bar.setValue(current)

    def end_step(self, message=""):
        if message:
            self._label.setText(message)

    def warning(self, message):
        self._label.setText(f"{tr('Aviso')}: {message}")

    def error(self, message):
        self._label.setText(f"{tr('Error')}: {message}")

    def log(self, message):
        self._label.setText(message)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Astro BellaDev")
        self.setMinimumSize(1280, 820)
        self.resize(1440, 900)

        self.registry = build_default_registry()
        self.session = Session()
        self.toolbar_manager = ToolbarManager()
        self.toolbar_manager.create_default_toolbars()
        self.expert_mode = False
        self.current_theme = "dark"

        self._apply_theme(self.current_theme)
        self._setup_ui()
        self._setup_menus()
        self._setup_toolbar()
        self._setup_shortcuts()

        # Aplicar modo auto DESPUES de crear toolbars
        self._set_mode(False)

        self.session.progress = GuiProgress(
            self.progress_bar, self.status_label
        )

    def _apply_theme(self, theme_name):
        self.current_theme = theme_name
        self.setStyleSheet(build_stylesheet(theme_name))
        # Reconstruir toolbars con colores del nuevo tema
        if hasattr(self, '_toolbars'):
            for tb in self.findChildren(QToolBar):
                self.removeToolBar(tb)
                tb.deleteLater()
            self._setup_toolbar()
            self._set_mode(self.expert_mode)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        t = get_theme(self.current_theme)

        # === HEADER ===
        header = QWidget()
        header.setFixedHeight(42)
        header.setObjectName("appHeader")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 0, 16, 0)

        logo = QLabel("ASTRO BELLADEV")
        logo.setObjectName("appLogo")
        h_layout.addWidget(logo)

        ver = QLabel("v1.1.0")
        ver.setObjectName("subtitle")
        h_layout.addWidget(ver)
        h_layout.addStretch()

        # Toggle AUTO | EXPERTO
        self.mode_auto_btn = QPushButton(tr("AUTO"))
        self.mode_expert_btn = QPushButton(tr("EXPERTO"))
        for btn in [self.mode_auto_btn, self.mode_expert_btn]:
            btn.setFixedSize(90, 30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.mode_auto_btn.clicked.connect(lambda: self._set_mode(False))
        self.mode_expert_btn.clicked.connect(lambda: self._set_mode(True))

        mode_c = QWidget()
        mode_c.setFixedSize(182, 32)
        mode_l = QHBoxLayout(mode_c)
        mode_l.setContentsMargins(0, 0, 0, 0)
        mode_l.setSpacing(1)
        mode_l.addWidget(self.mode_auto_btn)
        mode_l.addWidget(self.mode_expert_btn)
        h_layout.addWidget(mode_c)

        main_layout.addWidget(header)

        # === CONTENT ===
        content = QSplitter(Qt.Orientation.Horizontal)
        content.setHandleWidth(1)

        # Panel izquierdo: wizard (auto) o steps (experto)
        self.wizard_panel = WizardPanel(self)
        self.steps_panel = StepsPanel(self)
        self.steps_panel.setVisible(False)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        left_layout.addWidget(self.wizard_panel)
        left_layout.addWidget(self.steps_panel)
        content.addWidget(left_container)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        # Visor de imagen unico
        self.image_viewer = ImageViewer(self)
        self._active_viewer = self.image_viewer
        center_layout.addWidget(self.image_viewer, stretch=6)

        # Histograma + Log en tabs
        from PyQt6.QtWidgets import QTabWidget as QTW
        bottom_tabs = QTW()
        bottom_tabs.setMaximumHeight(200)

        self.histogram = HistogramWidget(self)
        bottom_tabs.addTab(
            self.histogram, get_icon("histogram", 16), "Histograma"
        )

        self.log_panel = LogPanel(self)
        bottom_tabs.addTab(
            self.log_panel, get_icon("macro", 16), "Consola"
        )

        center_layout.addWidget(bottom_tabs, stretch=2)
        content.addWidget(center)

        # Panel derecho: tabs Params + Asistente
        from PyQt6.QtWidgets import QTabWidget
        right_tabs = QTabWidget()
        right_tabs.setFixedWidth(290)

        self.params_panel = ParamsPanel(self.registry, self)
        right_tabs.addTab(self.params_panel, get_icon("levels", 16), tr("Parametros"))

        self.assistant_panel = AssistantPanel(self)
        right_tabs.addTab(self.assistant_panel, get_icon("assistant", 16), tr("Asistente"))

        content.addWidget(right_tabs)

        content.setSizes([200, 800, 290])
        main_layout.addWidget(content, stretch=1)

        # === PROCESS ICONS BAR ===
        self.process_icons = ProcessIconsBar(self.registry, self)
        main_layout.addWidget(self.process_icons)

        # === FOOTER ===
        footer = QWidget()
        footer.setFixedHeight(28)
        footer.setObjectName("appFooter")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(16, 0, 16, 0)

        self.mode_indicator = QLabel("")
        self._update_mode_indicator()
        f_layout.addWidget(self.mode_indicator)
        f_layout.addStretch()

        self.status_label = QLabel(tr("Listo"))
        self.status_label.setObjectName("subtitle")
        f_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(180)
        self.progress_bar.setTextVisible(False)
        f_layout.addWidget(self.progress_bar)
        f_layout.addStretch()

        self.image_info_label = QLabel("")
        self.image_info_label.setObjectName("subtitle")
        f_layout.addWidget(self.image_info_label)

        f_layout.addStretch()

        # Indicador de sistema (RAM, disco, nucleos)
        self.sys_info_label = QLabel("")
        self.sys_info_label.setStyleSheet(
            "font-size: 11px; color: #6A7A8A;"
        )
        f_layout.addWidget(self.sys_info_label)
        self._update_sys_info()

        from PyQt6.QtCore import QTimer
        self._sys_timer = QTimer()
        self._sys_timer.timeout.connect(self._update_sys_info)
        self._sys_timer.start(2000)

        main_layout.addWidget(footer)

    def _setup_menus(self):
        menubar = self.menuBar()

        menu_tree = {}
        for action in self.registry.get_all():
            parts = action.menu_path.split(" > ")
            node = menu_tree
            for part in parts[:-1]:
                if part not in node:
                    node[part] = {}
                elif not isinstance(node[part], dict):
                    existing = node[part]
                    node[part] = {"_action": existing}
                node = node[part]
            node[parts[-1]] = action

        menu_order = [
            "Archivo", "Pre-procesamiento", "Procesamiento",
            "AI", "Herramientas", "Asistente", "Planificador",
            "Vista",
        ]
        for top_name in menu_order:
            if top_name in menu_tree:
                menu = menubar.addMenu(tr(top_name))
                self._build_menu(menu, menu_tree[top_name])

        # --- Cerrar imagen en Archivo ---
        for act in menubar.actions():
            if tr("Archivo") in act.text():
                archivo_menu = act.menu()
                archivo_menu.addSeparator()
                close_act = QAction("Cerrar imagen", self)
                close_act.setShortcut(QKeySequence("Ctrl+W"))
                close_act.triggered.connect(self._close_image)
                archivo_menu.addAction(close_act)
                break

        # --- Acceso directo al pipeline en Pre-procesamiento ---
        for act in menubar.actions():
            if tr("Pre-procesamiento") in act.text():
                preproc_menu = act.menu()
                preproc_menu.insertSeparator(
                    preproc_menu.actions()[0]
                )
                pipeline_act = QAction(
                    get_icon("stack", 16),
                    "Pipeline completo (carpetas)...", self,
                )
                pipeline_act.triggered.connect(self._show_preprocess)
                preproc_menu.insertAction(
                    preproc_menu.actions()[0], pipeline_act
                )
                break

        # --- Menu Vista: idioma + tema ---
        vista_menu = menubar.actions()[-1].menu()
        vista_menu.addSeparator()

        # Tema
        theme_menu = vista_menu.addMenu(get_icon("theme", 16), tr("Tema"))
        theme_group = QActionGroup(self)
        for tname, tlabel in [("dark", tr("Oscuro")), ("light", tr("Claro"))]:
            act = QAction(tlabel, self)
            act.setCheckable(True)
            act.setChecked(tname == self.current_theme)
            tid = tname
            act.triggered.connect(
                lambda checked, t=tid: self._apply_theme(t)
            )
            theme_group.addAction(act)
            theme_menu.addAction(act)

        # Idioma
        lang_menu = vista_menu.addMenu(tr("Idioma / Language"))
        lang_group = QActionGroup(self)
        for code, name in available_languages().items():
            act = QAction(name, self)
            act.setCheckable(True)
            act.setChecked(code == get_language())
            lcode = code
            act.triggered.connect(
                lambda checked, c=lcode: self._change_language(c)
            )
            lang_group.addAction(act)
            lang_menu.addAction(act)

        # --- Conectar Planificador a dialogos reales ---
        for act in menubar.actions():
            if tr("Planificador") in act.text():
                planner_menu = act.menu()
                if planner_menu:
                    for a in planner_menu.actions():
                        if "arget" in a.text():
                            a.triggered.disconnect()
                            a.triggered.connect(
                                self._show_planner
                            )
                        elif "equipo" in a.text().lower() or \
                             "quipment" in a.text().lower():
                            a.triggered.disconnect()
                            a.triggered.connect(
                                self._show_equipment_dialog
                            )
                break

        # --- Menu Scripts ---
        scripts_menu = menubar.addMenu("Scripts")
        manage_scripts = QAction(
            get_icon("macro", 16), "Gestionar scripts...", self
        )
        manage_scripts.triggered.connect(self._show_scripts)
        scripts_menu.addAction(manage_scripts)
        scripts_menu.addSeparator()

        # Scripts predefinidos como accesos directos
        from ..scripts import ScriptManager
        sm = ScriptManager()
        sm.create_builtin_scripts()
        sm.scan()
        for script in sm.get_all():
            act = QAction(script.name, self)
            act.setStatusTip(script.description)
            sname = script.filename.replace(".abs", "")
            act.triggered.connect(
                lambda ch, n=sname: self._run_script(n)
            )
            scripts_menu.addAction(act)

        # --- About ---
        help_menu = menubar.addMenu("?")
        about_act = QAction("About Astro BellaDev", self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

    def _build_menu(self, parent_menu, tree):
        icon_map = {
            "stretch": "stretch", "background": "background",
            "stretch": "stretch", "background": "background",
            "denoise": "denoise", "sharpen": "sharpen",
            "wb": "color", "saturation": "color",
            "photometric": "color",
            "levels": "levels", "curves": "levels",
            "histogram": "histogram",
            "star": "stars", "crop": "crop",
            "rotate": "rotate", "flip": "rotate",
            "resize": "rotate", "binning": "stack",
            "export": "export", "save": "save",
            "social": "export", "watermark": "export",
            "ai_": "ai", "nb_": "narrowband",
            "scnr": "color", "lrgb": "color",
            "clahe": "levels", "local_contrast": "levels",
            "heal": "heal", "remove": "heal",
            "auto_detect": "heal",
            "spike": "spikes", "diffraction": "spikes",
            "reduction": "stars",
            "plate": "catalog", "catalog": "catalog",
            "search": "catalog", "annotate": "catalog",
            "planner": "planner", "session": "planner",
            "assistant": "assistant",
            "batch": "macro", "timelapse": "macro",
            "comparison": "mosaic", "mosaic": "mosaic",
            "hdr": "stretch",
            "drizzle": "stack",
            "pixelmath": "levels",
            "image_stats": "histogram",
        }
        for name, value in tree.items():
            if name == "_action":
                continue
            if hasattr(value, 'id'):
                q = QAction(value.name, self)
                q.setStatusTip(value.description)
                matched = False
                for prefix, iname in icon_map.items():
                    if prefix in value.id:
                        q.setIcon(get_icon(iname, 16))
                        matched = True
                        break
                if not matched:
                    q.setIcon(get_icon("auto", 16))
                aid = value.id
                q.triggered.connect(
                    lambda ch, a=aid: self._show_action_params(a)
                )
                parent_menu.addAction(q)
            elif isinstance(value, dict):
                sub = parent_menu.addMenu(tr(name))
                self._build_menu(sub, value)

    def _setup_toolbar(self):
        t = get_theme(self.current_theme)
        self._toolbars = {}

        def _make_toolbar(key, name, items, color):
            """Crea un toolbar con color de grupo."""
            tb = QToolBar(name)
            tb.setMovable(True)
            tb.setIconSize(QSize(22, 22))
            tb.setToolButtonStyle(
                Qt.ToolButtonStyle.ToolButtonTextUnderIcon
            )
            tb.setStyleSheet(f"""
                QToolBar {{
                    background-color: {t['toolbar_bg']};
                    border-bottom: 1px solid {t['border']};
                    border-top: 2px solid {color};
                    spacing: 2px; padding: 3px 4px;
                }}
                QToolBar QToolButton {{
                    background-color: {t['surface']};
                    color: {t['text_primary']};
                    border: 1px solid {t['border']};
                    border-radius: 5px;
                    padding: 4px 8px; margin: 1px;
                    font-size: 13px; font-weight: 500;
                }}
                QToolBar QToolButton:hover {{
                    background-color: {color};
                    color: white;
                    border-color: {color};
                }}
                QToolBar QToolButton:pressed {{
                    background-color: {t['surface_active']};
                }}
                QToolBar QToolButton:checked {{
                    background-color: {color};
                    color: white;
                    border-color: {color};
                    border-bottom: 3px solid white;
                }}
            """)

            for item in items:
                if item is None:
                    tb.addSeparator()
                    continue
                icon, label, tip, handler, aid = item
                q = QAction(get_icon(icon, 22), tr(label), self)
                q.setToolTip(tr(tip))
                q.setCheckable(aid is not None)
                if aid:
                    q.setData(aid)
                if handler:
                    q.triggered.connect(handler)
                elif aid:
                    q.triggered.connect(
                        lambda ch, a=aid: self._select_action(a)
                    )
                tb.addAction(q)

            self.addToolBar(tb)
            self._toolbars[key] = tb

        fc = GROUP_COLORS["file"]
        pc = GROUP_COLORS["preprocess"]
        gc = GROUP_COLORS["process"]
        ac = GROUP_COLORS["ai"]

        _make_toolbar("file", "Archivo", [
            ("open", "Abrir", "Abrir imagen (Ctrl+O)", self._open_file, None),
            ("save", "Guardar", "Guardar (Ctrl+S)", self._save_file, None),
            ("undo", "Deshacer", "Deshacer (Ctrl+Z)", self._undo, None),
            None,
            ("auto", "Auto", "Pipeline automatico", self._run_auto, None),
        ], fc)

        _make_toolbar("preprocess", "Pre-procesamiento", [
            ("calibrate", "Calibrar", "Calibrar lights", None, "calibrate_light"),
            ("score", "Scoring", "Evaluar calidad", None, "score_frames"),
            ("debayer", "Debayer", "CFA a RGB", None, "debayer"),
            ("align", "Alinear", "Registro estrellas", None, "align_frames"),
            ("stack", "Apilar", "Stacking", None, "stack_frames"),
        ], pc)

        _make_toolbar("process", "Procesamiento", [
            ("stretch", "Stretch", "Estiramiento", None, "stretch_auto"),
            ("background", "ABE", "Fondo", None, "background_abe"),
            ("denoise", "Denoise", "Ruido", None, "denoise_selective"),
            ("sharpen", "Sharpen", "Nitidez", None, "sharpen_usm"),
            ("color", "Color", "Balance blancos", None, "wb_auto"),
            ("levels", "Niveles", "Curvas/niveles", None, "levels"),
            ("stars", "Estrellas", "Star tools", None, "extract_starless"),
        ], gc)

        _make_toolbar("ai", "AI & Efectos", [
            ("ai", "AI", "AI Denoise", None, "ai_denoise_wavelet"),
            ("spikes", "Spikes", "Diffraction spikes", None, "diffraction_spikes"),
            None,
            ("macro", "Nebulosa", "Macro nebulosa", self._run_macro_nebula, None),
        ], ac)

    def _setup_shortcuts(self):
        for sc, handler in [
            ("Ctrl+O", self._open_file),
            ("Ctrl+S", self._save_file),
            ("Ctrl+Z", self._undo),
            ("F5", self._run_auto),
        ]:
            a = QAction(self)
            a.setShortcut(QKeySequence(sc))
            a.triggered.connect(handler)
            self.addAction(a)

    # === CORE ===

    def _select_action(self, action_id):
        """Selecciona una accion: ilumina su boton y muestra params."""
        # Desmarcar todos, marcar el correcto
        from PyQt6.QtWidgets import QToolBar
        for tb in self.findChildren(QToolBar):
            for act in tb.actions():
                if act.isCheckable():
                    # Comparar por data guardado en el action
                    act.setChecked(act.data() == action_id)

        self._current_action_id = action_id
        self._show_action_params(action_id)

    def _show_action_params(self, action_id):
        """Muestra los params de una accion en el panel derecho
        SIN aplicarla. El usuario ajusta y pulsa Aplicar."""
        action = self.registry.get(action_id)
        if action is None:
            return
        self.params_panel.show_action(action)

    def _execute_action(self, action_id):
        """Ejecuta una accion con indicador de progreso."""
        if self.session.current_data is None:
            QMessageBox.information(
                self, tr("Sin imagen"),
                tr("Abre una imagen primero (Ctrl+O)"),
            )
            return

        # Acciones que necesitan dialogo especial
        dialog_actions = {
            "hdr_combine": self._dialog_hdr,
            "pixelmath": self._dialog_pixelmath,
            "pixelmath_rgb": self._dialog_pixelmath,
            "nb_combine_custom": self._dialog_narrowband,
            "batch_process": self._show_scripts,
            "mosaic_stitch": self._show_preprocess,
            "search_catalog": self._show_planner,
            "annotate_objects": self._action_annotate,
            "annotate_full": self._action_annotate,
            "comparison": self._action_comparison,
            "timelapse": self._action_timelapse,
            "session_metadata": self._action_metadata,
            "session_timeline": self._action_metadata,
            "session_quality_graph": self._action_metadata,
            "plate_solve": self._action_plate_solve,
        }
        if action_id in dialog_actions:
            dialog_actions[action_id]()
            return

        action = self.registry.get(action_id)
        if action is None:
            return

        params = self.params_panel.get_current_params(action)

        # Mostrar indicador de procesamiento
        self.status_label.setText(
            f"Procesando: {action.name}..."
        )
        self.progress_bar.setMaximum(0)
        self.setCursor(Qt.CursorShape.WaitCursor)
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

        # Log al panel de consola
        params_str = ", ".join(
            f"{k}={v}" for k, v in params.items()
        )
        print(f"[Ejecutando] {action.name}")
        if params_str:
            print(f"  Parametros: {params_str}")

        data = self.session.current_data
        print(f"  Imagen: {data.shape[1]}x{data.shape[0]} "
              f"{'RGB' if data.ndim == 3 else 'Mono'}")

        try:
            import time
            t0 = time.time()
            self.session.apply(action, **params)
            elapsed = time.time() - t0

            self._update_display()
            self.steps_panel.refresh(self.session)

            result = self.session.current_data
            print(f"  [OK] Completado en {elapsed:.2f}s")
            print(f"  Resultado: min={result.min():.1f} "
                  f"max={result.max():.1f} "
                  f"mean={result.mean():.1f}")
            print(f"  Undo disponibles: "
                  f"{self.session.undo_count()}")

            self.status_label.setText(
                f"{action.name} completado ({elapsed:.1f}s)"
            )
        except Exception as e:
            print(f"  [ERROR] {action.name}: {e}")
            QMessageBox.critical(
                self, tr("Error"), f"{action.name}:\n{e}"
            )
            self.status_label.setText(f"Error: {action.name}")
        finally:
            self.progress_bar.setMaximum(100)
            self.progress_bar.setValue(100)
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Abrir"), "",
            "Astro (*.fits *.fit *.fts *.tif *.tiff *.png "
            "*.jpg *.cr2 *.nef *.arw *.dng);;All (*)",
        )
        if not path:
            return

        try:
            from ..io_fits import load_image
            import os

            data, header = load_image(path)
            name = os.path.basename(path)

            self.session.load_image(data, source_info=path)
            self._update_display()
            self.steps_panel.refresh(self.session)
            self.setWindowTitle(f"Astro BellaDev - {name}")
            self.status_label.setText(
                f"{tr('Cargada')}: {name} "
                f"({data.shape[1]}x{data.shape[0]})"
            )
            print(f"[Imagen] {name}: "
                  f"{data.shape[1]}x{data.shape[0]} "
                  f"{'RGB' if data.ndim == 3 else 'Mono'}")

        except Exception as e:
            QMessageBox.critical(self, tr("Error"), str(e))

    def _close_image(self):
        """Cierra la imagen actual y resetea."""
        self.session = Session()
        self.session.progress = GuiProgress(
            self.progress_bar, self.status_label
        )
        self.image_viewer._image = None
        self.image_viewer._canvas._pixmap = None
        self.image_viewer._canvas.update()
        self.histogram._hist_data = None
        self.histogram.update()
        self.steps_panel.refresh(self.session)
        if hasattr(self, 'wizard_panel'):
            self.wizard_panel.reset()
        self.image_info_label.setText("")
        self.setWindowTitle("Astro BellaDev")
        self.status_label.setText(tr("Listo"))
        print("[Imagen] Cerrada")

    def _save_file(self):
        if self.session.current_data is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Guardar"), "",
            "FITS (*.fits);;TIFF (*.tiff);;"
            "PNG (*.png);;JPEG (*.jpg)",
        )
        if not path:
            return
        try:
            from ..export import save_image
            save_image(path, self.session.current_data)
            self.status_label.setText(f"Saved: {path}")
        except Exception as e:
            QMessageBox.critical(self, tr("Error"), str(e))

    def _undo(self):
        if self.session.undo_count() > 0:
            self.session.undo()
            self._update_display()
            self.steps_panel.refresh(self.session)

    def _run_auto(self):
        if self.session.current_data is None:
            QMessageBox.information(
                self, tr("Sin imagen"),
                tr("Abre una imagen primero"),
            )
            return
        from ..assistant import generate_processing_plan
        plan = generate_processing_plan(
            self.session.current_data, "post_stack"
        )
        for step in plan:
            action = self.registry.get(step["action_id"])
            if action:
                try:
                    params = step.get("params", {})
                    self.session.apply(action, **params)
                except Exception:
                    pass
        self._update_display()
        self.steps_panel.refresh(self.session)
        self.status_label.setText(
            tr("Pipeline automatico completado")
        )

    def _run_macro_nebula(self):
        if self.session.current_data is None:
            QMessageBox.information(
                self, tr("Sin imagen"),
                tr("Abre una imagen primero"),
            )
            return
        tb = self.toolbar_manager.get_toolbar("macros")
        if tb:
            try:
                tb.execute_button(
                    "macro_nebula", self.session, self.registry
                )
                self._update_display()
                self.steps_panel.refresh(self.session)
            except Exception as e:
                QMessageBox.critical(self, tr("Error"), str(e))

    def _set_mode(self, expert):
        self.expert_mode = expert
        t = get_theme(self.current_theme)

        active_style = (
            "background-color: {bg}; color: white; border: none;"
            "font-weight: 700; font-size: 13px; letter-spacing: 1px;"
        )
        inactive_style = (
            "background-color: {bg}; color: {fg}; border: none;"
            "font-weight: 600; font-size: 13px; letter-spacing: 1px;"
        )

        if expert:
            self.mode_expert_btn.setStyleSheet(
                f"QPushButton {{ {active_style.format(bg=GROUP_COLORS['macro'])}"
                f"border-top-right-radius: 14px;"
                f"border-bottom-right-radius: 14px; }}"
            )
            self.mode_auto_btn.setStyleSheet(
                f"QPushButton {{ {inactive_style.format(bg=t['surface'], fg=t['text_secondary'])}"
                f"border-top-left-radius: 14px;"
                f"border-bottom-left-radius: 14px; }}"
            )
        else:
            self.mode_auto_btn.setStyleSheet(
                f"QPushButton {{ {active_style.format(bg=t['accent'])}"
                f"border-top-left-radius: 14px;"
                f"border-bottom-left-radius: 14px; }}"
            )
            self.mode_expert_btn.setStyleSheet(
                f"QPushButton {{ {inactive_style.format(bg=t['surface'], fg=t['text_secondary'])}"
                f"border-top-right-radius: 14px;"
                f"border-bottom-right-radius: 14px; }}"
            )

        self._update_mode_indicator()
        self.params_panel.set_expert_mode(expert)

        # En auto: wizard + ocultar toolbars avanzadas
        if hasattr(self, 'wizard_panel'):
            self.wizard_panel.setVisible(not expert)
            self.steps_panel.setVisible(expert)
        if hasattr(self, '_toolbars'):
            for key in ["preprocess", "ai"]:
                if key in self._toolbars:
                    self._toolbars[key].setVisible(expert)

    def _update_mode_indicator(self):
        t = get_theme(self.current_theme)
        if self.expert_mode:
            color = GROUP_COLORS['macro']
            text = tr(
                "Modo experto: control total sobre cada parametro"
            )
        else:
            color = t['accent']
            text = tr(
                "Modo automatico: el asistente decide los parametros"
            )
        self.mode_indicator.setText(
            f'<span style="color:{color};">&#9679;</span> {text}'
        )

    def _open_dropped_file(self, path):
        """Abre un archivo arrastrado al canvas."""
        try:
            from ..io_fits import load_image
            data, header = load_image(path)
            self.session.load_image(data, source_info=path)
            self._update_display()
            self.steps_panel.refresh(self.session)

            import os
            name = os.path.basename(path)
            self.setWindowTitle(f"Astro BellaDev - {name}")
            self.status_label.setText(
                f"{tr('Cargada')}: {name}"
            )
        except Exception as e:
            QMessageBox.critical(self, tr("Error"), str(e))

    def _show_equipment_dialog(self):
        """Muestra el dialogo de perfil de equipo."""
        dlg = EquipmentDialog(parent=self)
        if dlg.exec():
            profile = dlg.get_profile()
            self.status_label.setText(
                f"Equipo: {profile.pixel_scale_arcsec:.2f}\"/px"
                f" | FOV: {profile.fov_width_arcmin:.0f}'"
                f"x{profile.fov_height_arcmin:.0f}'"
            )

    def _action_annotate(self):
        """Anota la imagen con objetos del catalogo."""
        from ..annotate import annotate_full
        result = annotate_full(self.session.current_data)
        import numpy as np
        self.session.load_image(
            result.astype(np.float32) if result.dtype != np.float32
            else result,
            "Anotada",
        )
        self._update_display()
        print("[Anotacion] Imagen anotada")

    def _action_comparison(self):
        """Crea comparacion antes/despues."""
        if self.session.undo_count() == 0:
            QMessageBox.information(
                self, "Sin historial",
                "Necesitas al menos un paso aplicado "
                "para crear una comparacion.",
            )
            return
        from ..publish import create_comparison
        import numpy as np
        # Usar el backup del undo como "antes"
        before = self.session._undo_stack[-1]
        after = self.session.current_data
        result = create_comparison(before, after, mode="slider")
        self.session.load_image(
            result.astype(np.float32), "Comparacion"
        )
        self._update_display()
        print("[Comparacion] Antes/Despues creada")

    def _action_timelapse(self):
        """Crea timelapse desde el historial de undos."""
        if self.session.undo_count() == 0:
            QMessageBox.information(
                self, "Sin historial",
                "Necesitas varios pasos para crear timelapse.",
            )
            return
        from ..publish import create_timelapse_frames, save_gif
        frames = list(self.session._undo_stack) + [
            self.session.current_data
        ]
        tl_frames = create_timelapse_frames(frames)

        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar GIF", "timelapse.gif",
            "GIF (*.gif)",
        )
        if path:
            try:
                save_gif(tl_frames, path, duration_ms=500)
                self.status_label.setText(
                    f"Timelapse guardado: {path}"
                )
                print(f"[Timelapse] {len(tl_frames)} frames "
                      f"-> {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def _action_metadata(self):
        """Muestra metadatos de la imagen en consola."""
        from ..color import image_statistics
        stats = image_statistics(self.session.current_data)
        print("\n[Estadisticas de imagen]")
        for k, v in stats.items():
            if isinstance(v, dict):
                print(f"  {k}:")
                for k2, v2 in v.items():
                    print(f"    {k2}: {v2:.4f}")
            else:
                print(f"  {k}: {v}")

    def _action_plate_solve(self):
        """Plate solving de la imagen actual."""
        from ..platesolve import solve_image
        data = self.session.current_data
        solution = solve_image(data)
        if solution.solved:
            print(f"\n[Plate Solving]")
            print(f"  RA: {solution.ra_center:.4f}")
            print(f"  Dec: {solution.dec_center:.4f}")
            print(f"  Pixel scale: "
                  f"{solution.pixel_scale:.2f} arcsec/px")
            print(f"  FOV: {solution.fov_width_arcmin:.1f}' x "
                  f"{solution.fov_height_arcmin:.1f}'")
            self.status_label.setText(
                f"Solved: RA={solution.ra_center:.3f} "
                f"Dec={solution.dec_center:.3f}"
            )
        else:
            print("[Plate Solving] No se pudo resolver")
            self.status_label.setText("Plate solving fallido")

    def _dialog_hdr(self):
        """Dialogo HDR: combinar 2 exposiciones."""
        dlg = HDRDialog(self.session.current_data, self)
        if dlg.exec():
            result = dlg.get_result()
            if result is not None:
                self.session.load_image(result, "HDR result")
                self._update_display()
                print("[HDR] Combinacion completada")

    def _dialog_pixelmath(self):
        """Dialogo PixelMath."""
        dlg = PixelMathDialog(self.session.current_data, self)
        if dlg.exec():
            result = dlg.get_result()
            if result is not None:
                import numpy as np
                if result.ndim == 2 and self.session.current_data.ndim == 3:
                    result = np.stack([result]*3, axis=-1)
                self.session.load_image(
                    result.astype(np.float32), "PixelMath"
                )
                self._update_display()
                print("[PixelMath] Expresion aplicada")

    def _dialog_narrowband(self):
        """Dialogo Narrowband personalizado."""
        dlg = NarrowbandDialog(self.session.current_data, self)
        if dlg.exec():
            result = dlg.get_result()
            if result is not None:
                self.session.load_image(result, "Narrowband")
                self._update_display()
                print("[Narrowband] Combinacion completada")

    def _show_preprocess(self):
        """Abre el dialogo de pre-procesamiento."""
        dlg = PreprocessDialog(self)
        if dlg.exec():
            result = dlg.get_result()
            if result is not None:
                self.session.load_image(
                    result, source_info="Pipeline result"
                )
                self._active_viewer.set_image(result)
                self._update_display()
                self.steps_panel.refresh(self.session)
                self.status_label.setText(
                    "Apilado cargado en el visor"
                )

    def _show_scripts(self):
        """Abre el dialogo de gestion de scripts."""
        dlg = ScriptsDialog(self.registry, self.session, self)
        dlg.exec()
        self._update_display()
        self.steps_panel.refresh(self.session)

    def _run_script(self, script_name):
        """Ejecuta un script por nombre."""
        from ..scripts import ScriptManager, execute_script
        sm = ScriptManager()
        sm.scan()
        script = sm.get(script_name)
        if script is None:
            return

        # Scripts de apilamiento abren el pipeline
        pipeline_keywords = [
            "seestar", "preprocessing", "solo lights",
            "osc_preprocessing", "mono_preprocessing",
        ]
        is_pipeline = any(
            kw in script.name.lower() or
            kw in script.description.lower()
            for kw in pipeline_keywords
        )

        if is_pipeline or (
            self.session.current_data is None and
            script.category == "Pre-procesamiento"
        ):
            self._show_preprocess()
            return

        if self.session.current_data is None:
            QMessageBox.information(
                self, tr("Sin imagen"),
                tr("Abre una imagen primero"),
            )
            return

        try:
            execute_script(script, self.session, self.registry)
            self._update_display()
            self.steps_panel.refresh(self.session)
            self.status_label.setText(
                f"Script '{script.name}' completado"
            )
        except Exception as e:
            QMessageBox.critical(self, tr("Error"), str(e))

    def _wizard_analyze(self):
        """Wizard paso 2: analizar imagen."""
        if hasattr(self, 'assistant_panel'):
            self.assistant_panel._analyze()

    def _show_planner(self):
        """Muestra el planificador de sesion."""
        dlg = PlannerDialog(parent=self)
        dlg.exec()

    def _show_about(self):
        """Muestra el dialogo About."""
        dlg = AboutDialog(parent=self)
        dlg.exec()

    def _change_language(self, lang_code):
        """Cambia el idioma y reconstruye la GUI."""
        set_language(lang_code)

        # Reconstruir menus
        self.menuBar().clear()
        self._setup_menus()

        # Reconstruir toolbars
        for tb in self.findChildren(QToolBar):
            self.removeToolBar(tb)
            tb.deleteLater()
        self._setup_toolbar()
        self._set_mode(self.expert_mode)

        # Actualizar textos visibles
        self.mode_auto_btn.setText(tr("AUTO"))
        self.mode_expert_btn.setText(tr("EXPERTO"))
        self.status_label.setText(tr("Listo"))
        self.params_panel.title_label.setText(tr("Parametros"))
        self.params_panel.apply_button.setText(tr("Aplicar"))
        self.params_panel.reset_button.setText(tr("Reset"))
        self._update_mode_indicator()

        # Refrescar accion actual en params
        if self.params_panel._current_action:
            self.params_panel.show_action(
                self.params_panel._current_action
            )

    def _update_sys_info(self):
        """Actualiza indicadores de RAM, disco y nucleos."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            mem_used = mem.used / (1024 ** 3)
            mem_total = mem.total / (1024 ** 3)

            disk = psutil.disk_usage('/')
            disk_free = disk.free / (1024 ** 3)

            cores = psutil.cpu_count(logical=False) or 1
            threads = psutil.cpu_count(logical=True) or 1

            self.sys_info_label.setText(
                f"Mem: {mem_used:.1f}/{mem_total:.0f} GiB  |  "
                f"Disco: {disk_free:.0f} GiB  |  "
                f"CPU: {cores}c/{threads}t"
            )
        except ImportError:
            import os
            cores = os.cpu_count() or 1
            self.sys_info_label.setText(f"CPU: {cores} nucleos")

    def _update_display(self):
        if self.session.current_data is not None:
            self.image_viewer.set_image(self.session.current_data)
            self.histogram.update_histogram(
                self.session.current_data
            )
            data = self.session.current_data
            h, w = data.shape[:2]
            mode = "RGB" if data.ndim == 3 else "Mono"
            undo = self.session.undo_count()
            self.image_info_label.setText(
                f"{w} x {h}  |  {mode}  |  Undo: {undo}"
            )
