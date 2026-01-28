"""
UI Helper - Standardized Dialogs & Interactions
Centralizes QMessageBox logic to ensure consistent styling and i18n usage.
"""
from typing import Optional, Tuple
from PyQt6.QtWidgets import QWidget, QMessageBox, QInputDialog
from src.utils.i18n import t


class UIHelper:
    """
    Static helper class for common UI dialogs.
    Uses 'common' keys from locales for titles/buttons automatically.
    """

    @staticmethod
    def show_error(parent: QWidget, message: str, title: Optional[str] = None) -> None:
        """Shows a critical error message."""
        if title is None:
            title = t('common.error')
        QMessageBox.critical(parent, title, message)

    @staticmethod
    def show_success(parent: QWidget, message: str, title: Optional[str] = None) -> None:
        """Shows a success information message."""
        if title is None:
            title = t('common.success')
        QMessageBox.information(parent, title, message)

    @staticmethod
    def show_warning(parent: QWidget, message: str, title: Optional[str] = None) -> None:
        """Shows a warning message."""
        if title is None:
            title = t('common.error')  # Or add 'common.warning' to JSON if preferred
        QMessageBox.warning(parent, title, message)

    @staticmethod
    def confirm(parent: QWidget, question: str, title: Optional[str] = None) -> bool:
        """
        Shows a Yes/No confirmation dialog.
        Returns: True if user clicked Yes, False otherwise.
        """
        if title is None:
            title = t('ui.main_window.title')

        reply = QMessageBox.question(
            parent,
            title,
            question,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    @staticmethod
    def ask_text(parent: QWidget, title: str, label: str, current_text: str = "") -> Tuple[str, bool]:
        """
        Shows an input dialog for text.
        Returns: (text, ok) tuple.
        """
        return QInputDialog.getText(parent, title, label, text=current_text)