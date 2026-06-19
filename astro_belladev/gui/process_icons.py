"""
process_icons.py
----------------
Panel de Process Icons arrastrable, como PixInsight.

Una barra inferior donde el usuario puede arrastrar acciones
predefinidas o crear las suyas propias. Cada icono es un boton
con una accion + parametros guardados que se ejecuta con un click.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QToolButton, QMenu, QLabel,
    QScrollArea, QInputDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, QSize, QMimeData
from PyQt6.QtGui import QAction, QDrag

from .icons import get_icon
from .i18n import tr


class ProcessIconWidget(QToolButton):
    """Un icono de proceso individual."""

    def __init__(self, name, icon_name, action_id, params=None,
                 color="#4A7FB5", tooltip="", parent=None):
        super().__init__(parent)
        self.action_id = action_id
        self.action_params = params or {}
        self.icon_name = icon_name
        self.process_name = name

        self.setIcon(get_icon(icon_name, 28))
        self.setIconSize(QSize(28, 28))
        self.setText(name)
        self.setToolTip(tooltip or name)
        self.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextUnderIcon
        )
        self.setFixedSize(70, 58)
        self.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                color: #B0B8C8;
                border: 1px solid transparent;
                border-radius: 6px;
                font-size: 13px;
                padding: 2px;
            }}
            QToolButton:hover {{
                background-color: rgba(74, 127, 181, 0.15);
                border-color: rgba(74, 127, 181, 0.4);
                color: white;
            }}
            QToolButton:pressed {{
                background-color: rgba(74, 127, 181, 0.3);
            }}
        """)

        self.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.customContextMenuRequested.connect(self._context_menu)

    def _context_menu(self, pos):
        menu = QMenu(self)
        edit = menu.addAction("Editar parametros")
        rename = menu.addAction("Renombrar")
        remove = menu.addAction("Eliminar")

        action = menu.exec(self.mapToGlobal(pos))
        if action == remove:
            parent = self.parent()
            if parent and hasattr(parent, 'remove_icon'):
                parent.remove_icon(self)
        elif action == rename:
            text, ok = QInputDialog.getText(
                self, "Renombrar", "Nuevo nombre:",
                text=self.process_name,
            )
            if ok and text:
                self.process_name = text
                self.setText(text)


class ProcessIconsBar(QWidget):
    """Barra de Process Icons en la parte inferior."""

    def __init__(self, registry, parent=None):
        super().__init__(parent)
        self.registry = registry
        self._icons = []

        self.setFixedHeight(72)
        self.setStyleSheet("""
            ProcessIconsBar {
                border-top: 1px solid #2A2F45;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(2)

        label = QLabel("Process Icons")
        label.setStyleSheet(
            "color: #5A6378; font-size: 13px;"
            "font-weight: 600; letter-spacing: 1px;"
        )
        label.setFixedWidth(50)
        layout.addWidget(label)

        sep = QWidget()
        sep.setFixedWidth(1)
        sep.setStyleSheet("background-color: #2A2F45;")
        layout.addWidget(sep)

        scroll = QScrollArea()
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )
        scroll.setFixedHeight(64)

        self.icons_container = QWidget()
        self.icons_container.setStyleSheet("background: transparent;")
        self.icons_layout = QHBoxLayout(self.icons_container)
        self.icons_layout.setContentsMargins(4, 0, 4, 0)
        self.icons_layout.setSpacing(2)
        self.icons_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        scroll.setWidget(self.icons_container)
        layout.addWidget(scroll, stretch=1)

        # Boton para anadir
        add_btn = QToolButton()
        add_btn.setText("+")
        add_btn.setFixedSize(36, 36)
        add_btn.setStyleSheet("""
            QToolButton {
                background: transparent;
                color: #5A6378; border: 1px dashed #3A4060;
                border-radius: 6px; font-size: 18px;
            }
            QToolButton:hover {
                color: #4A7FB5; border-color: #4A7FB5;
            }
        """)
        add_btn.setToolTip("Anadir process icon")
        add_btn.clicked.connect(self._add_icon_dialog)
        layout.addWidget(add_btn)

        self._add_defaults()

    def _add_defaults(self):
        """Iconos por defecto."""
        defaults = [
            ("STF", "stretch", "stretch_midtone",
             {"midtone": 0.25, "black_clip": -2.8}, "Stretch MTF"),
            ("ABE", "background", "background_abe",
             {"grid_size": 8}, "Background extraction"),
            ("Denoise", "denoise", "denoise_selective",
             {"lum_strength": 0.5}, "Noise reduction"),
            ("Sharp", "sharpen", "sharpen_usm",
             {"radius": 2.0, "amount": 1.0}, "Unsharp mask"),
            ("WB", "color", "wb_auto",
             {}, "White balance"),
            ("Sat+", "color", "saturation",
             {"factor": 1.3}, "Boost saturation"),
            ("SCNR", "color", "scnr_average",
             {"amount": 1.0}, "Remove green noise"),
            ("Stars-", "starless", "extract_starless",
             {}, "Remove stars"),
            ("Spikes", "spikes", "diffraction_spikes",
             {"num_spikes": 4}, "Add diffraction spikes"),
            ("CLAHE", "levels", "clahe",
             {"clip_limit": 2.0}, "Local contrast"),
            ("AI Dn", "ai", "ai_denoise_wavelet",
             {"strength": 0.5}, "AI wavelet denoise"),
        ]

        for name, icon, aid, params, tip in defaults:
            self.add_icon(name, icon, aid, params, tip)

    def add_icon(self, name, icon_name, action_id, params=None,
                  tooltip=""):
        icon = ProcessIconWidget(
            name, icon_name, action_id, params, tooltip=tooltip,
        )
        icon.clicked.connect(
            lambda ch, i=icon: self._on_icon_clicked(i)
        )
        self.icons_layout.addWidget(icon)
        self._icons.append(icon)

    def remove_icon(self, icon):
        self.icons_layout.removeWidget(icon)
        self._icons.remove(icon)
        icon.deleteLater()

    def _on_icon_clicked(self, icon):
        main = self.parent()
        while main and not hasattr(main, '_show_action_params'):
            main = main.parent()
        if main:
            main._show_action_params(icon.action_id)

    def _add_icon_dialog(self):
        """Dialogo para anadir un nuevo process icon."""
        actions = self.registry.get_all()
        names = [f"{a.name} ({a.id})" for a in actions]

        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getItem(
            self, "Anadir Process Icon",
            "Selecciona una accion:", names, 0, False,
        )
        if ok and name:
            idx = names.index(name)
            action = actions[idx]
            icon_map = {
                "stretch": "stretch", "background": "background",
                "denoise": "denoise", "sharpen": "sharpen",
                "color": "color", "star": "stars",
                "ai_": "ai", "level": "levels",
            }
            icon_name = "auto"
            for prefix, iname in icon_map.items():
                if prefix in action.id:
                    icon_name = iname
                    break
            self.add_icon(
                action.name[:8], icon_name, action.id,
                tooltip=action.name,
            )
