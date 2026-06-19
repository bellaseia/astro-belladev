"""
planner_dialog.py
-----------------
Dialogo del planificador de sesion con deteccion automatica
de ubicacion y tabla de targets visibles.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QDoubleSpinBox, QSpinBox, QPushButton, QGroupBox,
    QFormLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ..planner import (
    ObserverLocation, EquipmentProfile,
    suggest_targets, calculate_visibility,
)
from ..catalog import AstroCatalog


class PlannerDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Planificador de Sesion")
        self.setMinimumSize(750, 600)

        self.catalog = AstroCatalog()
        self.catalog.load_builtin()

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # === UBICACION ===
        loc_group = QGroupBox("Ubicacion del observador")
        loc_layout = QFormLayout(loc_group)

        self.lat_spin = QDoubleSpinBox()
        self.lat_spin.setRange(-90, 90)
        self.lat_spin.setDecimals(2)
        self.lat_spin.setValue(38.0)
        self.lat_spin.setSuffix(" N")
        loc_layout.addRow("Latitud:", self.lat_spin)

        self.lon_spin = QDoubleSpinBox()
        self.lon_spin.setRange(-180, 180)
        self.lon_spin.setDecimals(2)
        self.lon_spin.setValue(-1.13)
        self.lon_spin.setSuffix(" E")
        loc_layout.addRow("Longitud:", self.lon_spin)

        self.bortle_spin = QSpinBox()
        self.bortle_spin.setRange(1, 9)
        self.bortle_spin.setValue(5)
        loc_layout.addRow("Bortle:", self.bortle_spin)

        btn_row = QHBoxLayout()
        auto_btn = QPushButton("Detectar ubicacion")
        auto_btn.setObjectName("primary")
        auto_btn.clicked.connect(self._auto_detect_location)
        btn_row.addWidget(auto_btn)

        calc_btn = QPushButton("Calcular targets")
        calc_btn.clicked.connect(self._calculate)
        btn_row.addWidget(calc_btn)
        btn_row.addStretch()

        loc_layout.addRow(btn_row)
        layout.addWidget(loc_group)

        # === INFO ===
        self.info_label = QLabel("")
        self.info_label.setObjectName("subtitle")
        layout.addWidget(self.info_label)

        # === TABLA ===
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "#", "Objeto", "Nombre", "Alt. max", "Horas", "Score"
        ])
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1A1E30;
                color: #E0E4EC;
                border: 1px solid #2A2F45;
                gridline-color: #2A2F45;
            }
            QTableWidget::item {
                padding: 4px;
                color: #E0E4EC;
            }
            QTableWidget::item:selected {
                background-color: #4A7FB5;
                color: white;
            }
            QTableWidget::item:alternate {
                background-color: #1E2233;
            }
            QHeaderView::section {
                background-color: #252540;
                color: #B0B8C8;
                border: 1px solid #2A2F45;
                padding: 4px;
                font-weight: 600;
            }
        """)
        self.table.selectionModel().selectionChanged.connect(
            self._on_selection_changed
        )
        layout.addWidget(self.table, stretch=1)

        # Preview de imagen del target
        from PyQt6.QtWidgets import QFrame
        preview_frame = QFrame()
        preview_frame.setFixedHeight(180)
        preview_frame.setStyleSheet(
            "QFrame { border: 1px solid #2A2F45; border-radius: 6px; }"
        )
        preview_layout = QHBoxLayout(preview_frame)
        preview_layout.setContentsMargins(8, 4, 8, 4)

        self.preview_label = QLabel()
        self.preview_label.setFixedSize(200, 160)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet(
            "background: #0A0C14; border-radius: 4px;"
        )
        self.preview_label.setText("Selecciona un target")
        preview_layout.addWidget(self.preview_label)

        self.target_info = QLabel("")
        self.target_info.setWordWrap(True)
        self.target_info.setStyleSheet("font-size: 13px;")
        preview_layout.addWidget(self.target_info, stretch=1)

        layout.addWidget(preview_frame)

        # Auto-calcular al abrir
        self._calculate()

    def _auto_detect_location(self):
        """Detecta ubicacion por IP (sin GPS)."""
        try:
            import urllib.request
            import json
            url = "http://ip-api.com/json/?fields=lat,lon,city,country"
            req = urllib.request.Request(url, headers={
                "User-Agent": "AstroBellaDev/1.1"
            })
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())

            lat = data.get("lat", 38.0)
            lon = data.get("lon", -1.13)
            city = data.get("city", "")
            country = data.get("country", "")

            self.lat_spin.setValue(lat)
            self.lon_spin.setValue(lon)
            self.info_label.setText(
                f"Ubicacion detectada: {city}, {country} "
                f"({lat:.2f}, {lon:.2f})"
            )
            self._calculate()

        except Exception as e:
            QMessageBox.warning(
                self, "Error",
                f"No se pudo detectar la ubicacion:\n{e}\n\n"
                "Introduce las coordenadas manualmente."
            )

    def _calculate(self):
        """Calcula targets visibles y llena la tabla."""
        location = ObserverLocation(
            latitude=self.lat_spin.value(),
            longitude=self.lon_spin.value(),
            name="Usuario",
        )

        targets = suggest_targets(
            self.catalog, location, top_n=30
        )

        self.table.setRowCount(len(targets))

        for i, t in enumerate(targets):
            name = t.common_name or t.object_name

            items = [
                str(i + 1),
                t.object_id,
                name,
                f"{t.max_altitude_deg:.0f} deg",
                f"{t.hours_above_30deg:.1f}h",
                f"{t.score:.0f}",
            ]

            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setFlags(
                    Qt.ItemFlag.ItemIsSelectable |
                    Qt.ItemFlag.ItemIsEnabled
                )

                if t.is_circumpolar:
                    item.setForeground(QColor("#4A9BD9"))
                if t.score > 100:
                    item.setForeground(QColor("#4CAF6E"))

                self.table.setItem(i, col, item)

        total = len(calculate_visibility(
            self.catalog, location, min_altitude=30
        ))
        self.info_label.setText(
            f"{total} objetos visibles (>30 deg) | "
            f"Top {len(targets)} mostrados | "
            f"Lat {self.lat_spin.value():.1f}, "
            f"Lon {self.lon_spin.value():.1f}, "
            f"Bortle {self.bortle_spin.value()}"
        )

    def _on_selection_changed(self):
        """Al seleccionar un target, mostrar preview e info."""
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return

        row = rows[0].row()
        obj_id = self.table.item(row, 1).text()
        obj = self.catalog.get(obj_id)
        if obj is None:
            return

        # Info del objeto
        name = obj.common_name or obj.name
        info = (
            f"<b style='font-size:15px;'>{obj.id}</b><br>"
            f"<span style='color:#4A7FB5;font-size:14px;'>"
            f"{name}</span><br><br>"
            f"Tipo: {obj.obj_type}<br>"
            f"Magnitud: {obj.magnitude}<br>"
            f"Tamano: {obj.size_arcmin} arcmin<br>"
            f"Constelacion: {obj.constellation}<br>"
            f"RA: {obj.ra_hms}<br>"
            f"Dec: {obj.dec_dms}<br>"
        )
        if obj.alt_ids:
            info += f"<br>Otros IDs: {', '.join(obj.alt_ids)}"
        self.target_info.setText(info)

        # Descargar thumbnail de Aladin/ESA
        self._load_preview(obj)

    def _load_preview(self, obj):
        """Descarga thumbnail del objeto desde Aladin Sky Atlas."""
        import urllib.request
        import ssl
        from PyQt6.QtGui import QPixmap

        self.preview_label.setText("Cargando...")
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()

        try:
            fov = max(obj.size_arcmin / 60.0 * 2, 0.5)
            url = (
                f"https://alasky.cds.unistra.fr/hips-image-services"
                f"/hips2fits?hips=CDS%2FP%2FDSS2%2Fcolor"
                f"&ra={obj.ra}&dec={obj.dec}"
                f"&fov={fov}&width=200&height=160"
                f"&projection=TAN&format=jpg"
            )

            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(url, headers={
                "User-Agent": "AstroBellaDev/1.1"
            })
            with urllib.request.urlopen(
                req, timeout=10, context=ctx
            ) as resp:
                data = resp.read()

            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if not pixmap.isNull():
                self.preview_label.setPixmap(
                    pixmap.scaled(
                        200, 160,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                self.preview_label.setText("Sin preview")

        except Exception:
            self.preview_label.setText("Sin conexion")
