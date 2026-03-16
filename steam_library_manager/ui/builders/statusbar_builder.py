#
# steam_library_manager/ui/builders/statusbar_builder.py
# Builds the status bar with statistics label and reload button
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QStatusBar, QLabel, QPushButton

from steam_library_manager.utils.i18n import t

if TYPE_CHECKING:
    from steam_library_manager.ui.main_window import MainWindow

__all__ = ["StatusbarBuilder"]


class StatusbarBuilder:
    """Constructs the application status bar with its permanent widgets."""

    def __init__(self, main_window: "MainWindow") -> None:
        self.main_window: "MainWindow" = main_window
        self.stats_label: QLabel = QLabel("")
        self.reload_btn: QPushButton = QPushButton()

    def build(self, statusbar: QStatusBar) -> None:
        """Populates a QStatusBar with the statistics label and reload button."""
        mw = self.main_window

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("padding: 0 10px;")
        statusbar.addPermanentWidget(self.stats_label, 1)

        self.reload_btn = QPushButton(t("menu.file.refresh"))
        self.reload_btn.clicked.connect(mw.file_actions.refresh_data)
        self.reload_btn.setMaximumWidth(150)
        self.reload_btn.hide()
        statusbar.addPermanentWidget(self.reload_btn)

        statusbar.showMessage(t("ui.main_window.status_ready"))
