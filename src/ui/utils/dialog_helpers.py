"""
Common dialog patterns and confirmations.

This module provides reusable dialog functions for common user interactions
like confirmations, text input, and choice selections.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QMessageBox, QWidget, QDialog, QVBoxLayout, QLabel,
    QLineEdit, QComboBox, QDialogButtonBox
)

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

    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(QMessageBox.Icon.Question)
    yes_btn = msg.addButton(t('common.yes'), QMessageBox.ButtonRole.YesRole)
    no_btn = msg.addButton(t('common.no'), QMessageBox.ButtonRole.NoRole)
    msg.setDefaultButton(no_btn)
    msg.exec()

    return msg.clickedButton() == yes_btn

def ask_text_input(
        parent: QWidget,
        title: str,
        label: str,
        default_value: str = ""
) -> str | None:
    """Shows a dialog requesting text input from the user.

    Returns the entered text or None if cancelled.

    Args:
        parent: Parent widget for the dialog.
        title: Dialog window title.
        label: Label text shown above the input field.
        default_value: Pre-filled text in the input field. Defaults to empty string.

    Returns:
        str | None: The entered text, or None if cancelled.
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    layout = QVBoxLayout()

    # Label
    label_widget = QLabel(label)
    layout.addWidget(label_widget)

    # Text input
    line_edit = QLineEdit()
    line_edit.setText(default_value)
    layout.addWidget(line_edit)

    # Buttons
    button_box = QDialogButtonBox()
    button_box.addButton(t('common.ok'), QDialogButtonBox.ButtonRole.AcceptRole)
    button_box.addButton(t('common.cancel'), QDialogButtonBox.ButtonRole.RejectRole)
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)
    layout.addWidget(button_box)

    dialog.setLayout(layout)

    if dialog.exec() == QDialog.DialogCode.Accepted:
        text = line_edit.text()
        if text:
            return text
    return None

def ask_choice(
        parent: QWidget,
        title: str,
        label: str,
        option_list: list[str],
        current: int = 0
) -> str | None:
    """Shows a dropdown selection dialog.

    Returns the selected option or None if cancelled.

    Args:
        parent: Parent widget for the dialog.
        title: Dialog window title.
        label: Label text shown above the dropdown.
        option_list: List of options to choose from.
        current: Index of the initially selected option. Defaults to 0.

    Returns:
        str | None: The selected option, or None if cancelled.
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    layout = QVBoxLayout()

    # Label
    label_widget = QLabel(label)
    layout.addWidget(label_widget)

    # Combo box
    combo_box = QComboBox()
    combo_box.addItems(option_list)
    combo_box.setCurrentIndex(current)
    layout.addWidget(combo_box)

    # Buttons
    button_box = QDialogButtonBox()
    button_box.addButton(t('common.ok'), QDialogButtonBox.ButtonRole.AcceptRole)
    button_box.addButton(t('common.cancel'), QDialogButtonBox.ButtonRole.RejectRole)
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)
    layout.addWidget(button_box)

    dialog.setLayout(layout)

    if dialog.exec() == QDialog.DialogCode.Accepted:
        return combo_box.currentText()
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

    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(QMessageBox.Icon.Warning)
    msg.addButton(t('common.ok'), QMessageBox.ButtonRole.AcceptRole)
    msg.exec()

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

    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(QMessageBox.Icon.Information)
    msg.addButton(t('common.ok'), QMessageBox.ButtonRole.AcceptRole)
    msg.exec()

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

    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.addButton(t('common.ok'), QMessageBox.ButtonRole.AcceptRole)
    msg.exec()

def ask_yes_no_cancel(
        parent: QWidget,
        message: str,
        title: str = ""
) -> bool | None:
    """Shows a Yes/No/Cancel dialog.

    Returns True for Yes, False for No, None for Cancel.

    Args:
        parent: Parent widget for the dialog.
        message: Question to display.
        title: Optional title for the dialog window.

    Returns:
        bool | None: True if Yes, False if No, None if Cancel.
    """
    if not title:
        title = t('ui.dialogs.confirm')

    msg = QMessageBox(parent)
    msg.setWindowTitle(title)
    msg.setText(message)
    msg.setIcon(QMessageBox.Icon.Question)
    yes_btn = msg.addButton(t('common.yes'), QMessageBox.ButtonRole.YesRole)
    no_btn = msg.addButton(t('common.no'), QMessageBox.ButtonRole.NoRole)
    cancel_btn = msg.addButton(t('common.cancel'), QMessageBox.ButtonRole.RejectRole)
    msg.setDefaultButton(cancel_btn)
    msg.exec()

    clicked = msg.clickedButton()
    if clicked == yes_btn:
        return True
    elif clicked == no_btn:
        return False
    else:
        return None