"""
assistant_panel.py
------------------
Panel visual del asistente inteligente.
Muestra diagnostico de la imagen con indicadores de color
y botones para aplicar las sugerencias directamente.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QScrollArea, QHBoxLayout, QFrame,
)
from PyQt6.QtCore import Qt

from .i18n import tr


SEVERITY_COLORS = {
    "critical": "#D94452",
    "warning": "#E6A817",
    "info": "#4A9BD9",
    "ok": "#4CAF6E",
}

SEVERITY_ICONS = {
    "critical": "!!",
    "warning": "!",
    "info": "i",
    "ok": "OK",
}


class SuggestionCard(QFrame):
    """Tarjeta individual de sugerencia."""

    def __init__(self, suggestion, parent=None):
        super().__init__(parent)
        self.suggestion = suggestion
        color = SEVERITY_COLORS.get(suggestion.severity, "#888")

        self.setStyleSheet(f"""
            SuggestionCard {{
                background-color: rgba({self._hex_to_rgb(color)}, 0.08);
                border: 1px solid rgba({self._hex_to_rgb(color)}, 0.3);
                border-left: 3px solid {color};
                border-radius: 6px;
                padding: 8px;
                margin: 2px 0;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        header = QHBoxLayout()
        badge = QLabel(SEVERITY_ICONS.get(suggestion.severity, "?"))
        badge.setFixedSize(22, 22)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet(f"""
            background-color: {color};
            color: white; border-radius: 11px;
            font-size: 13px; font-weight: 700;
        """)
        header.addWidget(badge)

        title = QLabel(suggestion.title)
        title.setWordWrap(True)
        title.setStyleSheet("font-weight: 600; font-size: 13px;")
        header.addWidget(title, stretch=1)
        layout.addLayout(header)

        desc = QLabel(suggestion.description)
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #8892A8; font-size: 13px;")
        layout.addWidget(desc)

        if suggestion.action_id:
            action_layout = QHBoxLayout()
            action_layout.addStretch()

            apply_btn = QPushButton(
                f"Aplicar: {suggestion.action_id}"
            )
            apply_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white; border: none;
                    border-radius: 4px; padding: 4px 12px;
                    font-size: 13px; font-weight: 600;
                }}
                QPushButton:hover {{ opacity: 0.9; }}
            """)
            apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            aid = suggestion.action_id
            apply_btn.clicked.connect(
                lambda ch, a=aid: self._apply(a)
            )
            action_layout.addWidget(apply_btn)
            layout.addLayout(action_layout)

    def _apply(self, action_id):
        main = self.parent()
        while main and not hasattr(main, '_execute_action'):
            main = main.parent()
        if main:
            main._execute_action(action_id)

    def _hex_to_rgb(self, hex_color):
        h = hex_color.lstrip('#')
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"{r}, {g}, {b}"


class AssistantPanel(QWidget):
    """Panel del asistente con analisis visual."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._suggestions = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel("Asistente")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()

        self.score_label = QLabel("")
        self.score_label.setStyleSheet(
            "font-size: 13px; font-weight: 700;"
        )
        header.addWidget(self.score_label)
        layout.addLayout(header)

        self.summary_label = QLabel(
            "Abre una imagen para analizar"
        )
        self.summary_label.setObjectName("subtitle")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        # Analyze button
        self.analyze_btn = QPushButton("Analizar imagen")
        self.analyze_btn.setObjectName("primary")
        self.analyze_btn.clicked.connect(self._analyze)
        layout.addWidget(self.analyze_btn)

        # Scroll area for suggestions
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 4, 0, 0)
        self.cards_layout.setSpacing(6)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.cards_container)

        layout.addWidget(scroll, stretch=1)

        # Apply all button
        self.apply_all_btn = QPushButton("Aplicar plan completo")
        self.apply_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF6E; color: white;
                border: none; border-radius: 5px;
                padding: 6px; font-weight: 600;
            }
            QPushButton:hover { background-color: #5BC07E; }
        """)
        self.apply_all_btn.clicked.connect(self._apply_all)
        self.apply_all_btn.setVisible(False)
        layout.addWidget(self.apply_all_btn)

    def _analyze(self):
        main = self.parent()
        while main and not hasattr(main, 'session'):
            main = main.parent()

        if not main or main.session.current_data is None:
            self.summary_label.setText("Abre una imagen primero")
            return

        from ..assistant import analyze_image
        suggestions = analyze_image(
            main.session.current_data, "post_stack"
        )
        self.show_suggestions(suggestions)

    def show_suggestions(self, suggestions):
        self._suggestions = suggestions

        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        problems = [
            s for s in suggestions
            if s.severity in ("critical", "warning")
        ]
        ok_count = sum(1 for s in suggestions if s.severity == "ok")
        total = len(suggestions)

        if not problems:
            color = "#4CAF6E"
            self.summary_label.setText(
                "La imagen esta en buen estado"
            )
        elif any(s.severity == "critical" for s in problems):
            color = "#D94452"
            self.summary_label.setText(
                f"{len(problems)} problemas detectados"
            )
        else:
            color = "#E6A817"
            self.summary_label.setText(
                f"{len(problems)} aspectos mejorables"
            )

        self.score_label.setText(f"{ok_count}/{total}")
        self.score_label.setStyleSheet(
            f"font-size: 13px; font-weight: 700; color: {color};"
        )

        for s in suggestions:
            card = SuggestionCard(s)
            self.cards_layout.addWidget(card)

        has_actions = any(s.action_id for s in problems)
        self.apply_all_btn.setVisible(has_actions)

    def _apply_all(self):
        main = self.parent()
        while main and not hasattr(main, '_execute_action'):
            main = main.parent()
        if not main:
            return

        for s in self._suggestions:
            if s.action_id and s.severity in ("critical", "warning"):
                try:
                    main._execute_action(s.action_id)
                except Exception:
                    pass
