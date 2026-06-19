"""
wizard_panel.py
---------------
Panel de modo guiado (wizard) para el modo AUTO.
Lleva al usuario paso a paso por el pipeline completo,
explicando que hace cada paso y aplicandolo con un click.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QProgressBar,
)
from PyQt6.QtCore import Qt

from .i18n import tr


WIZARD_STEPS = [
    {
        "title": "1. Cargar imagen",
        "desc": "Abre tus light frames apilados (FITS, TIFF o RAW). "
                "Si aun no has apilado, usa el pipeline completo desde "
                "Pre-procesamiento.",
        "action": None,
        "icon": "open",
        "button": "Abrir imagen",
        "handler": "_open_file",
    },
    {
        "title": "2. Analizar imagen",
        "desc": "El asistente analiza tu imagen y detecta problemas: "
                "gradiente, ruido, estrellas alargadas, color "
                "desbalanceado. Te dice exactamente que corregir.",
        "action": None,
        "icon": "assistant",
        "button": "Analizar",
        "handler": "_wizard_analyze",
    },
    {
        "title": "3. Stretch (estirar)",
        "desc": "Tu imagen esta en formato lineal (casi toda negra). "
                "El stretch revela las estructuras debiles. "
                "Ajusta 'midtone' (0.15-0.25) para controlar "
                "cuanta senal se revela. Valor bajo = mas senal.",
        "action": "stretch_midtone",
        "icon": "stretch",
        "button": "Aplicar Stretch",
    },
    {
        "title": "4. Extraccion de fondo (ABE)",
        "desc": "Elimina gradientes de contaminacion luminica y "
                "vineteo residual. Ahora que la imagen es visible, "
                "podras ver si hay gradientes que corregir.",
        "action": "background_abe",
        "icon": "background",
        "button": "Aplicar ABE",
    },
    {
        "title": "5. Reduccion de ruido",
        "desc": "Reduce el ruido del fondo sin perder detalle en "
                "nebulosas y estrellas. Filtra mas la luminancia "
                "(donde esta el ruido visible) y menos el color.",
        "action": "denoise_selective",
        "icon": "denoise",
        "button": "Aplicar Denoise",
    },
    {
        "title": "6. Balance de color",
        "desc": "Corrige el balance de blancos para que las estrellas "
                "se vean con sus colores reales. Usa estrellas "
                "brillantes como referencia neutra.",
        "action": "wb_stars",
        "icon": "color",
        "button": "Aplicar WB",
    },
    {
        "title": "7. Nitidez",
        "desc": "Recupera detalle perdido por el seeing atmosferico "
                "y las aberraciones opticas. Unsharp Mask para "
                "detalles finos.",
        "action": "sharpen_usm",
        "icon": "sharpen",
        "button": "Aplicar Sharpen",
    },
    {
        "title": "8. Saturacion",
        "desc": "Potencia los colores de la imagen. Las nebulosas "
                "y estrellas ganaran viveza. Ajusta al gusto.",
        "action": "saturation",
        "icon": "color",
        "button": "Aplicar Color",
    },
    {
        "title": "9. Guardar resultado",
        "desc": "Guarda tu imagen procesada. FITS para seguir "
                "procesando, TIFF para calidad maxima, PNG/JPEG "
                "para compartir en redes.",
        "action": None,
        "icon": "save",
        "button": "Guardar",
        "handler": "_save_file",
    },
]


class WizardStepCard(QFrame):
    """Tarjeta de un paso del wizard. Clickable para navegar."""

    def __init__(self, step_data, step_index, is_current=False,
                 is_done=False, parent=None):
        super().__init__(parent)
        self.step_data = step_data
        self.step_index = step_index
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        if is_current:
            bg = "rgba(74, 127, 181, 0.12)"
            border = "#4A7FB5"
        elif is_done:
            bg = "rgba(76, 175, 110, 0.08)"
            border = "#4CAF6E"
        else:
            bg = "transparent"
            border = "#2A2F45"

        self.setStyleSheet(f"""
            WizardStepCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
                padding: 6px;
                margin: 2px 0;
            }}
            WizardStepCard:hover {{
                border-color: #4A7FB5;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        # Titulo con estado
        header = QHBoxLayout()
        if is_done:
            status = QLabel("[OK]")
            status.setStyleSheet(
                "color: #4CAF6E; font-weight: 700; font-size: 12px;"
            )
        elif is_current:
            status = QLabel("[>>]")
            status.setStyleSheet(
                "color: #4A7FB5; font-weight: 700; font-size: 12px;"
            )
        else:
            status = QLabel("[  ]")
            status.setStyleSheet(
                "color: #4A5068; font-size: 12px;"
            )
        status.setFixedWidth(30)
        header.addWidget(status)

        title = QLabel(step_data["title"])
        title.setStyleSheet(
            f"font-weight: {'700' if is_current else '500'};"
            f"font-size: {'14px' if is_current else '13px'};"
        )
        header.addWidget(title, stretch=1)
        layout.addLayout(header)

        if is_current:
            desc = QLabel(step_data["desc"])
            desc.setWordWrap(True)
            desc.setStyleSheet(
                "color: #8892A8; font-size: 12px; "
                "margin-left: 30px; margin-top: 4px;"
            )
            layout.addWidget(desc)

    def mousePressEvent(self, event):
        """Click en la card navega a ese paso."""
        wizard = self.parent()
        while wizard and not isinstance(wizard, WizardPanel):
            wizard = wizard.parent()
        if wizard:
            wizard._go_to_step(self.step_index)


class WizardPanel(QWidget):
    """Panel wizard que reemplaza al steps panel en modo AUTO."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_step = 0
        self._done_steps = set()

        self.setFixedWidth(280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(6)

        # Header
        title = QLabel("Modo Guiado")
        title.setStyleSheet(
            "font-weight: 700; font-size: 15px; color: #4A7FB5;"
        )
        layout.addWidget(title)

        subtitle = QLabel(
            "Sigue los pasos en orden para\n"
            "procesar tu imagen de principio a fin."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Progreso
        self.progress = QProgressBar()
        self.progress.setMaximum(len(WIZARD_STEPS))
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        layout.addWidget(self.progress)

        self.progress_label = QLabel("Paso 1 de 9")
        self.progress_label.setObjectName("subtitle")
        layout.addWidget(self.progress_label)

        # Cards container
        from PyQt6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 4, 0, 0)
        self.cards_layout.setSpacing(4)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll, stretch=1)

        # Info para el usuario
        self.tip_label = QLabel("")
        self.tip_label.setWordWrap(True)
        self.tip_label.setStyleSheet(
            "color: #E6A817; font-size: 12px; "
            "background: rgba(230,168,23,0.08); "
            "border: 1px solid rgba(230,168,23,0.2); "
            "border-radius: 5px; padding: 6px; margin: 2px 0;"
        )
        self.tip_label.setVisible(False)
        layout.addWidget(self.tip_label)

        # Botones
        self.action_btn = QPushButton("Abrir imagen")
        self.action_btn.setObjectName("primary")
        self.action_btn.setMinimumHeight(36)
        self.action_btn.clicked.connect(self._on_action)
        layout.addWidget(self.action_btn)

        nav = QHBoxLayout()

        self.undo_btn = QPushButton("Deshacer paso")
        self.undo_btn.setStyleSheet(
            "color: #D94452; border-color: #D94452;"
        )
        self.undo_btn.clicked.connect(self._undo_step)
        self.undo_btn.setEnabled(False)
        nav.addWidget(self.undo_btn)

        self.repeat_btn = QPushButton("Repetir")
        self.repeat_btn.clicked.connect(self._repeat_step)
        self.repeat_btn.setEnabled(False)
        nav.addWidget(self.repeat_btn)

        layout.addLayout(nav)

        # Navegacion libre
        nav2 = QHBoxLayout()

        self.prev_btn = QPushButton("<< Anterior")
        self.prev_btn.clicked.connect(self._prev_step)
        nav2.addWidget(self.prev_btn)

        self.skip_btn = QPushButton("Saltar >>")
        self.skip_btn.clicked.connect(self._next_step)
        nav2.addWidget(self.skip_btn)

        layout.addLayout(nav2)

        self._refresh_cards()

    def _refresh_cards(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, step in enumerate(WIZARD_STEPS):
            card = WizardStepCard(
                step, i,
                is_current=(i == self._current_step),
                is_done=(i in self._done_steps),
            )
            self.cards_layout.addWidget(card)

        step = WIZARD_STEPS[self._current_step]
        self.action_btn.setText(step["button"])
        self.progress.setValue(len(self._done_steps))
        self.progress_label.setText(
            f"Paso {self._current_step + 1} de {len(WIZARD_STEPS)}"
        )

        # Mostrar tips contextuales
        has_action = step.get("action") is not None
        is_done = self._current_step in self._done_steps

        if is_done and has_action:
            self.tip_label.setText(
                "Ya aplicaste este paso. Puedes:\n"
                "- 'Deshacer paso' si no te gusta el resultado\n"
                "- 'Repetir' con parametros diferentes\n"
                "- 'Saltar' para continuar"
            )
            self.tip_label.setVisible(True)
        elif has_action:
            self.tip_label.setText(
                "Ajusta los parametros en el panel derecho "
                "antes de aplicar. Activa 'Preview en tiempo real' "
                "para ver el efecto antes de confirmar."
            )
            self.tip_label.setVisible(True)
        else:
            self.tip_label.setVisible(False)

        self.undo_btn.setEnabled(is_done)
        self.repeat_btn.setEnabled(is_done and has_action)
        self.prev_btn.setEnabled(self._current_step > 0)
        self.skip_btn.setEnabled(
            self._current_step < len(WIZARD_STEPS) - 1
        )

        # Mostrar parametros en panel derecho automaticamente
        if has_action:
            self._show_params_for_step(step)

    def _show_params_for_step(self, step):
        """Muestra los parametros del paso actual en el panel derecho,
        forzando modo experto y preview activado."""
        main = self._get_main()
        if main:
            main.params_panel._expert_mode = True
            main.params_panel.preview_check.setChecked(True)
            main._show_action_params(step["action"])

    def _get_main(self):
        main = self.parent()
        while main and not hasattr(main, '_execute_action'):
            main = main.parent()
        return main

    def _on_action(self):
        step = WIZARD_STEPS[self._current_step]
        main = self._get_main()
        if not main:
            return

        if step.get("handler"):
            handler = getattr(main, step["handler"], None)
            if handler:
                handler()
                self._mark_done()
        elif step.get("action"):
            if main.session.current_data is None:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(
                    self, "Sin imagen",
                    "Primero carga una imagen (paso 1)",
                )
                return
            # Ejecutar con los params que el usuario ajusto
            main._execute_action(step["action"])
            self._mark_done()

    def _undo_step(self):
        """Deshace el ultimo paso aplicado."""
        main = self._get_main()
        if main and main.session.undo_count() > 0:
            main._undo()
            # Desmarcar el paso actual como hecho
            if self._current_step in self._done_steps:
                self._done_steps.remove(self._current_step)
            self._refresh_cards()

    def _repeat_step(self):
        """Deshace y permite repetir con parametros diferentes."""
        self._undo_step()
        # Los params ya se muestran por _refresh_cards

    def _wizard_analyze(self):
        main = self._get_main()
        if main and hasattr(main, 'assistant_panel'):
            main.assistant_panel._analyze()

    def _mark_done(self):
        self._done_steps.add(self._current_step)
        if self._current_step < len(WIZARD_STEPS) - 1:
            self._current_step += 1
        self._refresh_cards()

    def _go_to_step(self, index):
        """Navega directamente a cualquier paso."""
        if 0 <= index < len(WIZARD_STEPS):
            self._current_step = index
            self._refresh_cards()

    def _next_step(self):
        if self._current_step < len(WIZARD_STEPS) - 1:
            self._current_step += 1
            self._refresh_cards()

    def _prev_step(self):
        if self._current_step > 0:
            self._current_step -= 1
            self._refresh_cards()

    def reset(self):
        self._current_step = 0
        self._done_steps.clear()
        self._refresh_cards()
