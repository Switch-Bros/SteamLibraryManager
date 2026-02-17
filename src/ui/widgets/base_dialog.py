"""Base class for application dialogs with consistent layout.

Provides standard window setup, title label, content area,
and button rows. Subclasses implement only _build_content().
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.utils.font_helper import FontHelper
from src.utils.i18n import t

__all__ = ["BaseDialog"]


class BaseDialog(QDialog):
    """Standard dialog with consistent layout and button handling.

    Subclasses override _build_content() to add their specific UI.
    Most dialogs also use buttons="custom" and add buttons in _build_content().

    Args:
        parent: Parent widget.
        title_key: i18n key for window title and optional header label.
        min_width: Minimum dialog width in pixels.
        show_title_label: Whether to show a bold header label.
        buttons: Button mode — "ok_cancel", "close", "custom", or "none".
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
        """Initializes the base dialog.

        Args:
            parent: Parent widget.
            title_key: i18n key for the window title (and header label).
            title_text: Pre-formatted title string (takes precedence over title_key).
            min_width: Minimum dialog width in pixels.
            show_title_label: Whether to display a bold title label at top.
            buttons: Button layout mode.
        """
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
        """Override this to add dialog-specific content.

        Args:
            layout: The main vertical layout to add widgets to.
        """

    def _add_buttons(self, mode: str) -> None:
        """Adds a standard button row based on mode.

        Args:
            mode: One of "ok_cancel", "close", "custom", "none".
        """
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
