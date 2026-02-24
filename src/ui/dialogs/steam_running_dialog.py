"""
Steam Running Warning Dialog.

This dialog is shown when the user tries to save changes while Steam is running.
Provides options to:
- Cancel the save operation
- Close Steam and save (kills Steam process)
"""

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QPushButton, QLabel

from src.ui.theme import Theme
from src.ui.widgets.base_dialog import BaseDialog
from src.ui.widgets.ui_helper import UIHelper
from src.utils.i18n import t

__all__ = ["SteamRunningDialog"]


class SteamRunningDialog(BaseDialog):
    """Warning dialog shown when Steam is running during save operation.

    Return codes:
        CANCELLED: User cancelled the operation
        CLOSE_AND_SAVE: User chose to close Steam and save
    """

    CANCELLED = 0
    CLOSE_AND_SAVE = 1

    def __init__(self, parent=None):
        """Initialize the Steam running warning dialog.

        Args:
            parent: Parent widget
        """
        super().__init__(
            parent,
            title_key="steam.running.title",
            min_width=450,
            show_title_label=False,
            buttons="custom",
        )

    def _build_content(self, layout: QVBoxLayout) -> None:
        """Builds the warning content with icon, message, and action buttons."""
        layout.setSpacing(20)

        # Warning icon + message
        header_layout = QHBoxLayout()

        icon_label = QLabel(t("emoji.warning"))
        icon_label.setStyleSheet("font-size: 48px;")
        header_layout.addWidget(icon_label)

        message_layout = QVBoxLayout()
        message_layout.setSpacing(10)

        title = QLabel(t("steam.running.warning_title"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        message_layout.addWidget(title)

        explanation = QLabel(t("steam.running.explanation"))
        explanation.setWordWrap(True)
        explanation.setStyleSheet(f"color: {Theme.TEXT_MUTED};")
        message_layout.addWidget(explanation)

        header_layout.addLayout(message_layout, 1)
        layout.addLayout(header_layout)

        # Info box
        info_box = QLabel(t("steam.running.info"))
        info_box.setWordWrap(True)
        info_box.setStyleSheet(Theme.info_box())
        layout.addWidget(info_box)

        # Buttons
        layout.addStretch()
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.btn_cancel = QPushButton(t("common.cancel"))
        self.btn_cancel.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.btn_cancel)

        self.btn_close_steam = QPushButton(t("steam.running.close_and_save"))
        self.btn_close_steam.setDefault(True)
        self.btn_close_steam.setStyleSheet(Theme.button_danger())
        self.btn_close_steam.clicked.connect(self._on_close_steam)
        button_layout.addWidget(self.btn_close_steam)

        layout.addLayout(button_layout)

    def _on_cancel(self):
        """Handle cancel button click."""
        self.done(self.CANCELLED)

    def _on_close_steam(self):
        """Handle close Steam button click."""
        from src.core.steam_account_scanner import kill_steam_process

        if not UIHelper.confirm(
            self,
            t("steam.running.confirm_message"),
            title=t("steam.running.confirm_title"),
        ):
            return

        success = kill_steam_process()

        if success:
            UIHelper.show_success(self, t("steam.running.steam_closed"))
            self.done(self.CLOSE_AND_SAVE)
        else:
            UIHelper.show_error(self, t("steam.running.close_failed"))
