# src/ui/dialogs/auto_categorize_dialog.py

"""Dialog for automatic game categorization.

Provides preset management, method selection (via AutoCatMethodSelector),
curator configuration, and start logic.
"""

from __future__ import annotations

__all__ = ["AutoCategorizeDialog"]

import logging
from typing import Any, Callable

from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.services.autocat_preset_manager import AutoCatPreset, AutoCatPresetManager
from src.ui.utils.font_helper import FontHelper
from src.ui.widgets.autocat_method_selector import AutoCatMethodSelector
from src.ui.widgets.base_dialog import BaseDialog
from src.ui.widgets.ui_helper import UIHelper
from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.auto_categorize_dialog")


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

        settings = self.selector.get_settings()
        preset = AutoCatPreset(
            name=name,
            methods=tuple(settings["methods"]),
            tags_count=settings["tags_count"],
            ignore_common=settings["ignore_common"],
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
        """Create the curator settings section with info label.

        The old live-fetch approach (URL input + recommendation type checkboxes)
        has been replaced. Curators are now managed via Tools > Manage Curators
        and their recommendations are stored in the database.

        Args:
            parent_layout: Layout to add the section to.
        """
        self.curator_group = QGroupBox(t("auto_categorize.by_curator"))
        curator_layout = QVBoxLayout()

        # Info label explaining the new DB-backed approach
        info_label = QLabel(t("auto_categorize.curator_info"))
        info_label.setWordWrap(True)
        curator_layout.addWidget(info_label)

        self.curator_group.setLayout(curator_layout)
        self.curator_group.setVisible(False)
        parent_layout.addWidget(self.curator_group)

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

        self.result = dict(settings)

        self.accept()
        if self.on_start:
            self.on_start(self.result)

    def get_result(self) -> dict[str, Any] | None:
        """Get the configuration result after the dialog is accepted.

        Returns:
            The configuration dictionary, or None if canceled.
        """
        return self.result
