"""
Auto-Categorize Dialog - PyQt6 Version mit Checkboxen für mehrere Methoden!

Speichern als: src/ui/auto_categorize_dialog.py
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QCheckBox, QRadioButton, QSpinBox, QPushButton, QFrame,
    QButtonGroup
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from typing import List, Callable, Optional
from src.utils.i18n import t


class AutoCategorizeDialog(QDialog):
    """Dialog für Auto-Kategorisierung"""

    def __init__(self, parent, games: List,
                 all_games_count: int,
                 on_start: Callable,
                 category_name: Optional[str] = None):
        super().__init__(parent)

        self.games = games
        self.all_games_count = all_games_count
        self.on_start = on_start
        self.category_name = category_name
        self.result = None

        # Window setup
        self.setWindowTitle(t('ui.auto_categorize.title'))
        self.setMinimumWidth(550)
        self.setModal(True)

        self._create_ui()
        self._update_estimate()

        # Center window
        self._center_on_parent()

    def _center_on_parent(self):
        """Center dialog on parent window"""
        if self.parent():
            parent_geo = self.parent().geometry()
            self.move(
                parent_geo.x() + (parent_geo.width() - self.width()) // 2,
                parent_geo.y() + (parent_geo.height() - self.height()) // 2
            )

    def _create_ui(self):
        """Create UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel(f"🏷️ {t('ui.auto_categorize.title')}")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # === METHODS GROUP ===
        methods_group = QGroupBox(t('ui.auto_categorize.method') + " (select multiple)")
        methods_layout = QVBoxLayout()

        self.cb_tags = QCheckBox(f"{t('ui.auto_categorize.by_tags')} (Recommended)")
        self.cb_tags.setChecked(True)
        self.cb_tags.toggled.connect(self._update_estimate)
        methods_layout.addWidget(self.cb_tags)

        self.cb_publisher = QCheckBox(t('ui.auto_categorize.by_publisher'))
        self.cb_publisher.toggled.connect(self._update_estimate)
        methods_layout.addWidget(self.cb_publisher)

        self.cb_franchise = QCheckBox(f"{t('ui.auto_categorize.by_franchise')} (LEGO, AC, etc.)")
        self.cb_franchise.toggled.connect(self._update_estimate)
        methods_layout.addWidget(self.cb_franchise)

        self.cb_genre = QCheckBox(t('ui.auto_categorize.by_genre'))
        self.cb_genre.toggled.connect(self._update_estimate)
        methods_layout.addWidget(self.cb_genre)

        methods_group.setLayout(methods_layout)
        layout.addWidget(methods_group)

        # === TAGS SETTINGS GROUP ===
        self.tags_group = QGroupBox(t('ui.auto_categorize.settings'))
        tags_layout = QVBoxLayout()

        # Tags per game
        tags_per_game_layout = QHBoxLayout()
        tags_per_game_layout.addWidget(QLabel(t('ui.auto_categorize.tags_per_game') + ":"))
        self.tags_count_spin = QSpinBox()
        self.tags_count_spin.setMinimum(1)
        self.tags_count_spin.setMaximum(20)
        self.tags_count_spin.setValue(13)
        self.tags_count_spin.valueChanged.connect(self._update_estimate)
        tags_per_game_layout.addWidget(self.tags_count_spin)
        tags_per_game_layout.addStretch()
        tags_layout.addLayout(tags_per_game_layout)

        # Ignore common tags
        self.cb_ignore_common = QCheckBox(t('ui.auto_categorize.ignore_common') + " (Singleplayer, Multiplayer, Controller, etc.)")
        self.cb_ignore_common.setChecked(True)
        tags_layout.addWidget(self.cb_ignore_common)

        self.tags_group.setLayout(tags_layout)
        layout.addWidget(self.tags_group)

        # === APPLY TO GROUP ===
        apply_group = QGroupBox("Apply to")
        apply_layout = QVBoxLayout()

        self.scope_group = QButtonGroup(self)

        if self.category_name:
            scope_text = f"Selected category: {self.category_name} ({len(self.games)} games)"
        else:
            scope_text = f"{t('ui.categories.uncategorized')} ({len(self.games)} games)"

        self.rb_selected = QRadioButton(scope_text)
        self.rb_selected.setChecked(True)
        self.rb_selected.toggled.connect(self._update_estimate)
        self.scope_group.addButton(self.rb_selected)
        apply_layout.addWidget(self.rb_selected)

        self.rb_all = QRadioButton(f"{t('ui.categories.all_games')} ({self.all_games_count} games)")
        self.rb_all.toggled.connect(self._update_estimate)
        self.scope_group.addButton(self.rb_all)
        apply_layout.addWidget(self.rb_all)

        apply_group.setLayout(apply_layout)
        layout.addWidget(apply_group)

        # === SEPARATOR ===
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # === ESTIMATE LABEL ===
        self.estimate_label = QLabel()
        self.estimate_label.setWordWrap(True)
        self.estimate_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.estimate_label)

        # === WARNING ===
        warning = QLabel("⚠️ " + t('ui.dialogs.backup_created').split(' at ')[0])
        warning.setStyleSheet("color: orange;")
        layout.addWidget(warning)

        # === BUTTONS ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton(t('ui.auto_categorize.cancel'))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        start_btn = QPushButton(t('ui.auto_categorize.start'))
        start_btn.setDefault(True)
        start_btn.clicked.connect(self._start)
        button_layout.addWidget(start_btn)

        layout.addLayout(button_layout)

    def _update_estimate(self):
        """Update time estimate"""
        # Show/hide tags settings
        self.tags_group.setVisible(self.cb_tags.isChecked())

        # Calculate game count
        game_count = self.all_games_count if self.rb_all.isChecked() else len(self.games)

        # Count selected methods
        selected_methods = []
        if self.cb_tags.isChecked():
            selected_methods.append('tags')
        if self.cb_publisher.isChecked():
            selected_methods.append('publisher')
        if self.cb_franchise.isChecked():
            selected_methods.append('franchise')
        if self.cb_genre.isChecked():
            selected_methods.append('genre')

        # Estimate time (1.5s per game for tags, instant for others)
        if 'tags' in selected_methods:
            seconds = int(game_count * 1.5)
            minutes = seconds // 60
            if minutes > 0:
                time_str = f"~{minutes} minute{'s' if minutes != 1 else ''}"
            else:
                time_str = f"~{seconds} seconds"
        else:
            time_str = "< 1 second"

        methods_text = f"{len(selected_methods)} method(s) selected" if selected_methods else "No methods selected"

        self.estimate_label.setText(
            f"Estimated time: {time_str}\n"
            f"({game_count} games, {methods_text})"
        )

    def _start(self):
        """Start auto-categorization"""
        # Get selected methods
        selected_methods = []
        if self.cb_tags.isChecked():
            selected_methods.append('tags')
        if self.cb_publisher.isChecked():
            selected_methods.append('publisher')
        if self.cb_franchise.isChecked():
            selected_methods.append('franchise')
        if self.cb_genre.isChecked():
            selected_methods.append('genre')

        # Validation
        if not selected_methods:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "No Method Selected",
                "Please select at least one categorization method!"
            )
            return

        # Build result
        self.result = {
            'methods': selected_methods,
            'scope': 'all' if self.rb_all.isChecked() else 'selected',
            'tags_count': self.tags_count_spin.value(),
            'ignore_common': self.cb_ignore_common.isChecked()
        }

        self.accept()

        # Call callback
        if self.on_start:
            self.on_start(self.result)

    def get_result(self):
        """Get dialog result"""
        return self.result