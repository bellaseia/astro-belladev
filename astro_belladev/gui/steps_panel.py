"""
steps_panel.py
--------------
Panel izquierdo: lista de pasos aplicados con su estado.
Permite seleccionar un paso para ver sus parametros
y deshacer hasta ese punto.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QHBoxLayout,
)
from PyQt6.QtCore import Qt


class StepsPanel(QWidget):
    """Panel con la lista de pasos del pipeline aplicados."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        title = QLabel("Pipeline")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(title)

        self.step_list = QListWidget()
        # Styling comes from theme.py QListWidget rules
        layout.addWidget(self.step_list, stretch=1)

        # Info del paso seleccionado
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setObjectName("subtitle")
        layout.addWidget(self.info_label)

        # Botones
        btn_layout = QHBoxLayout()
        undo_btn = QPushButton("Deshacer")
        undo_btn.clicked.connect(self._undo_to_selected)
        btn_layout.addWidget(undo_btn)
        layout.addLayout(btn_layout)

        self._add_initial_message()

    def _add_initial_message(self):
        item = QListWidgetItem("  Abre una imagen (Ctrl+O)")
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.step_list.addItem(item)

    def refresh(self, session):
        """Actualiza la lista con el historial de la sesion."""
        self.step_list.clear()

        if session.current_data is None:
            self._add_initial_message()
            return

        # Paso 0: imagen cargada
        source = session.metadata.get("source", "imagen")
        item = QListWidgetItem(f"  [OK] Cargada")
        item.setToolTip(str(source))
        self.step_list.addItem(item)

        # Pasos del historial
        for record in session.get_history():
            text = f"  [OK] {record.action_name}"
            item = QListWidgetItem(text)
            params_str = ", ".join(f"{k}={v}" for k, v in record.params.items())
            item.setToolTip(f"{record.action_name}\n{params_str}\n{record.elapsed_seconds:.2f}s")
            self.step_list.addItem(item)

        # Info
        undo_count = session.undo_count()
        self.info_label.setText(
            f"{len(session.get_history())} pasos | "
            f"Undo: {undo_count}"
        )

    def _undo_to_selected(self):
        """Deshace el ultimo paso."""
        main = self.parent()
        while main and not hasattr(main, '_undo'):
            main = main.parent()
        if main:
            main._undo()
