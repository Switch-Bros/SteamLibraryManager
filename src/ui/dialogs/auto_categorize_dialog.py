# src/ui/dialogs/auto_categorize_dialog.py

"""Dialog for automatic game categorization.

Provides preset management, method selection (via AutoCatMethodSelector),
curator configuration, and start logic.
"""

from __future__ import annotations

__all__ = ["AutoCategorizeDialog"]

import logging
from pathlib import Path
from typing import Any, Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.config import config
from src.services.autocat_preset_manager import AutoCatPreset, AutoCatPresetManager
from src.ui.utils.font_helper import FontHelper
from src.ui.widgets.autocat_method_selector import AutoCatMethodSelector
from src.ui.widgets.base_dialog import BaseDialog
from src.ui.widgets.ui_helper import UIHelper
from src.utils.i18n import t
from src.utils.json_utils import load_json, save_json

logger = logging.getLogger("steamlibmgr.auto_categorize_dialog")

_CURATOR_HISTORY_FILE: Path = config.DATA_DIR / "curator_history.json"
_MAX_CURATOR_HISTORY = 20


class AutoCategorizeDialog(BaseDialog):
    """Dialog for configuring and starting automatic game categorization.

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
            on_start: Callback to execute when categorization starts.
            category_name: Name of the category being processed, if any.
        """
        self.games = games
        self.all_games_count = all_games_count
        self.on_start = on_start
        self.category_name = category_name
        self.result: dict[str, Any] | None = None
        self._preset_manager = AutoCatPresetManager()

        super().__init__(
            parent,
            title_key="auto_categorize.title",
            min_width=550,
            show_title_label=False,
            buttons="custom",
        )
        self._center_on_parent()

    def _center_on_parent(self) -> None:
        """Center this dialog relative to its parent window."""
        if self.parent():
            parent_geo = self.parent().geometry()
            self.move(
                parent_geo.x() + (parent_geo.width() - self.width()) // 2,
                parent_geo.y() + (parent_geo.height() - self.height()) // 2,
            )

    def _build_content(self, layout: QVBoxLayout) -> None:
        """Initialize and lay out all UI components."""
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSizeConstraint(QVBoxLayout.SizeConstraint.SetMinAndMaxSize)

        # Title
        title = QLabel(t("auto_categorize.header"))
        title.setFont(FontHelper.get_font(16, FontHelper.BOLD))
        layout.addWidget(title)

        # Preset section
        self._create_preset_section(layout)

        # Method selector widget
        self.selector = AutoCatMethodSelector(self, len(self.games), self.all_games_count, self.category_name)
        self.selector.methods_changed.connect(self._on_methods_changed)
        layout.addWidget(self.selector)

        # Curator settings
        self._create_curator_section(layout)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # Warning
        warning = QLabel(t("auto_categorize.warning_backup"))
        warning.setStyleSheet("color: orange;")
        layout.addWidget(warning)

        # Buttons
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

    def _on_methods_changed(self) -> None:
        """Handle method selection changes from the selector."""
        self.curator_group.setVisible(self.selector.is_curator_selected())
        self.adjustSize()

    # ------------------------------------------------------------------
    # Preset section
    # ------------------------------------------------------------------

    def _create_preset_section(self, parent_layout: QVBoxLayout) -> None:
        """Create the preset load/save/delete section.

        Args:
            parent_layout: Layout to add the section to.
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
        """Load the selected preset and apply its settings."""
        presets = self._preset_manager.load_presets()
        if not presets:
            return

        idx = self.preset_combo.currentIndex()
        if idx < 0 or idx >= len(presets):
            return

        self._apply_preset(presets[idx])

    def _apply_preset(self, preset: AutoCatPreset) -> None:
        """Apply a preset's settings to the dialog.

        Args:
            preset: The preset to apply.
        """
        self.selector.apply_preset(
            set(preset.methods),
            preset.tags_count,
            preset.ignore_common,
        )

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

        existing = self._preset_manager.load_presets()
        if any(p.name == name for p in existing):
            if not UIHelper.confirm(
                self,
                t("auto_categorize.preset_overwrite_msg", name=name),
                title=t("auto_categorize.preset_overwrite_title"),
            ):
                return

        # Build curator settings
        curator_recs: tuple[str, ...] | None = None
        curator_url: str | None = None
        if self.selector.is_curator_selected():
            curator_url = self.curator_url_edit.text().strip() or None
            recs: list[str] = []
            if self.cb_curator_recommended.isChecked():
                recs.append("recommended")
            if self.cb_curator_not_recommended.isChecked():
                recs.append("not_recommended")
            if self.cb_curator_informational.isChecked():
                recs.append("informational")
            curator_recs = tuple(recs) if recs else None

        settings = self.selector.get_settings()
        preset = AutoCatPreset(
            name=name,
            methods=tuple(settings["methods"]),
            tags_count=settings["tags_count"],
            ignore_common=settings["ignore_common"],
            curator_url=curator_url,
            curator_recommendations=curator_recs,
        )

        self._preset_manager.save_preset(preset)
        self._refresh_preset_combo()

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

        self._preset_manager.delete_preset(presets[idx].name)
        self._refresh_preset_combo()

    # ------------------------------------------------------------------
    # Curator section
    # ------------------------------------------------------------------

    def _create_curator_section(self, parent_layout: QVBoxLayout) -> None:
        """Create the curator settings section with history, URL input, and type checkboxes.

        Args:
            parent_layout: Layout to add the section to.
        """
        self.curator_group = QGroupBox(t("auto_categorize.by_curator"))
        curator_layout = QVBoxLayout()

        # Curator history list
        self.curator_history_list = QListWidget()
        self.curator_history_list.setMaximumHeight(80)
        self.curator_history_list.itemClicked.connect(self._on_curator_history_clicked)
        self.curator_history_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.curator_history_list.customContextMenuRequested.connect(self._on_curator_history_context_menu)
        self._load_curator_history()
        curator_layout.addWidget(self.curator_history_list)

        # Curator URL input
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

    # ------------------------------------------------------------------
    # Curator history
    # ------------------------------------------------------------------

    def _load_curator_history(self) -> None:
        """Load saved curator URLs into the history list widget."""
        self.curator_history_list.clear()
        for url in self._read_curator_history():
            self.curator_history_list.addItem(url)

    def _on_curator_history_clicked(self, item: Any) -> None:
        """Fill URL input when a history item is clicked.

        Args:
            item: The clicked QListWidgetItem.
        """
        self.curator_url_edit.setText(item.text())

    def _on_curator_history_context_menu(self, position: Any) -> None:
        """Show context menu for curator history (remove entry).

        Args:
            position: Position where the context menu was requested.
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
        """Add the current URL input text to curator history."""
        url = self.curator_url_edit.text().strip()
        if url:
            self._save_curator_url_to_history(url)

    def _remove_curator_url(self, url: str) -> None:
        """Remove a curator URL from the persistent history.

        Args:
            url: The curator URL to remove.
        """
        urls = [u for u in self._read_curator_history() if u != url]
        self._write_curator_history(urls)
        self._load_curator_history()

    def _save_curator_url_to_history(self, url: str) -> None:
        """Add a curator URL to persistent history (most recent first, deduped).

        Args:
            url: The curator URL to save.
        """
        urls = [u for u in self._read_curator_history() if u != url]
        urls.insert(0, url)
        self._write_curator_history(urls[:_MAX_CURATOR_HISTORY])
        self._load_curator_history()

    @staticmethod
    def _write_curator_history(urls: list[str]) -> None:
        """Write curator URL history to disk.

        Args:
            urls: List of curator URLs to persist.
        """
        save_json(_CURATOR_HISTORY_FILE, urls)

    @staticmethod
    def _read_curator_history() -> list[str]:
        """Read curator URL history from disk.

        Returns:
            List of previously used curator URLs.
        """
        data = load_json(_CURATOR_HISTORY_FILE, default=[])
        return [str(u) for u in data] if isinstance(data, list) else []

    # ------------------------------------------------------------------
    # Start
    # ------------------------------------------------------------------

    def _start(self) -> None:
        """Start the auto-categorization process."""
        settings = self.selector.get_settings()
        methods = settings["methods"]

        if not methods:
            UIHelper.show_warning(
                self, t("auto_categorize.error_no_method"), title=t("auto_categorize.no_method_title")
            )
            return

        # Validate curator URL if curator method is selected
        if "curator" in methods:
            curator_url = self.curator_url_edit.text().strip()
            if not curator_url:
                UIHelper.show_warning(
                    self, t("auto_categorize.curator_error_url"), title=t("auto_categorize.no_method_title")
                )
                return

        self.result = dict(settings)

        # Add curator-specific settings
        if "curator" in methods:
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
