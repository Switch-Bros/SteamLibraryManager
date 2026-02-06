# src/ui/components/ui_helper.py

"""
Provides static helper methods for creating standardized UI dialogs.

This class centralizes QMessageBox and QInputDialog logic to ensure
consistent styling, titles, and use of internationalization across the application.
"""
from typing import Optional, Tuple
from PyQt6.QtWidgets import QWidget, QMessageBox, QInputDialog
from src.utils.i18n import t


class UIHelper:
    """A static helper class for common UI dialog interactions."""

    @staticmethod
    def show_error(parent: QWidget, message: str, title: Optional[str] = None) -> None:
        """
        Displays a standardized critical error message box.

        Args:
            parent (QWidget): The parent widget for the dialog.
            message (str): The main error message to display.
            title (Optional[str]): The title for the dialog window. Defaults to the
                                   common 'Error' translation.
        """
        if title is None:
            title = t('common.error')
        QMessageBox.critical(parent, title, message)

    @staticmethod
    def show_success(parent: QWidget, message: str, title: Optional[str] = None) -> None:
        """
        Displays a standardized informational success message box.

        Args:
            parent (QWidget): The parent widget for the dialog.
            message (str): The success message to display.
            title (Optional[str]): The title for the dialog window. Defaults to the
                                   common 'Success' translation.
        """
        if title is None:
            title = t('common.success')
        QMessageBox.information(parent, title, message)

    @staticmethod
    def show_warning(parent: QWidget, message: str, title: Optional[str] = None) -> None:
        """
        Displays a standardized warning message box.

        Args:
            parent (QWidget): The parent widget for the dialog.
            message (str): The warning message to display.
            title (Optional[str]): The title for the dialog window. Defaults to the
                                   common 'Warning' translation.
        """
        if title is None:
            title = t('common.warning')  # Use the new 'warning' key
        QMessageBox.warning(parent, title, message)

    @staticmethod
    def show_info(parent: QWidget, message: str, title: Optional[str] = None) -> None:
        """
        Displays a standardized informational message box.

        Args:
            parent (QWidget): The parent widget for the dialog.
            message (str): The informational message to display.
            title (Optional[str]): The title for the dialog window. Defaults to the
                                   common 'Info' translation.
        """
        if title is None:
            title = t('common.info')
        QMessageBox.information(parent, title, message)

    @staticmethod
    def confirm(parent: QWidget, question: str, title: Optional[str] = None) -> bool:
        """Displays a Yes/No confirmation dialog with localised button texts.

        Uses addButton() instead of StandardButtons because Qt6 on Linux does
        not translate StandardButton labels without .qm translation files.

        Args:
            parent: The parent widget for the dialog.
            question: The question to ask the user.
            title: The title bar text.  Defaults to the app title.

        Returns:
            True if the user clicked Yes, False otherwise.
        """
        if title is None:
            title = t('ui.main_window.title')

        msg = QMessageBox(parent)
        msg.setWindowTitle(title)
        msg.setText(question)
        msg.setIcon(QMessageBox.Icon.Question)

        # Manual buttons with i18n text — bypasses broken Qt auto-translation
        yes_btn = msg.addButton(t('common.yes'), QMessageBox.ButtonRole.YesRole)
        msg.addButton(t('common.no'), QMessageBox.ButtonRole.NoRole)
        msg.setDefaultButton(yes_btn)

        msg.exec()
        return msg.clickedButton() == yes_btn

    @staticmethod
    def ask_text(parent: QWidget, title: str, label: str, current_text: str = "") -> Tuple[str, bool]:
        """
        Displays a standardized input dialog to ask the user for text.

        Args:
            parent (QWidget): The parent widget for the dialog.
            title (str): The title for the dialog window.
            label (str): The label displayed next to the input field.
            current_text (str): The default text to show in the input field.

        Returns:
            Tuple[str, bool]: A tuple containing the entered text and a boolean
                              indicating if the user clicked OK (True) or Cancel (False).
        """
        return QInputDialog.getText(parent, title, label, text=current_text)
