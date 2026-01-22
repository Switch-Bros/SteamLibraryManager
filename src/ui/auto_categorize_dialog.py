"""
Auto-Categorize Dialog - Fully Localized
Speichern als: src/ui/auto_categorize_dialog.py
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QCheckBox, QRadioButton, QSpinBox, QPushButton, QFrame,
    QButtonGroup, QMessageBox
)
from PyQt6.QtGui import QFont
from typing import List, Callable, Optional, Dict, Any
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
        self.result: Optional[Dict[str, Any]] = None

        # Window setup
        self.setWindowTitle(t('ui.auto_categorize.title'))
        self.setMinimumWidth(550)
        self.setModal(True)

        self._create_ui()
        self._update_estimate()
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
        title = QLabel(t('ui.auto_categorize.header'))
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # === METHODS GROUP ===
        methods_group = QGroupBox(t('ui.auto_categorize.method_group'))
        methods_layout = QVBoxLayout()

        self.cb_tags = QCheckBox(t('ui.auto_categorize.option_tags'))
        self.cb_tags.setChecked(True)
        self.cb_tags.toggled.connect(self._update_estimate)
        methods_layout.addWidget(self.cb_tags)

        self.cb_publisher = QCheckBox(t('ui.auto_categorize.by_publisher'))
        self.cb_publisher.toggled.connect(self._update_estimate)
        methods_layout.addWidget(self.cb_publisher)

        self.cb_franchise = QCheckBox(t('ui.auto_categorize.option_franchise'))
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
        self.cb_ignore_common = QCheckBox(t('ui.auto_categorize.option_ignore_common'))
        self.cb_ignore_common.setChecked(True)
        tags_layout.addWidget(self.cb_ignore_common)

        self.tags_group.setLayout(tags_layout)
        layout.addWidget(self.tags_group)

        # === APPLY TO GROUP ===
        apply_group = QGroupBox(t('ui.auto_categorize.apply_group'))
        apply_layout = QVBoxLayout()

        self.scope_group = QButtonGroup(self)

        if self.category_name:
            scope_text = t('ui.auto_categorize.scope_category', name=self.category_name, count=len(self.games))
        else:
            scope_text = t('ui.auto_categorize.scope_uncategorized', count=len(self.games))

        self.rb_selected = QRadioButton(scope_text)
        self.rb_selected.setChecked(True)
        self.rb_selected.toggled.connect(self._update_estimate)
        self.scope_group.addButton(self.rb_selected)
        apply_layout.addWidget(self.rb_selected)

        self.rb_all = QRadioButton(t('ui.auto_categorize.scope_all', count=self.all_games_count))
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
        warning = QLabel(t('ui.auto_categorize.warning_backup'))
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

    def _get_selected_methods(self) -> List[str]:
        """FIX: Hilfsmethode zur Vermeidung von Code-Duplikaten"""
        methods = []
        if self.cb_tags.isChecked(): methods.append('tags')
        if self.cb_publisher.isChecked(): methods.append('publisher')
        if self.cb_franchise.isChecked(): methods.append('franchise')
        if self.cb_genre.isChecked(): methods.append('genre')
        return methods

    def _update_estimate(self):
        """Update time estimate"""
        self.tags_group.setVisible(self.cb_tags.isChecked())

        game_count = self.all_games_count if self.rb_all.isChecked() else len(self.games)
        selected_methods = self._get_selected_methods()

        if 'tags' in selected_methods:
            seconds = int(game_count * 1.5)
            minutes = seconds // 60
            if minutes > 0:
                time_str = t('ui.auto_categorize.estimate_minutes', count=minutes)
            else:
                time_str = t('ui.auto_categorize.estimate_seconds', count=seconds)
        else:
            time_str = t('ui.auto_categorize.estimate_instant')

        self.estimate_label.setText(
            t('ui.auto_categorize.estimate_label', time=time_str, games=game_count, methods=len(selected_methods))
        )

    def _start(self):
        """Start auto-categorization"""
        selected_methods = self._get_selected_methods()

        if not selected_methods:
            QMessageBox.warning(
                self,
                t('ui.auto_categorize.no_method_title'),
                t('ui.auto_categorize.error_no_method')
            )
            return

        self.result = {
            'methods': selected_methods,
            'scope': 'all' if self.rb_all.isChecked() else 'selected',
            'tags_count': self.tags_count_spin.value(),
            'ignore_common': self.cb_ignore_common.isChecked()
        }

        self.accept()
        if self.on_start:
            self.on_start(self.result)

    def get_result(self) -> Optional[Dict[str, Any]]:
        return self.result