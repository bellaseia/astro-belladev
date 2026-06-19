"""
params_panel.py
---------------
Panel derecho: parametros de la accion con sliders + spinbox.

Cuando el usuario hace click en un boton de la toolbar o un menu,
este panel muestra los parametros editables. El usuario ajusta los
valores y pulsa "Aplicar" para ejecutar. Como PixInsight.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QSlider, QDoubleSpinBox,
    QSpinBox, QComboBox, QPushButton, QFormLayout,
    QScrollArea, QCheckBox, QHBoxLayout,
)
from PyQt6.QtCore import Qt

from .i18n import tr


class ParamsPanel(QWidget):

    def __init__(self, registry, parent=None):
        super().__init__(parent)
        self.registry = registry
        self._current_action = None
        self._widgets = {}
        self._expert_mode = False

        self.setFixedWidth(280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.title_label = QLabel(tr("Parametros"))
        self.title_label.setObjectName("title")
        layout.addWidget(self.title_label)

        self.desc_label = QLabel("")
        self.desc_label.setWordWrap(True)
        self.desc_label.setObjectName("subtitle")
        layout.addWidget(self.desc_label)

        # Mensaje modo auto (visible solo en auto)
        self.auto_msg = QLabel(
            "Modo AUTO: los parametros se ajustan\n"
            "automaticamente. Pulsa Aplicar para\n"
            "ejecutar con la configuracion optima."
        )
        self.auto_msg.setWordWrap(True)
        self.auto_msg.setStyleSheet(
            "color: #4A7FB5; background-color: rgba(74,127,181,0.08);"
            "border: 1px solid rgba(74,127,181,0.2);"
            "border-radius: 6px; padding: 10px; margin: 4px 0;"
        )
        self.auto_msg.setVisible(True)
        layout.addWidget(self.auto_msg)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )

        self.params_container = QWidget()
        self.params_container.setStyleSheet("background: transparent;")
        self.params_layout = QFormLayout(self.params_container)
        self.params_layout.setContentsMargins(0, 8, 0, 0)
        self.params_layout.setSpacing(10)
        scroll.setWidget(self.params_container)
        layout.addWidget(scroll, stretch=1)

        # Preview checkbox
        from PyQt6.QtWidgets import QCheckBox as QCB
        self.preview_check = QCB("Preview en tiempo real")
        self.preview_check.setChecked(False)
        self.preview_check.setToolTip(
            "Aplica cambios al soltar el slider (puede ser lento)"
        )
        layout.addWidget(self.preview_check)

        # Botones
        self.apply_button = QPushButton(tr("Aplicar"))
        self.apply_button.setObjectName("primary")
        self.apply_button.setMinimumHeight(34)
        self.apply_button.clicked.connect(self._on_apply)
        layout.addWidget(self.apply_button)

        self.reset_button = QPushButton(tr("Reset"))
        self.reset_button.clicked.connect(self._on_reset)
        layout.addWidget(self.reset_button)

    def show_action(self, action):
        """Muestra los parametros de una accion."""
        self._current_action = action
        self._widgets.clear()

        self.title_label.setText(action.name)
        self.desc_label.setText(action.description)

        while self.params_layout.count():
            item = self.params_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # En modo auto, ocultar sliders y mostrar mensaje
        if not self._expert_mode:
            self.auto_msg.setVisible(True)
            self.auto_msg.setText(
                f"Modo AUTO\n\n"
                f"'{action.name}' se aplicara con\n"
                f"parametros optimizados automaticamente.\n\n"
                f"Cambia a EXPERTO para ajustar manualmente."
            )
            return

        self.auto_msg.setVisible(False)

        if not action.params:
            lbl = QLabel(tr("Sin parametros configurables"))
            lbl.setObjectName("subtitle")
            self.params_layout.addRow(lbl)
            return

        for param in action.params:
            widget = self._create_param_widget(param)
            if widget:
                name_lbl = QLabel(param.name)
                name_lbl.setToolTip(param.tooltip)
                name_lbl.setStyleSheet("font-weight: 600;")
                self.params_layout.addRow(name_lbl, widget)
                self._widgets[param.name] = widget

    def _create_param_widget(self, param):
        if param.choices:
            combo = QComboBox()
            combo.setStyleSheet("""
                QComboBox {
                    background-color: #1A1E30;
                    color: #E0E4EC;
                    border: 1px solid #2A2F45;
                    border-radius: 4px;
                    padding: 4px 8px;
                }
                QComboBox QAbstractItemView {
                    background-color: #1E2233;
                    color: #E0E4EC;
                    border: 1px solid #2A2F45;
                    selection-background-color: #4A7FB5;
                    selection-color: white;
                }
            """)
            for choice in param.choices:
                combo.addItem(str(choice))
            idx = combo.findText(str(param.default))
            if idx >= 0:
                combo.setCurrentIndex(idx)
            return combo

        if param.type == float:
            container = QWidget()
            container.setStyleSheet("background: transparent;")
            lay = QVBoxLayout(container)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(2)

            spin = QDoubleSpinBox()
            spin.setDecimals(3)
            pmin = param.min_value if param.min_value is not None else -99999
            pmax = param.max_value if param.max_value is not None else 99999
            spin.setMinimum(pmin)
            spin.setMaximum(pmax)
            spin.setValue(param.default)
            spin.setSingleStep(0.01)
            lay.addWidget(spin)

            if param.min_value is not None and param.max_value is not None:
                slider = QSlider(Qt.Orientation.Horizontal)
                slider.setMinimum(0)
                slider.setMaximum(1000)
                norm = (param.default - pmin) / max(pmax - pmin, 0.001)
                slider.setValue(int(norm * 1000))

                def on_slider(val, s=spin, mn=pmin, mx=pmax):
                    s.setValue(mn + (mx - mn) * val / 1000)

                def on_spin(val, sl=slider, mn=pmin, mx=pmax):
                    n = (val - mn) / max(mx - mn, 0.001)
                    sl.blockSignals(True)
                    sl.setValue(int(n * 1000))
                    sl.blockSignals(False)

                slider.valueChanged.connect(on_slider)
                spin.valueChanged.connect(on_spin)
                slider.sliderReleased.connect(self._on_slider_released)
                spin.valueChanged.connect(
                    lambda v: self._on_slider_released()
                )
                lay.addWidget(slider)

            container._spin = spin
            return container

        if param.type == int:
            container = QWidget()
            container.setStyleSheet("background: transparent;")
            lay = QVBoxLayout(container)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(2)

            spin = QSpinBox()
            pmin = int(param.min_value) if param.min_value is not None else 0
            pmax = int(param.max_value) if param.max_value is not None else 99999
            spin.setMinimum(pmin)
            spin.setMaximum(pmax)
            spin.setValue(int(param.default))
            lay.addWidget(spin)

            if param.min_value is not None and param.max_value is not None:
                slider = QSlider(Qt.Orientation.Horizontal)
                slider.setMinimum(pmin)
                slider.setMaximum(pmax)
                slider.setValue(int(param.default))

                slider.valueChanged.connect(spin.setValue)
                spin.valueChanged.connect(slider.setValue)
                slider.sliderReleased.connect(self._on_slider_released)
                spin.valueChanged.connect(
                    lambda v: self._on_slider_released()
                )
                lay.addWidget(slider)

            container._spin = spin
            return container

        if param.type == bool:
            check = QCheckBox()
            check.setChecked(bool(param.default))
            return check

        if param.type == str:
            combo = QComboBox()
            combo.setEditable(True)
            combo.setCurrentText(str(param.default))
            combo.setStyleSheet("""
                QComboBox {
                    background-color: #1A1E30;
                    color: #E0E4EC;
                    border: 1px solid #2A2F45;
                    border-radius: 4px;
                    padding: 4px 8px;
                }
                QComboBox QAbstractItemView {
                    background-color: #1E2233;
                    color: #E0E4EC;
                    border: 1px solid #2A2F45;
                    selection-background-color: #4A7FB5;
                }
            """)
            return combo

        return None

    def get_current_params(self, action=None):
        if action is None:
            action = self._current_action
        if action is None:
            return {}

        params = {}
        for param in action.params:
            if param.name in self._widgets:
                widget = self._widgets[param.name]

                if hasattr(widget, '_spin'):
                    spin = widget._spin
                    if isinstance(spin, QDoubleSpinBox):
                        params[param.name] = spin.value()
                    elif isinstance(spin, QSpinBox):
                        params[param.name] = spin.value()
                elif isinstance(widget, QDoubleSpinBox):
                    params[param.name] = widget.value()
                elif isinstance(widget, QSpinBox):
                    params[param.name] = widget.value()
                elif isinstance(widget, QComboBox):
                    val = widget.currentText()
                    if param.type == int:
                        params[param.name] = int(val)
                    elif param.type == float:
                        params[param.name] = float(val)
                    else:
                        params[param.name] = val
                elif isinstance(widget, QCheckBox):
                    params[param.name] = widget.isChecked()

        return params

    def _on_slider_released(self):
        """Preview al soltar el slider o cambiar valor."""
        if self.preview_check.isChecked():
            # Delay para no recalcular en cada tick
            if not hasattr(self, '_preview_timer'):
                from PyQt6.QtCore import QTimer
                self._preview_timer = QTimer()
                self._preview_timer.setSingleShot(True)
                self._preview_timer.timeout.connect(self._do_preview)
            self._preview_timer.start(300)

    def _do_preview(self):
        """Aplica la accion temporalmente para previsualizar."""
        if not self._current_action:
            return

        main = self.parent()
        while main and not isinstance(main, QMainWindow):
            main = main.parent()
        if not main or main.session.current_data is None:
            return

        action = self._current_action
        params = self.get_current_params(action)

        # Guardar datos antes del preview
        if not hasattr(self, '_preview_backup'):
            self._preview_backup = None

        if self._preview_backup is None:
            import numpy as np
            self._preview_backup = main.session.current_data.copy()

        # Aplicar sobre la copia del backup (no modifica sesion)
        try:
            import numpy as np
            main.status_label.setText(
                f"Preview: {action.name}..."
            )
            main.setCursor(Qt.CursorShape.WaitCursor)
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()

            import time
            t0 = time.time()
            temp = self._preview_backup.copy()
            result = action.execute(temp, **params)
            elapsed = time.time() - t0

            main.image_viewer.set_image(result)
            main.histogram.update_histogram(result)
            self._preview_result = result

            main.status_label.setText(
                f"Preview: {action.name} ({elapsed:.1f}s)"
            )
            main.setCursor(Qt.CursorShape.ArrowCursor)
        except Exception as e:
            main.status_label.setText(f"Preview error: {e}")
            main.setCursor(Qt.CursorShape.ArrowCursor)

    def _on_apply(self):
        if self._current_action and self.parent():
            main = self.parent()
            while main and not isinstance(main, QMainWindow):
                main = main.parent()
            if not main:
                return

            # Si hay preview activo, confirmar el resultado
            if hasattr(self, '_preview_result') and self._preview_result is not None:
                import numpy as np
                # Restaurar backup y aplicar de verdad en la sesion
                if self._preview_backup is not None:
                    main.session.current_data = self._preview_backup
                main._execute_action(self._current_action.id)
                self._preview_backup = None
                self._preview_result = None
            elif hasattr(main, '_execute_action'):
                main._execute_action(self._current_action.id)

    def _on_reset(self):
        """Resetea params y cancela preview."""
        # Restaurar imagen original si habia preview
        if hasattr(self, '_preview_backup') and self._preview_backup is not None:
            main = self.parent()
            while main and not isinstance(main, QMainWindow):
                main = main.parent()
            if main and main.session.current_data is not None:
                main.session.current_data = self._preview_backup
                main._update_display()
            self._preview_backup = None
            self._preview_result = None

        if self._current_action:
            self.show_action(self._current_action)

    def set_expert_mode(self, expert):
        self._expert_mode = expert
        self.auto_msg.setVisible(not expert)
        if self._current_action:
            self.show_action(self._current_action)
        elif not expert:
            self.auto_msg.setText(
                "Modo AUTO\n\n"
                "Selecciona una accion de la toolbar\n"
                "o del menu y se aplicara con los\n"
                "parametros optimos automaticamente."
            )


from PyQt6.QtWidgets import QMainWindow
