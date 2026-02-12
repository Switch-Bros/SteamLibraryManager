# src/ui/auto_categorize_dialog.py

"""
Dialog for automatic game categorization.

This module provides a dialog that allows users to automatically categorize
their Steam games using various methods (tags, publisher, franchise, genre).
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QCheckBox,
    QRadioButton,
    QSpinBox,
    QPushButton,
    QFrame,
    QButtonGroup,
    QMessageBox,
)
from PyQt6.QtGui import QFont
from typing import Any, Callable
from src.utils.i18n import t
from src.config import config


class AutoCategorizeDialog(QDialog):
    """
    Dialog for configuring and starting automatic game categorization.

    This dialog allows users to select categorization methods, configure settings,
    and choose which games to apply the categorization to.

    Attributes:
        games (List): List of games to categorize (selected or uncategorized).
        all_games_count (int): Total number of games in the library.
        on_start (Callable): Callback function to execute when categorization starts.
        category_name (str | None): Name of the category being processed, if any.
        result (dict[str, Any] | None): Configuration result after dialog is accepted.
    """

    def __init__(self, parent, games: list, all_games_count: int, on_start: Callable, category_name: str | None = None):
        """
        Initializes the auto-categorize dialog.

        Args:
            parent: Parent widget.
            games (List): List of games to categorize (selected or uncategorized).
            all_games_count (int): Total number of games in the library.
            on_start (Callable): Callback function to execute when categorization starts.
            category_name (str | None): Name of the category being processed, if any.
        """
        super().__init__(parent)

        self.games = games
        self.all_games_count = all_games_count
        self.on_start = on_start
        self.category_name = category_name
        self.result: dict[str, Any] | None = None

        # Window setup
        self.setWindowTitle(t("ui.auto_categorize.title"))
        self.setMinimumWidth(550)
        self.setModal(True)

        self._create_ui()
        self._update_estimate()
        self._center_on_parent()

    def _center_on_parent(self):
        """Center this dialog relative to its parent window."""
        if self.parent():
            parent_geo = self.parent().geometry()
            self.move(
                parent_geo.x() + (parent_geo.width() - self.width()) // 2,
                parent_geo.y() + (parent_geo.height() - self.height()) // 2,
            )

    def _create_ui(self):
        """Initialize and lay out all UI components for the auto-categorize dialog."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel(t("ui.auto_categorize.header"))
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # === METHODS GROUP ===
        methods_group = QGroupBox(t("ui.auto_categorize.method_group"))
        methods_layout = QVBoxLayout()

        self.cb_tags = QCheckBox(t("ui.auto_categorize.option_tags"))
        self.cb_tags.setChecked(True)
        methods_layout.addWidget(self.cb_tags)

        self.cb_publisher = QCheckBox(t("ui.auto_categorize.by_publisher"))
        methods_layout.addWidget(self.cb_publisher)

        self.cb_franchise = QCheckBox(t("ui.auto_categorize.option_franchise"))
        methods_layout.addWidget(self.cb_franchise)

        self.cb_genre = QCheckBox(t("ui.auto_categorize.by_genre"))
        methods_layout.addWidget(self.cb_genre)

        methods_group.setLayout(methods_layout)
        layout.addWidget(methods_group)

        # === TAGS SETTINGS GROUP ===
        self.tags_group = QGroupBox(t("ui.auto_categorize.settings"))
        tags_layout = QVBoxLayout()

        # Tags per game
        tags_per_game_layout = QHBoxLayout()
        tags_per_game_layout.addWidget(QLabel(t("ui.auto_categorize.tags_per_game") + ":"))
        self.tags_count_spin = QSpinBox()
        self.tags_count_spin.setMinimum(1)
        self.tags_count_spin.setMaximum(50)  # Increased limit
        self.tags_count_spin.setValue(config.TAGS_PER_GAME)  # Load from config
        tags_per_game_layout.addWidget(self.tags_count_spin)
        tags_per_game_layout.addStretch()
        tags_layout.addLayout(tags_per_game_layout)

        # Ignore common tags
        self.cb_ignore_common = QCheckBox(t("ui.auto_categorize.option_ignore_common"))
        self.cb_ignore_common.setChecked(True)
        tags_layout.addWidget(self.cb_ignore_common)

        self.tags_group.setLayout(tags_layout)
        layout.addWidget(self.tags_group)

        # === APPLY TO GROUP ===
        apply_group = QGroupBox(t("ui.auto_categorize.apply_group"))
        apply_layout = QVBoxLayout()

        self.scope_group = QButtonGroup(self)

        # Determine label for "Selected" option
        if self.category_name:
            scope_text = t("ui.auto_categorize.scope_category", name=self.category_name, count=len(self.games))
        else:
            # Use generic "Selected Games" label if no category name is provided
            scope_text = t("ui.auto_categorize.scope_selected", count=len(self.games))

        self.rb_selected = QRadioButton(scope_text)
        self.rb_selected.setChecked(True)
        self.scope_group.addButton(self.rb_selected)
        apply_layout.addWidget(self.rb_selected)

        self.rb_all = QRadioButton(t("ui.auto_categorize.scope_all", count=self.all_games_count))
        self.scope_group.addButton(self.rb_all)
        apply_layout.addWidget(self.rb_all)

        # If "All Games" are selected, pre-select "All" option to avoid confusion
        if len(self.games) == self.all_games_count:
            self.rb_all.setChecked(True)

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
        warning = QLabel(t("ui.auto_categorize.warning_backup"))
        warning.setStyleSheet("color: orange;")
        layout.addWidget(warning)

        # === BUTTONS ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton(t("common.cancel"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        start_btn = QPushButton(t("ui.auto_categorize.start"))
        start_btn.setDefault(True)
        start_btn.clicked.connect(self._start)
        button_layout.addWidget(start_btn)

        layout.addLayout(button_layout)

        # === CONNECT SIGNALS (After all widgets are created) ===
        # noinspection DuplicatedCode
        self.cb_tags.toggled.connect(self._update_estimate)
        self.cb_publisher.toggled.connect(self._update_estimate)
        self.cb_franchise.toggled.connect(self._update_estimate)
        self.cb_genre.toggled.connect(self._update_estimate)
        self.tags_count_spin.valueChanged.connect(self._update_estimate)
        self.rb_selected.toggled.connect(self._update_estimate)
        self.rb_all.toggled.connect(self._update_estimate)

    def _get_selected_methods(self) -> list[str]:
        """
        Gets the list of selected categorization methods.

        Returns:
            list[str]: A list of method names ('tags', 'publisher', 'franchise', 'genre').
        """
        methods = []
        if self.cb_tags.isChecked():
            methods.append("tags")
        if self.cb_publisher.isChecked():
            methods.append("publisher")
        if self.cb_franchise.isChecked():
            methods.append("franchise")
        if self.cb_genre.isChecked():
            methods.append("genre")
        return methods

    def _update_estimate(self):
        """
        Updates the time estimate label based on selected options.

        This method calculates the estimated processing time based on the number
        of games and selected categorization methods.
        """
        # Safety check if called before UI is fully initialized
        if not hasattr(self, "estimate_label") or not hasattr(self, "tags_group"):
            return

        self.tags_group.setVisible(self.cb_tags.isChecked())

        game_count = self.all_games_count if self.rb_all.isChecked() else len(self.games)
        selected_methods = self._get_selected_methods()

        if "tags" in selected_methods:
            seconds = int(game_count * 1.5)
            minutes = seconds // 60
            if minutes > 0:
                time_str = t("ui.auto_categorize.estimate_minutes", count=minutes)
            else:
                time_str = t("ui.auto_categorize.estimate_seconds", count=seconds)
        else:
            time_str = t("ui.auto_categorize.estimate_instant")

        self.estimate_label.setText(
            t("ui.auto_categorize.estimate_label", time=time_str, games=game_count, methods=len(selected_methods))
        )

    def _start(self):
        """
        Starts the auto-categorization process.

        This method validates the selection, builds the configuration result,
        and calls the on_start callback.
        """
        selected_methods = self._get_selected_methods()

        if not selected_methods:
            QMessageBox.warning(self, t("ui.auto_categorize.no_method_title"), t("ui.auto_categorize.error_no_method"))
            return

        self.result = {
            "methods": selected_methods,
            "scope": "all" if self.rb_all.isChecked() else "selected",
            "tags_count": self.tags_count_spin.value(),
            "ignore_common": self.cb_ignore_common.isChecked(),
        }

        self.accept()
        if self.on_start:
            self.on_start(self.result)

    def get_result(self) -> dict[str, Any] | None:
        """
        Gets the configuration result after the dialog is accepted.

        Returns:
            dict[str, Any] | None: The configuration dictionary, or None if canceled.
        """
        return self.result
