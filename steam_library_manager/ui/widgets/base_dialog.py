#
# steam_library_manager/ui/widgets/base_dialog.py
# Base class for application dialogs with consistent layout.
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from steam_library_manager.ui.utils.font_helper import FontHelper
from steam_library_manager.utils.i18n import t

__all__ = ["BaseDialog"]


class BaseDialog(QDialog):
    """Standard dialog with consistent layout and button handling.

    Subclasses override _build_content() to add their specific UI.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        title_key: str = "",
        title_text: str = "",
        min_width: int = 500,
        show_title_label: bool = True,
        buttons: str = "ok_cancel",
    ) -> None:
        super().__init__(parent)
        display_title = title_text or (t(title_key) if title_key else "")
        if display_title:
            self.setWindowTitle(display_title)
        self.setMinimumWidth(min_width)
        self.setModal(True)

        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(12)

        if show_title_label and display_title:
            title_label = QLabel(display_title)
            title_label.setFont(FontHelper.get_font(14, FontHelper.BOLD))
            self._layout.addWidget(title_label)

        self._build_content(self._layout)
        self._add_buttons(buttons)

    def _build_content(self, layout: QVBoxLayout) -> None:
        """Override to add dialog-specific content."""

    def _add_buttons(self, mode: str) -> None:
        if mode in ("none", "custom"):
            return

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        if mode == "ok_cancel":
            self.btn_cancel = QPushButton(t("common.cancel"))
            self.btn_cancel.clicked.connect(self.reject)
            btn_layout.addWidget(self.btn_cancel)

            self.btn_ok = QPushButton(t("common.ok"))
            self.btn_ok.clicked.connect(self.accept)
            self.btn_ok.setDefault(True)
            btn_layout.addWidget(self.btn_ok)

        elif mode == "close":
            btn_close = QPushButton(t("common.close"))
            btn_close.clicked.connect(self.reject)
            btn_layout.addWidget(btn_close)

        self._layout.addLayout(btn_layout)
