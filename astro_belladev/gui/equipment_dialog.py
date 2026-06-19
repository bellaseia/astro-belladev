"""
equipment_dialog.py
-------------------
Dialogo para configurar el perfil de equipo.
Muestra calculos en tiempo real de pixel scale, FOV, etc.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QDoubleSpinBox, QSpinBox, QComboBox, QPushButton,
    QGroupBox, QFormLayout, QFrame,
)
from PyQt6.QtCore import Qt

from ..planner import EquipmentProfile


class EquipmentDialog(QDialog):

    def __init__(self, profile=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Perfil de Equipo")
        self.setMinimumWidth(480)
        self.profile = profile or EquipmentProfile()

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Telescopio
        scope_group = QGroupBox("Telescopio")
        scope_layout = QFormLayout(scope_group)

        self.focal_spin = QDoubleSpinBox()
        self.focal_spin.setRange(50, 10000)
        self.focal_spin.setValue(self.profile.telescope_focal_mm)
        self.focal_spin.setSuffix(" mm")
        self.focal_spin.valueChanged.connect(self._update_calcs)
        scope_layout.addRow("Focal:", self.focal_spin)

        self.aperture_spin = QDoubleSpinBox()
        self.aperture_spin.setRange(10, 2000)
        self.aperture_spin.setValue(self.profile.telescope_aperture_mm)
        self.aperture_spin.setSuffix(" mm")
        self.aperture_spin.valueChanged.connect(self._update_calcs)
        scope_layout.addRow("Apertura:", self.aperture_spin)

        layout.addWidget(scope_group)

        # Camara
        cam_group = QGroupBox("Camara")
        cam_layout = QFormLayout(cam_group)

        self.pixel_spin = QDoubleSpinBox()
        self.pixel_spin.setRange(0.5, 20)
        self.pixel_spin.setDecimals(2)
        self.pixel_spin.setValue(self.profile.camera_pixel_um)
        self.pixel_spin.setSuffix(" um")
        self.pixel_spin.valueChanged.connect(self._update_calcs)
        cam_layout.addRow("Pixel size:", self.pixel_spin)

        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 100000)
        self.width_spin.setValue(self.profile.camera_width_px)
        self.width_spin.setSuffix(" px")
        self.width_spin.valueChanged.connect(self._update_calcs)
        cam_layout.addRow("Ancho:", self.width_spin)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(100, 100000)
        self.height_spin.setValue(self.profile.camera_height_px)
        self.height_spin.setSuffix(" px")
        self.height_spin.valueChanged.connect(self._update_calcs)
        cam_layout.addRow("Alto:", self.height_spin)

        layout.addWidget(cam_group)

        # Condiciones
        cond_group = QGroupBox("Condiciones")
        cond_layout = QFormLayout(cond_group)

        self.bortle_spin = QSpinBox()
        self.bortle_spin.setRange(1, 9)
        self.bortle_spin.setValue(self.profile.bortle_class)
        self.bortle_spin.valueChanged.connect(self._update_calcs)
        cond_layout.addRow("Escala Bortle:", self.bortle_spin)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "broadband", "Ha", "OIII", "SII", "LRGB"
        ])
        self.filter_combo.setCurrentText(self.profile.filter_type)
        cond_layout.addRow("Filtro:", self.filter_combo)

        layout.addWidget(cond_group)

        # Calculos
        calc_frame = QFrame()
        calc_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(74, 127, 181, 0.1);
                border: 1px solid rgba(74, 127, 181, 0.3);
                border-radius: 8px; padding: 12px;
            }
        """)
        calc_layout = QVBoxLayout(calc_frame)

        calc_title = QLabel("Calculos")
        calc_title.setStyleSheet(
            "font-weight: 700; color: #4A7FB5; font-size: 13px;"
        )
        calc_layout.addWidget(calc_title)

        self.calc_labels = {}
        for name in [
            "Pixel Scale", "FOV", "Focal Ratio",
            "Muestreo", "Exposicion sugerida"
        ]:
            lbl = QLabel("")
            lbl.setStyleSheet("font-size: 12px; padding: 2px 0;")
            calc_layout.addWidget(lbl)
            self.calc_labels[name] = lbl

        layout.addWidget(calc_frame)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("Guardar")
        ok_btn.setObjectName("primary")
        ok_btn.clicked.connect(self._save_and_accept)
        btn_layout.addWidget(ok_btn)

        layout.addLayout(btn_layout)

        self._update_calcs()

    def _update_calcs(self):
        p = EquipmentProfile(
            telescope_focal_mm=self.focal_spin.value(),
            telescope_aperture_mm=self.aperture_spin.value(),
            camera_pixel_um=self.pixel_spin.value(),
            camera_width_px=self.width_spin.value(),
            camera_height_px=self.height_spin.value(),
            bortle_class=self.bortle_spin.value(),
        )

        self.calc_labels["Pixel Scale"].setText(
            f"Pixel Scale: {p.pixel_scale_arcsec:.2f} arcsec/px"
        )
        self.calc_labels["FOV"].setText(
            f"FOV: {p.fov_width_arcmin:.0f}' x "
            f"{p.fov_height_arcmin:.0f}' "
            f"({p.fov_width_deg:.1f} x {p.fov_height_deg:.1f} deg)"
        )
        self.calc_labels["Focal Ratio"].setText(
            f"Focal Ratio: f/{p.focal_ratio:.1f}"
        )
        self.calc_labels["Muestreo"].setText(
            f"Muestreo: {p.resolution_rating}"
        )
        self.calc_labels["Exposicion sugerida"].setText(
            f"Exposicion sugerida: {p.suggested_exposure()}s "
            f"(Bortle {p.bortle_class})"
        )

    def _save_and_accept(self):
        self.profile = EquipmentProfile(
            telescope_focal_mm=self.focal_spin.value(),
            telescope_aperture_mm=self.aperture_spin.value(),
            camera_pixel_um=self.pixel_spin.value(),
            camera_width_px=self.width_spin.value(),
            camera_height_px=self.height_spin.value(),
            bortle_class=self.bortle_spin.value(),
            filter_type=self.filter_combo.currentText(),
        )
        self.accept()

    def get_profile(self):
        return self.profile
