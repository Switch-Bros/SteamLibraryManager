# src/ui/builders/statusbar_builder.py

"""
Builder for the main application status bar.

Extracts the QStatusBar setup that currently lives at the bottom of
MainWindow._create_ui().  The status bar holds two permanent widgets:
a statistics label (left, stretching) and a reload button (right, hidden
by default).
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QStatusBar, QLabel, QPushButton

from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class StatusbarBuilder:
    """Constructs the application status bar with its permanent widgets.

    After construction the caller can access stats_label and reload_btn
    to wire up the same logic that MainWindow currently uses.

    Attributes:
        main_window: Back-reference to the owning MainWindow instance.
        stats_label: Permanent left-side label for collection statistics.
        reload_btn: Permanent right-side button; hidden until an error occurs.
    """

    def __init__(self, main_window: 'MainWindow') -> None:
        """Initializes the StatusbarBuilder.

        Args:
            main_window: The MainWindow instance that owns the status bar.
        """
        self.main_window: 'MainWindow' = main_window

        # These are created in build() but declared here for type-checkers
        self.stats_label: QLabel = QLabel("")
        self.reload_btn: QPushButton = QPushButton()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, statusbar: QStatusBar) -> None:
        """Populates a QStatusBar with the statistics label and reload button.

        The stats label stretches to fill available space (stretch=1).
        The reload button is hidden by default and only shown when game
        loading fails so the user can retry without restarting.

        Args:
            statusbar: The QStatusBar instance to populate (typically self.statusBar()).
        """
        mw = self.main_window

        # --- Statistics label (left, permanent, stretching) ---
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("padding: 0 10px;")
        # stretch=1 so it fills the space and showMessage() text goes to the right
        statusbar.addPermanentWidget(self.stats_label, 1)

        # --- Reload button (right, permanent, hidden until needed) ---
        self.reload_btn = QPushButton(t('ui.menu.file.refresh'))
        self.reload_btn.clicked.connect(mw.refresh_data)
        self.reload_btn.setMaximumWidth(150)
        self.reload_btn.hide()  # Only shown on load failure
        statusbar.addPermanentWidget(self.reload_btn)

        # Set initial status message
        statusbar.showMessage(t('ui.main_window.status_ready'))
