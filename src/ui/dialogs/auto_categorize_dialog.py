# src/ui/auto_categorize_dialog.py

"""
Dialog for automatic game categorization.

This module provides a dialog that allows users to automatically categorize
their Steam games using various methods (tags, publisher, franchise, genre,
curator, etc.) and save/load presets for recurring configurations.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QCheckBox,
    QRadioButton,
    QSpinBox,
    QPushButton,
    QFrame,
    QButtonGroup,
    QMessageBox,
    QLineEdit,
    QComboBox,
    QInputDialog,
    QWidget,
    QListWidget,
    QMenu,
)

from src.config import config
from src.services.autocat_preset_manager import AutoCatPreset, AutoCatPresetManager
from src.ui.utils.font_helper import FontHelper
from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.auto_categorize_dialog")

_CURATOR_HISTORY_FILE: Path = config.DATA_DIR / "curator_history.json"
_MAX_CURATOR_HISTORY = 20


class AutoCategorizeDialog(QDialog):
    """Dialog for configuring and starting automatic game categorization.

    Supports method selection, curator configuration, and preset management.

    Attributes:
        games: List of games to categorize (selected or uncategorized).
        all_games_count: Total number of games in the library.
        on_start: Callback function to execute when categorization starts.
        category_name: Name of the category being processed, if any.
        result: Configuration result after dialog is accepted.
    """

    def __init__(
        self,
        parent: QWidget | None,
        games: list,
        all_games_count: int,
        on_start: Callable,
        category_name: str | None = None,
    ) -> None:
        """Initialize the auto-categorize dialog.

        Args:
            parent: Parent widget.
            games: List of games to categorize (selected or uncategorized).
            all_games_count: Total number of games in the library.
            on_start: Callback function to execute when categorization starts.
            category_name: Name of the category being processed, if any.
        """
        super().__init__(parent)

        self.games = games
        self.all_games_count = all_games_count
        self.on_start = on_start
        self.category_name = category_name
        self.result: dict[str, Any] | None = None
        self._preset_manager = AutoCatPresetManager()

        # Window setup
        self.setWindowTitle(t("auto_categorize.title"))
        self.setMinimumWidth(550)
        self.setModal(True)

        self._create_ui()
        self._update_estimate()
        self._center_on_parent()

    def _center_on_parent(self) -> None:
        """Center this dialog relative to its parent window."""
        if self.parent():
            parent_geo = self.parent().geometry()
            self.move(
                parent_geo.x() + (parent_geo.width() - self.width()) // 2,
                parent_geo.y() + (parent_geo.height() - self.height()) // 2,
            )

    def _create_ui(self) -> None:
        """Initialize and lay out all UI components for the auto-categorize dialog."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinAndMaxSize)

        # Title
        title = QLabel(t("auto_categorize.header"))
        title.setFont(FontHelper.get_font(16, FontHelper.BOLD))
        layout.addWidget(title)

        # === PRESET SECTION ===
        self._create_preset_section(layout)

        # === METHODS GROUP (2-column grid) ===
        methods_group = QGroupBox(t("auto_categorize.method_group"))
        methods_grid = QGridLayout()
        methods_grid.setSpacing(4)

        self.cb_tags = QCheckBox(t("auto_categorize.option_tags"))
        self.cb_tags.setChecked(True)
        self.cb_publisher = QCheckBox(t("auto_categorize.by_publisher"))
        self.cb_franchise = QCheckBox(t("auto_categorize.option_franchise"))
        self.cb_genre = QCheckBox(t("auto_categorize.by_genre"))
        self.cb_developer = QCheckBox(t("auto_categorize.by_developer"))
        self.cb_platform = QCheckBox(t("auto_categorize.by_platform"))
        self.cb_user_score = QCheckBox(t("auto_categorize.by_user_score"))
        self.cb_hours_played = QCheckBox(t("auto_categorize.by_hours_played"))
        self.cb_flags = QCheckBox(t("auto_categorize.by_flags"))
        self.cb_vr = QCheckBox(t("auto_categorize.by_vr"))
        self.cb_year = QCheckBox(t("auto_categorize.by_year"))
        self.cb_hltb = QCheckBox(t("auto_categorize.by_hltb"))
        self.cb_language = QCheckBox(t("auto_categorize.by_language"))
        self.cb_curator = QCheckBox(t("auto_categorize.by_curator"))

        checkboxes = [
            self.cb_tags,
            self.cb_publisher,
            self.cb_franchise,
            self.cb_genre,
            self.cb_developer,
            self.cb_platform,
            self.cb_user_score,
            self.cb_hours_played,
            self.cb_flags,
            self.cb_vr,
            self.cb_year,
            self.cb_hltb,
            self.cb_language,
            self.cb_curator,
        ]
        cols = 3
        for i, cb in enumerate(checkboxes):
            methods_grid.addWidget(cb, i // cols, i % cols)

        methods_group.setLayout(methods_grid)
        layout.addWidget(methods_group)

        # === TAGS SETTINGS GROUP ===
        self.tags_group = QGroupBox(t("auto_categorize.settings"))
        tags_layout = QVBoxLayout()

        # Tags per game
        tags_per_game_layout = QHBoxLayout()
        tags_per_game_layout.addWidget(QLabel(t("auto_categorize.tags_per_game") + ":"))
        self.tags_count_spin = QSpinBox()
        self.tags_count_spin.setMinimum(1)
        self.tags_count_spin.setMaximum(50)
        self.tags_count_spin.setValue(config.TAGS_PER_GAME)
        tags_per_game_layout.addWidget(self.tags_count_spin)
        tags_per_game_layout.addStretch()
        tags_layout.addLayout(tags_per_game_layout)

        # Ignore common tags
        self.cb_ignore_common = QCheckBox(t("settings.tags.ignore_common"))
        self.cb_ignore_common.setChecked(config.IGNORE_COMMON_TAGS)
        tags_layout.addWidget(self.cb_ignore_common)

        self.tags_group.setLayout(tags_layout)
        layout.addWidget(self.tags_group)

        # === CURATOR SETTINGS GROUP ===
        self._create_curator_section(layout)

        # === APPLY TO GROUP ===
        apply_group = QGroupBox(t("auto_categorize.apply_group"))
        apply_layout = QVBoxLayout()

        self.scope_group = QButtonGroup(self)

        # Determine label for "Selected" option
        if self.category_name:
            scope_text = t("auto_categorize.scope_category", name=self.category_name, count=len(self.games))
        else:
            scope_text = t("auto_categorize.scope_selected", count=len(self.games))

        self.rb_selected = QRadioButton(scope_text)
        self.rb_selected.setChecked(True)
        self.scope_group.addButton(self.rb_selected)
        apply_layout.addWidget(self.rb_selected)

        self.rb_all = QRadioButton(t("auto_categorize.scope_all", count=self.all_games_count))
        self.scope_group.addButton(self.rb_all)
        apply_layout.addWidget(self.rb_all)

        # If "All Games" are selected, pre-select "All" option
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
        warning = QLabel(t("auto_categorize.warning_backup"))
        warning.setStyleSheet("color: orange;")
        layout.addWidget(warning)

        # === BUTTONS ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton(t("common.cancel"))
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        start_btn = QPushButton(t("auto_categorize.start"))
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
        self.cb_developer.toggled.connect(self._update_estimate)
        self.cb_platform.toggled.connect(self._update_estimate)
        self.cb_user_score.toggled.connect(self._update_estimate)
        self.cb_hours_played.toggled.connect(self._update_estimate)
        self.cb_flags.toggled.connect(self._update_estimate)
        self.cb_vr.toggled.connect(self._update_estimate)
        self.cb_year.toggled.connect(self._update_estimate)
        self.cb_hltb.toggled.connect(self._update_estimate)
        self.cb_language.toggled.connect(self._update_estimate)
        self.cb_curator.toggled.connect(self._update_estimate)
        self.cb_curator.toggled.connect(self._on_curator_toggled)
        self.tags_count_spin.valueChanged.connect(self._update_estimate)
        self.rb_selected.toggled.connect(self._update_estimate)
        self.rb_all.toggled.connect(self._update_estimate)

    def _create_preset_section(self, parent_layout: QVBoxLayout) -> None:
        """Create the preset load/save/delete section.

        Args:
            parent_layout: The parent layout to add the section to.
        """
        preset_group = QGroupBox(t("auto_categorize.preset_section"))
        preset_layout = QHBoxLayout()

        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(200)
        self._refresh_preset_combo()
        preset_layout.addWidget(self.preset_combo)

        load_btn = QPushButton(t("auto_categorize.preset_load"))
        load_btn.clicked.connect(self._load_preset)
        preset_layout.addWidget(load_btn)

        save_btn = QPushButton(t("auto_categorize.preset_save"))
        save_btn.clicked.connect(self._save_preset)
        preset_layout.addWidget(save_btn)

        delete_btn = QPushButton(t("auto_categorize.preset_delete"))
        delete_btn.clicked.connect(self._delete_preset)
        preset_layout.addWidget(delete_btn)

        preset_layout.addStretch()
        preset_group.setLayout(preset_layout)
        parent_layout.addWidget(preset_group)

    def _create_curator_section(self, parent_layout: QVBoxLayout) -> None:
        """Create the curator settings section with history list, URL input, and type checkboxes.

        The history list supports click-to-select (fills URL input) and right-click
        context menu for removing entries.

        Args:
            parent_layout: The parent layout to add the section to.
        """
        self.curator_group = QGroupBox(t("auto_categorize.by_curator"))
        curator_layout = QVBoxLayout()

        # Curator history list (small scrollable box, right-click context menu)
        self.curator_history_list = QListWidget()
        self.curator_history_list.setMaximumHeight(80)
        self.curator_history_list.itemClicked.connect(self._on_curator_history_clicked)
        self.curator_history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.curator_history_list.customContextMenuRequested.connect(self._on_curator_history_context_menu)
        self._load_curator_history()
        curator_layout.addWidget(self.curator_history_list)

        # Curator URL input + Add button
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel(t("auto_categorize.curator_url_label")))
        self.curator_url_edit = QLineEdit()
        self.curator_url_edit.setPlaceholderText(t("auto_categorize.curator_url_placeholder"))
        url_layout.addWidget(self.curator_url_edit)

        add_btn = QPushButton(t("common.add"))
        add_btn.clicked.connect(self._add_curator_url)
        url_layout.addWidget(add_btn)
        curator_layout.addLayout(url_layout)

        # Recommendation type checkboxes
        rec_label = QLabel(t("auto_categorize.curator_include_label"))
        curator_layout.addWidget(rec_label)

        rec_layout = QHBoxLayout()
        self.cb_curator_recommended = QCheckBox(t("auto_categorize.curator_recommended"))
        self.cb_curator_recommended.setChecked(True)
        rec_layout.addWidget(self.cb_curator_recommended)

        self.cb_curator_not_recommended = QCheckBox(t("auto_categorize.curator_not_recommended"))
        self.cb_curator_not_recommended.setChecked(True)
        rec_layout.addWidget(self.cb_curator_not_recommended)

        self.cb_curator_informational = QCheckBox(t("auto_categorize.curator_informational"))
        self.cb_curator_informational.setChecked(True)
        rec_layout.addWidget(self.cb_curator_informational)

        rec_layout.addStretch()
        curator_layout.addLayout(rec_layout)

        self.curator_group.setLayout(curator_layout)
        self.curator_group.setVisible(False)
        parent_layout.addWidget(self.curator_group)

    # === CURATOR HISTORY ===

    def _load_curator_history(self) -> None:
        """Load saved curator URLs into the history list widget."""
        self.curator_history_list.clear()
        urls = self._read_curator_history()
        for url in urls:
            self.curator_history_list.addItem(url)

    def _on_curator_history_clicked(self, item: Any) -> None:
        """Fill the URL input when a history item is clicked.

        Args:
            item: The clicked QListWidgetItem.
        """
        self.curator_url_edit.setText(item.text())

    def _on_curator_history_context_menu(self, position: Any) -> None:
        """Show context menu for the curator history list (right-click to remove).

        Args:
            position: The position where the context menu was requested.
        """
        item = self.curator_history_list.itemAt(position)
        if not item:
            return

        menu = QMenu(self)
        remove_action = menu.addAction(t("auto_categorize.curator_remove"))
        action = menu.exec(self.curator_history_list.mapToGlobal(position))

        if action == remove_action:
            self._remove_curator_url(item.text())

    def _add_curator_url(self) -> None:
        """Add the current URL input text to the curator history list."""
        url = self.curator_url_edit.text().strip()
        if not url:
            return
        self._save_curator_url_to_history(url)

    def _remove_curator_url(self, url: str) -> None:
        """Remove a curator URL from the persistent history.

        Args:
            url: The curator URL to remove.
        """
        urls = self._read_curator_history()
        urls = [u for u in urls if u != url]
        self._write_curator_history(urls)
        self._load_curator_history()

    def _save_curator_url_to_history(self, url: str) -> None:
        """Add a curator URL to the persistent history (most recent first, deduped).

        Args:
            url: The curator URL to save.
        """
        urls = self._read_curator_history()

        # Remove if already present, then prepend
        urls = [u for u in urls if u != url]
        urls.insert(0, url)
        urls = urls[:_MAX_CURATOR_HISTORY]

        self._write_curator_history(urls)
        self._load_curator_history()

    @staticmethod
    def _write_curator_history(urls: list[str]) -> None:
        """Write the curator URL history to disk.

        Args:
            urls: List of curator URLs to persist.
        """
        try:
            _CURATOR_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(_CURATOR_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(urls, f, indent=2, ensure_ascii=False)
        except OSError as exc:
            logger.warning("Failed to save curator history: %s", exc)

    @staticmethod
    def _read_curator_history() -> list[str]:
        """Read curator URL history from disk.

        Returns:
            List of previously used curator URLs.
        """
        if not _CURATOR_HISTORY_FILE.exists():
            return []
        try:
            with open(_CURATOR_HISTORY_FILE, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return [str(u) for u in data]
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read curator history: %s", exc)
        return []

    def _on_curator_toggled(self, checked: bool) -> None:
        """Show or hide the curator settings group.

        Args:
            checked: Whether the curator checkbox is checked.
        """
        self.curator_group.setVisible(checked)
        self.adjustSize()

    # === PRESET MANAGEMENT ===

    def _refresh_preset_combo(self) -> None:
        """Reload preset names into the combo box."""
        self.preset_combo.clear()
        presets = self._preset_manager.load_presets()
        if not presets:
            self.preset_combo.addItem(t("auto_categorize.preset_no_presets"))
            self.preset_combo.setEnabled(False)
        else:
            self.preset_combo.setEnabled(True)
            for preset in presets:
                self.preset_combo.addItem(preset.name)

    def _load_preset(self) -> None:
        """Load the selected preset and apply its settings to the dialog."""
        presets = self._preset_manager.load_presets()
        if not presets:
            return

        idx = self.preset_combo.currentIndex()
        if idx < 0 or idx >= len(presets):
            return

        preset = presets[idx]
        self._apply_preset(preset)

    def _apply_preset(self, preset: AutoCatPreset) -> None:
        """Apply a preset's settings to the dialog widgets.

        Args:
            preset: The preset to apply.
        """
        methods = set(preset.methods)

        # Method checkboxes
        method_map: dict[str, QCheckBox] = {
            "tags": self.cb_tags,
            "publisher": self.cb_publisher,
            "franchise": self.cb_franchise,
            "genre": self.cb_genre,
            "developer": self.cb_developer,
            "platform": self.cb_platform,
            "user_score": self.cb_user_score,
            "hours_played": self.cb_hours_played,
            "flags": self.cb_flags,
            "vr": self.cb_vr,
            "year": self.cb_year,
            "hltb": self.cb_hltb,
            "language": self.cb_language,
            "curator": self.cb_curator,
        }

        for method_name, checkbox in method_map.items():
            checkbox.setChecked(method_name in methods)

        # Tags settings
        self.tags_count_spin.setValue(preset.tags_count)
        self.cb_ignore_common.setChecked(preset.ignore_common)

        # Curator settings
        if preset.curator_url:
            self.curator_url_edit.setText(preset.curator_url)
        if preset.curator_recommendations:
            rec_set = set(preset.curator_recommendations)
            self.cb_curator_recommended.setChecked("recommended" in rec_set)
            self.cb_curator_not_recommended.setChecked("not_recommended" in rec_set)
            self.cb_curator_informational.setChecked("informational" in rec_set)

    def _save_preset(self) -> None:
        """Save the current dialog settings as a named preset."""
        name, ok = QInputDialog.getText(self, t("auto_categorize.preset_save"), t("auto_categorize.preset_name_prompt"))
        if not ok or not name.strip():
            return

        name = name.strip()

        # Check for existing preset
        existing = self._preset_manager.load_presets()
        if any(p.name == name for p in existing):
            reply = QMessageBox.question(
                self,
                t("auto_categorize.preset_overwrite_title"),
                t("auto_categorize.preset_overwrite_msg", name=name),
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        # Build curator recommendations tuple
        curator_recs: tuple[str, ...] | None = None
        curator_url: str | None = None
        if self.cb_curator.isChecked():
            curator_url = self.curator_url_edit.text().strip() or None
            recs: list[str] = []
            if self.cb_curator_recommended.isChecked():
                recs.append("recommended")
            if self.cb_curator_not_recommended.isChecked():
                recs.append("not_recommended")
            if self.cb_curator_informational.isChecked():
                recs.append("informational")
            curator_recs = tuple(recs) if recs else None

        preset = AutoCatPreset(
            name=name,
            methods=tuple(self._get_selected_methods()),
            tags_count=self.tags_count_spin.value(),
            ignore_common=self.cb_ignore_common.isChecked(),
            curator_url=curator_url,
            curator_recommendations=curator_recs,
        )

        self._preset_manager.save_preset(preset)
        self._refresh_preset_combo()

        # Select the newly saved preset
        idx = self.preset_combo.findText(name)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)

    def _delete_preset(self) -> None:
        """Delete the currently selected preset."""
        presets = self._preset_manager.load_presets()
        if not presets:
            return

        idx = self.preset_combo.currentIndex()
        if idx < 0 or idx >= len(presets):
            return

        name = presets[idx].name
        self._preset_manager.delete_preset(name)
        self._refresh_preset_combo()

    # === METHODS & ESTIMATE ===

    def _get_selected_methods(self) -> list[str]:
        """Get the list of selected categorization methods.

        Returns:
            A list of method names.
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
        if self.cb_developer.isChecked():
            methods.append("developer")
        if self.cb_platform.isChecked():
            methods.append("platform")
        if self.cb_user_score.isChecked():
            methods.append("user_score")
        if self.cb_hours_played.isChecked():
            methods.append("hours_played")
        if self.cb_flags.isChecked():
            methods.append("flags")
        if self.cb_vr.isChecked():
            methods.append("vr")
        if self.cb_year.isChecked():
            methods.append("year")
        if self.cb_hltb.isChecked():
            methods.append("hltb")
        if self.cb_language.isChecked():
            methods.append("language")
        if self.cb_curator.isChecked():
            methods.append("curator")
        return methods

    def _update_estimate(self) -> None:
        """Update the time estimate label based on selected options."""
        # Safety check if called before UI is fully initialized
        if not hasattr(self, "estimate_label") or not hasattr(self, "tags_group"):
            return

        self.tags_group.setVisible(self.cb_tags.isChecked())
        self.adjustSize()

        game_count = self.all_games_count if self.rb_all.isChecked() else len(self.games)
        selected_methods = self._get_selected_methods()

        if "tags" in selected_methods:
            seconds = int(game_count * 1.5)
            minutes = seconds // 60
            if minutes > 0:
                time_str = t("auto_categorize.estimate_minutes", count=minutes)
            else:
                time_str = t("auto_categorize.estimate_seconds", count=seconds)
        else:
            time_str = t("auto_categorize.estimate_instant")

        self.estimate_label.setText(
            t("auto_categorize.estimate_label", time=time_str, games=game_count, methods=len(selected_methods))
        )

    def _start(self) -> None:
        """Start the auto-categorization process.

        Validates the selection, builds the configuration result,
        and calls the on_start callback.
        """
        selected_methods = self._get_selected_methods()

        if not selected_methods:
            QMessageBox.warning(self, t("auto_categorize.no_method_title"), t("auto_categorize.error_no_method"))
            return

        # Validate curator URL if curator method is selected
        if "curator" in selected_methods:
            curator_url = self.curator_url_edit.text().strip()
            if not curator_url:
                QMessageBox.warning(self, t("auto_categorize.no_method_title"), t("auto_categorize.curator_error_url"))
                return

        self.result = {
            "methods": selected_methods,
            "scope": "all" if self.rb_all.isChecked() else "selected",
            "tags_count": self.tags_count_spin.value(),
            "ignore_common": self.cb_ignore_common.isChecked(),
        }

        # Add curator-specific settings
        if "curator" in selected_methods:
            curator_url_val = self.curator_url_edit.text().strip()
            self.result["curator_url"] = curator_url_val
            self._save_curator_url_to_history(curator_url_val)
            recs: list[str] = []
            if self.cb_curator_recommended.isChecked():
                recs.append("recommended")
            if self.cb_curator_not_recommended.isChecked():
                recs.append("not_recommended")
            if self.cb_curator_informational.isChecked():
                recs.append("informational")
            self.result["curator_recommendations"] = recs

        self.accept()
        if self.on_start:
            self.on_start(self.result)

    def get_result(self) -> dict[str, Any] | None:
        """Get the configuration result after the dialog is accepted.

        Returns:
            The configuration dictionary, or None if canceled.
        """
        return self.result
