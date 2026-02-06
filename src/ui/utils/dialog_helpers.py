"""
Common dialog patterns and confirmations.

This module provides reusable dialog functions for common user interactions
like confirmations, text input, and choice selections.
"""
from typing import Optional, List

from PyQt6.QtWidgets import QMessageBox, QInputDialog, QWidget

from src.utils.i18n import t


def ask_confirmation(
        parent: QWidget,
        message: str,
        title: str = ""
) -> bool:
    """Shows a Yes/No confirmation dialog.

    Returns True if user clicks Yes, False if user clicks No.

    Args:
        parent: Parent widget for the dialog.
        message: Confirmation question to display.
        title: Optional title for the dialog window.

    Returns:
        bool: True if confirmed, False otherwise.
    """
    if not title:
        title = t('ui.dialogs.confirm')

    reply = QMessageBox.question(
        parent,
        title,
        message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No  # Default to No for safety
    )

    return reply == QMessageBox.StandardButton.Yes


def ask_text_input(
        parent: QWidget,
        title: str,
        label: str,
        default_value: str = ""
) -> Optional[str]:
    """Shows a dialog requesting text input from the user.

    Returns the entered text or None if cancelled.

    Args:
        parent: Parent widget for the dialog.
        title: Dialog window title.
        label: Label text shown above the input field.
        default_value: Pre-filled text in the input field. Defaults to empty string.

    Returns:
        Optional[str]: The entered text, or None if cancelled.
    """
    text, ok = QInputDialog.getText(parent, title, label, text=default_value)

    if ok and text:
        return text
    return None


def ask_choice(
        parent: QWidget,
        title: str,
        label: str,
        option_list: List[str],
        current: int = 0
) -> Optional[str]:
    """Shows a dropdown selection dialog.

    Returns the selected option or None if cancelled.

    Args:
        parent: Parent widget for the dialog.
        title: Dialog window title.
        label: Label text shown above the dropdown.
        option_list: List of options to choose from.
        current: Index of the initially selected option. Defaults to 0.

    Returns:
        Optional[str]: The selected option, or None if cancelled.
    """
    selected_option, ok = QInputDialog.getItem(
        parent,
        title,
        label,
        option_list,
        current,
        False  # Not editable
    )

    if ok:
        return selected_option
    return None


def show_warning(
        parent: QWidget,
        message: str,
        title: str = ""
) -> None:
    """Shows a warning message dialog with an OK button.

    Args:
        parent: Parent widget for the dialog.
        message: Warning message to display.
        title: Optional title for the dialog window.
    """
    if not title:
        title = t('ui.dialogs.warning')

    QMessageBox.warning(parent, title, message, QMessageBox.StandardButton.Ok)


def show_info(
        parent: QWidget,
        message: str,
        title: str = ""
) -> None:
    """Shows an information message dialog with an OK button.

    Args:
        parent: Parent widget for the dialog.
        message: Information message to display.
        title: Optional title for the dialog window.
    """
    if not title:
        title = t('ui.dialogs.info')

    QMessageBox.information(parent, title, message, QMessageBox.StandardButton.Ok)


def show_error(
        parent: QWidget,
        message: str,
        title: str = ""
) -> None:
    """Shows an error message dialog with an OK button.

    Args:
        parent: Parent widget for the dialog.
        message: Error message to display.
        title: Optional title for the dialog window.
    """
    if not title:
        title = t('ui.dialogs.error')

    QMessageBox.critical(parent, title, message, QMessageBox.StandardButton.Ok)


def ask_yes_no_cancel(
        parent: QWidget,
        message: str,
        title: str = ""
) -> Optional[bool]:
    """Shows a Yes/No/Cancel dialog.

    Returns True for Yes, False for No, None for Cancel.

    Args:
        parent: Parent widget for the dialog.
        message: Question to display.
        title: Optional title for the dialog window.

    Returns:
        Optional[bool]: True if Yes, False if No, None if Cancel.
    """
    if not title:
        title = t('ui.dialogs.confirm')

    reply = QMessageBox.question(
        parent,
        title,
        message,
        QMessageBox.StandardButton.Yes |
        QMessageBox.StandardButton.No |
        QMessageBox.StandardButton.Cancel,
        QMessageBox.StandardButton.Cancel  # Default to Cancel for safety
    )

    if reply == QMessageBox.StandardButton.Yes:
        return True
    elif reply == QMessageBox.StandardButton.No:
        return False
    else:
        return None