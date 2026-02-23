"""Base dialog class for standardized dialog setup.

All NEW dialogs should inherit from BaseDialog instead of raw QDialog.
Existing 13 dialogs will be migrated in a separate task.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QWidget

from src.utils.i18n import t

__all__ = ["BaseDialog"]


class BaseDialog(QDialog):
    """Standardized base for all project dialogs.

    Provides consistent window title (i18n), sizing, and modality.
    """

    def __init__(
        self,
        parent: QWidget | None,
        title_key: str,
        width: int = 600,
        height: int = 400,
        resizable: bool = True,
        modal: bool = True,
    ) -> None:
        """Initialize base dialog.

        Args:
            parent: Parent widget.
            title_key: i18n key for window title.
            width: Dialog width in pixels.
            height: Dialog height in pixels.
            resizable: Whether dialog can be resized.
            modal: Whether dialog is modal.
        """
        super().__init__(parent)
        self.setWindowTitle(t(title_key))
        if resizable:
            self.setMinimumSize(width, height)
        else:
            self.setFixedSize(width, height)
        if modal:
            self.setWindowModality(Qt.WindowModality.WindowModal)
