"""
scripts_dialog.py
-----------------
Dialogo de gestion de scripts, estilo Siril.
Tabla con categoria, nombre, tipo. Botones para ejecutar,
editar, crear nuevo y abrir carpeta de scripts.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit, QFileDialog,
    QMessageBox, QGroupBox, QLineEdit,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..scripts import ScriptManager, parse_script, generate_script, ScriptInfo, ScriptStep


class ScriptsDialog(QDialog):

    def __init__(self, registry, session, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scripts")
        self.setMinimumSize(800, 550)

        self.registry = registry
        self.session = session

        self.manager = ScriptManager()
        self.manager.create_builtin_scripts()
        self.manager.scan()

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        header = QHBoxLayout()
        title = QLabel("Scripts")
        title.setStyleSheet(
            "font-size: 16px; font-weight: 700; color: #4A7FB5;"
        )
        header.addWidget(title)
        header.addStretch()

        dirs_label = QLabel(
            "Directorio: " + ", ".join(self.manager._dirs)
        )
        dirs_label.setObjectName("subtitle")
        dirs_label.setWordWrap(True)
        layout.addWidget(dirs_label)

        layout.addLayout(header)

        # Busqueda
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar scripts...")
        self.search_input.textChanged.connect(self._filter_table)
        search_row.addWidget(self.search_input)
        layout.addLayout(search_row)

        # Tabla
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Categoria", "Script", "Tipo", "Descripcion", "Pasos",
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
                padding: 4px; color: #E0E4EC;
            }
            QTableWidget::item:selected {
                background-color: #4A7FB5; color: white;
            }
            QTableWidget::item:alternate {
                background-color: #1E2233;
            }
            QHeaderView::section {
                background-color: #252540;
                color: #B0B8C8;
                border: 1px solid #2A2F45;
                padding: 4px; font-weight: 600;
            }
        """)
        self.table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.table.doubleClicked.connect(self._on_execute)
        layout.addWidget(self.table, stretch=1)

        # Botones
        btn_layout = QHBoxLayout()

        execute_btn = QPushButton("Ejecutar")
        execute_btn.setObjectName("primary")
        execute_btn.clicked.connect(self._on_execute)
        btn_layout.addWidget(execute_btn)

        view_btn = QPushButton("Ver/Editar")
        view_btn.clicked.connect(self._on_edit)
        btn_layout.addWidget(view_btn)

        new_btn = QPushButton("Nuevo script")
        new_btn.clicked.connect(self._on_new)
        btn_layout.addWidget(new_btn)

        import_btn = QPushButton("Importar .py/.abs")
        import_btn.clicked.connect(self._on_import)
        btn_layout.addWidget(import_btn)

        btn_layout.addStretch()

        folder_btn = QPushButton("Abrir carpeta")
        folder_btn.clicked.connect(self._on_open_folder)
        btn_layout.addWidget(folder_btn)

        refresh_btn = QPushButton("Refrescar")
        refresh_btn.clicked.connect(self._refresh)
        btn_layout.addWidget(refresh_btn)

        layout.addLayout(btn_layout)

        self._populate_table()

    def _populate_table(self):
        scripts = self.manager.get_all()
        self.table.setRowCount(len(scripts))

        for i, s in enumerate(scripts):
            items = [
                s.category,
                s.name,
                s.script_type.upper(),
                s.description[:50] + "..." if len(s.description) > 50 else s.description,
                str(len(s.steps)),
            ]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setFlags(
                    Qt.ItemFlag.ItemIsSelectable |
                    Qt.ItemFlag.ItemIsEnabled
                )
                item.setData(Qt.ItemDataRole.UserRole, s.filename)
                self.table.setItem(i, col, item)

    def _filter_table(self, text):
        text = text.lower()
        for row in range(self.table.rowCount()):
            match = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text in item.text().lower():
                    match = True
                    break
            self.table.setRowHidden(row, not match)

    def _get_selected_script(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(
                self, "Sin seleccion",
                "Selecciona un script de la tabla",
            )
            return None

        row = rows[0].row()
        item = self.table.item(row, 0)
        filename = item.data(Qt.ItemDataRole.UserRole)
        stem = filename.replace(".abs", "")
        return self.manager.get(stem)

    def _on_execute(self):
        script = self._get_selected_script()
        if not script:
            return

        if self.session.current_data is None:
            QMessageBox.information(
                self, "Sin imagen",
                "Abre una imagen primero antes de ejecutar un script",
            )
            return

        from ..scripts import execute_script
        from ..progress import ConsoleProgress

        try:
            results = execute_script(
                script, self.session, self.registry,
            )

            ok = sum(1 for r in results if r["ok"])
            total = len(results)

            QMessageBox.information(
                self, "Script completado",
                f"'{script.name}' ejecutado.\n"
                f"{ok}/{total} pasos completados correctamente.",
            )

            main = self.parent()
            if main and hasattr(main, '_update_display'):
                main._update_display()
                main.steps_panel.refresh(main.session)

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Error ejecutando script:\n{e}"
            )

    def _on_edit(self):
        script = self._get_selected_script()
        if not script:
            return

        dlg = ScriptEditorDialog(script, self.registry, self)
        if dlg.exec():
            self.manager.scan()
            self._populate_table()

    def _on_new(self):
        info = ScriptInfo(
            name="Nuevo Script",
            author="Usuario",
            category="Custom",
            steps=[],
        )
        dlg = ScriptEditorDialog(info, self.registry, self)
        if dlg.exec():
            self.manager.scan()
            self._populate_table()

    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Importar script", "",
            "Scripts (*.py *.abs);;Python (*.py);;ABS (*.abs);;Todos (*)",
        )
        if path:
            import shutil
            dest = self.manager._dirs[-1]
            shutil.copy2(path, dest)
            self.manager.scan()
            self._populate_table()

    def _on_open_folder(self):
        import subprocess
        folder = self.manager._dirs[-1]
        subprocess.Popen(f'explorer "{folder}"')

    def _refresh(self):
        self.manager.scan()
        self._populate_table()


class ScriptEditorDialog(QDialog):
    """Editor de scripts con preview de pasos."""

    def __init__(self, script_info, registry, parent=None):
        super().__init__(parent)
        self.setWindowTitle(
            f"Editor: {script_info.name}"
        )
        self.setMinimumSize(600, 500)
        self.script_info = script_info
        self.registry = registry

        layout = QVBoxLayout(self)

        info_label = QLabel(
            "Cada linea: action_id param1=valor1 param2=valor2\n"
            "Lineas con # son comentarios/metadatos."
        )
        info_label.setObjectName("subtitle")
        layout.addWidget(info_label)

        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 12))
        self.editor.setPlainText(generate_script(script_info))
        layout.addWidget(self.editor, stretch=1)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Guardar")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _save(self):
        text = self.editor.toPlainText()
        info = parse_script(text)
        info.filename = self.script_info.filename

        manager = ScriptManager()
        manager.save_script(info)

        QMessageBox.information(
            self, "Guardado",
            f"Script '{info.name}' guardado correctamente.",
        )
        self.accept()
