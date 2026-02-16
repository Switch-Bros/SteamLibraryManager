# src/ui/dialogs/profile_dialog.py

"""Dialog for managing categorization profiles.

Provides a modal dialog with a profile list, allowing the user to
save the current setup, load an existing profile, delete, rename,
export, and import profiles.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.utils.dialog_helpers import ask_confirmation, ask_text_input, show_error
from src.ui.utils.font_helper import FontHelper
from src.ui.widgets.ui_helper import UIHelper
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.core.profile_manager import ProfileManager

logger = logging.getLogger("steamlibmgr.profile_dialog")

__all__ = ["ProfileDialog"]


class ProfileDialog(QDialog):
    """Modal dialog for profile management.

    After ``exec()`` returns ``Accepted``, the caller should check
    ``self.action`` and ``self.selected_name`` to determine which
    action to perform.

    Attributes:
        action: The action chosen by the user (``"save"``, ``"load"``, or ``""``).
        selected_name: The profile name associated with the chosen action.
    """

    def __init__(self, manager: ProfileManager, parent: QWidget | None = None) -> None:
        """Initializes the ProfileDialog.

        Args:
            manager: The ProfileManager for data operations.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.manager: ProfileManager = manager
        self.action: str = ""
        self.selected_name: str = ""

        self.setWindowTitle(t("ui.profile.dialog_title"))
        self.setMinimumWidth(500)
        self.setMinimumHeight(420)
        self.setModal(True)

        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self) -> None:
        """Creates the dialog layout with title, info, list, and action buttons."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Title
        title = QLabel(t("ui.profile.dialog_title"))
        title.setFont(FontHelper.get_font(14, FontHelper.BOLD))
        layout.addWidget(title)

        # Info text
        info = QLabel(t("ui.profile.info_text"))
        info.setWordWrap(True)
        layout.addWidget(info)

        # Profile list
        self.profile_list = QListWidget()
        self.profile_list.setAlternatingRowColors(True)
        self.profile_list.itemDoubleClicked.connect(self._on_load)
        layout.addWidget(self.profile_list, stretch=1)

        # No-profiles placeholder (hidden by default)
        self.no_profiles_label = QLabel(t("ui.profile.no_profiles"))
        self.no_profiles_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_profiles_label.setStyleSheet("color: gray; padding: 20px;")
        self.no_profiles_label.setVisible(False)
        layout.addWidget(self.no_profiles_label)

        # Action buttons row 1: Save Current, Load, Delete
        row1 = QHBoxLayout()
        self.btn_save = QPushButton(t("common.save"))
        self.btn_save.clicked.connect(self._on_save_current)
        row1.addWidget(self.btn_save)

        self.btn_load = QPushButton(t("common.load"))
        self.btn_load.clicked.connect(self._on_load)
        row1.addWidget(self.btn_load)

        self.btn_delete = QPushButton(t("common.delete"))
        self.btn_delete.clicked.connect(self._on_delete)
        row1.addWidget(self.btn_delete)

        layout.addLayout(row1)

        # Action buttons row 2: Rename, Export, Import
        row2 = QHBoxLayout()
        self.btn_rename = QPushButton(t("common.rename"))
        self.btn_rename.clicked.connect(self._on_rename)
        row2.addWidget(self.btn_rename)

        self.btn_export = QPushButton(t("common.export"))
        self.btn_export.clicked.connect(self._on_export)
        row2.addWidget(self.btn_export)

        self.btn_import = QPushButton(t("common.import"))
        self.btn_import.clicked.connect(self._on_import)
        row2.addWidget(self.btn_import)

        layout.addLayout(row2)

        # Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        btn_close = QPushButton(t("common.close"))
        btn_close.clicked.connect(self.reject)
        close_layout.addWidget(btn_close)
        layout.addLayout(close_layout)

    # ------------------------------------------------------------------
    # List management
    # ------------------------------------------------------------------

    def _refresh_list(self) -> None:
        """Reloads the profile list from disk."""
        self.profile_list.clear()
        profiles = self.manager.list_profiles()

        has_profiles = len(profiles) > 0
        self.profile_list.setVisible(has_profiles)
        self.no_profiles_label.setVisible(not has_profiles)

        for name, created_at in profiles:
            date_str = datetime.fromtimestamp(created_at).strftime("%d.%m.%Y %H:%M") if created_at else "—"
            display = f"{name}    ({t('ui.profile.created_at', date=date_str)})"
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.profile_list.addItem(item)

        # Enable/disable action buttons based on selection
        self._update_button_states()
        self.profile_list.currentItemChanged.connect(lambda: self._update_button_states())

    def _update_button_states(self) -> None:
        """Enables or disables buttons depending on whether a profile is selected."""
        has_selection = self.profile_list.currentItem() is not None
        self.btn_load.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)
        self.btn_rename.setEnabled(has_selection)
        self.btn_export.setEnabled(has_selection)

    def _get_selected_name(self) -> str | None:
        """Returns the name stored in the currently selected list item.

        Returns:
            The profile name, or None if no item is selected.
        """
        item = self.profile_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_save_current(self) -> None:
        """Handles 'Save Current' button: asks for name, signals save action."""
        name = ask_text_input(
            self,
            title=t("ui.profile.new_title"),
            label=t("ui.profile.new_prompt"),
        )
        if not name:
            return

        # Check for duplicate
        existing = [n for n, _ in self.manager.list_profiles()]
        if name in existing:
            overwrite = ask_confirmation(
                self,
                t("ui.profile.error_duplicate_name", name=name),
                title=t("ui.profile.new_title"),
            )
            if not overwrite:
                return

        self.action = "save"
        self.selected_name = name
        self.accept()

    def _on_load(self) -> None:
        """Handles 'Load' button or double-click: signals load action."""
        name = self._get_selected_name()
        if not name:
            return

        self.action = "load"
        self.selected_name = name
        self.accept()

    def _on_delete(self) -> None:
        """Handles 'Delete' button: asks confirmation and deletes."""
        name = self._get_selected_name()
        if not name:
            return

        confirmed = ask_confirmation(
            self,
            t("ui.profile.delete_confirm", name=name),
            title=t("ui.profile.delete_confirm_title"),
        )
        if not confirmed:
            return

        self.manager.delete_profile(name)
        UIHelper.show_success(self, t("ui.profile.delete_success", name=name))
        self._refresh_list()

    def _on_rename(self) -> None:
        """Handles 'Rename' button: asks for new name and renames."""
        name = self._get_selected_name()
        if not name:
            return

        new_name = ask_text_input(
            self,
            title=t("ui.profile.rename_title"),
            label=t("ui.profile.rename_prompt"),
            default_value=name,
        )
        if not new_name or new_name == name:
            return

        success = self.manager.rename_profile(name, new_name)
        if success:
            UIHelper.show_success(self, t("ui.profile.rename_success", name=new_name))
            self._refresh_list()

    def _on_export(self) -> None:
        """Handles 'Export' button: opens file save dialog and exports."""
        from pathlib import Path

        from PyQt6.QtWidgets import QFileDialog

        name = self._get_selected_name()
        if not name:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            t("ui.profile.export_title"),
            f"{name}.json",
            t("ui.profile.import_filter"),
        )
        if not file_path:
            return

        success = self.manager.export_profile(name, Path(file_path))
        if success:
            UIHelper.show_success(self, t("ui.profile.export_success"))

    def _on_import(self) -> None:
        """Handles 'Import' button: opens file dialog and imports."""
        from pathlib import Path

        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t("ui.profile.import_title"),
            "",
            t("ui.profile.import_filter"),
        )
        if not file_path:
            return

        try:
            profile = self.manager.import_profile(Path(file_path))
            UIHelper.show_success(self, t("ui.profile.import_success", name=profile.name))
            self._refresh_list()
        except (FileNotFoundError, KeyError, Exception) as exc:
            show_error(self, t("ui.profile.error_import_failed", error=str(exc)))
