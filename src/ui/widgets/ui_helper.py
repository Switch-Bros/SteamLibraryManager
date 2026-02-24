# src/ui/components/ui_helper.py

"""
Provides static helper methods for creating standardized UI dialogs.

This class centralizes QMessageBox and QInputDialog logic to ensure
consistent styling, titles, and use of internationalization across the application.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QVBoxLayout,
    QWidget,
)

from src.utils.i18n import t
from src.version import __app_name__

__all__ = ["UIHelper"]


class UIHelper:
    """A static helper class for common UI dialog interactions."""

    @staticmethod
    def _show_message(
        parent: QWidget,
        message: str,
        title: str,
        icon: QMessageBox.Icon,
    ) -> None:
        """Display a message box with a localized OK button.

        Args:
            parent: The parent widget for the dialog.
            message: The message text to display.
            title: The dialog window title.
            icon: The QMessageBox icon to show.
        """
        msg = QMessageBox(parent)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(icon)
        msg.addButton(t("common.ok"), QMessageBox.ButtonRole.AcceptRole)
        msg.exec()

    @staticmethod
    def show_error(parent: QWidget, message: str, title: str | None = None) -> None:
        """Displays a critical error message box with localized OK button.

        Args:
            parent: The parent widget for the dialog.
            message: The main error message to display.
            title: The title for the dialog window. Defaults to common 'Error'.
        """
        UIHelper._show_message(
            parent,
            message,
            title or t("common.error"),
            QMessageBox.Icon.Critical,
        )

    @staticmethod
    def show_success(parent: QWidget, message: str, title: str | None = None) -> None:
        """Displays an informational success message box with localized OK button.

        Args:
            parent: The parent widget for the dialog.
            message: The success message to display.
            title: The title for the dialog window. Defaults to common 'Success'.
        """
        UIHelper._show_message(
            parent,
            message,
            title or t("common.success"),
            QMessageBox.Icon.Information,
        )

    @staticmethod
    def show_warning(parent: QWidget, message: str, title: str | None = None) -> None:
        """Displays a warning message box with localized OK button.

        Args:
            parent: The parent widget for the dialog.
            message: The warning message to display.
            title: The title for the dialog window. Defaults to common 'Warning'.
        """
        UIHelper._show_message(
            parent,
            message,
            title or t("common.warning"),
            QMessageBox.Icon.Warning,
        )

    @staticmethod
    def show_info(parent: QWidget, message: str, title: str | None = None) -> None:
        """Displays an informational message box with localized OK button.

        Args:
            parent: The parent widget for the dialog.
            message: The informational message to display.
            title: The title for the dialog window. Defaults to common 'Info'.
        """
        UIHelper._show_message(
            parent,
            message,
            title or t("common.info"),
            QMessageBox.Icon.Information,
        )

    @staticmethod
    def confirm(parent: QWidget, question: str, title: str | None = None) -> bool:
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
            title = __app_name__

        msg = QMessageBox(parent)
        msg.setWindowTitle(title)
        msg.setText(question)
        msg.setIcon(QMessageBox.Icon.Question)

        # Manual buttons with i18n text — bypasses broken Qt auto-translation
        yes_btn = msg.addButton(t("common.yes"), QMessageBox.ButtonRole.YesRole)
        msg.addButton(t("common.no"), QMessageBox.ButtonRole.NoRole)
        msg.setDefaultButton(yes_btn)

        msg.exec()
        return msg.clickedButton() == yes_btn

    @staticmethod
    def show_batch_result(
        parent: QWidget,
        message: str,
        title: str | None = None,
    ) -> bool:
        """Displays a batch operation result with force-refresh option.

        Shows the result message with two buttons:
        - "Alle neu einlesen" (force refresh) -> returns True
        - "OK" (close) -> returns False

        This replaces separate force-refresh menu entries. Users can
        trigger force-refresh from the result dialog instead.

        Args:
            parent: The parent widget for the dialog.
            message: The result message to display.
            title: The dialog window title. Defaults to common 'Info'.

        Returns:
            True if the user clicked force-refresh, False for OK.
        """
        msg = QMessageBox(parent)
        msg.setWindowTitle(title or t("common.info"))
        msg.setText(message)
        msg.setIcon(QMessageBox.Icon.Information)

        refresh_btn = msg.addButton(
            t("ui.enrichment.force_refresh_button"),
            QMessageBox.ButtonRole.ActionRole,
        )
        ok_btn = msg.addButton(t("common.ok"), QMessageBox.ButtonRole.AcceptRole)
        msg.setDefaultButton(ok_btn)

        msg.exec()
        return msg.clickedButton() == refresh_btn

    @staticmethod
    def ask_text(parent: QWidget, title: str, label: str, current_text: str = "") -> tuple[str, bool]:
        """
        Displays a standardized input dialog to ask the user for text.

        Args:
            parent (QWidget): The parent widget for the dialog.
            title (str): The title for the dialog window.
            label (str): The label displayed next to the input field.
            current_text (str): The default text to show in the input field.

        Returns:
            tuple[str, bool]: A tuple containing the entered text and a boolean
                              indicating if the user clicked OK (True) or Cancel (False).
        """
        dialog = QDialog(parent)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout()

        # Label
        label_widget = QLabel(label)
        layout.addWidget(label_widget)

        # Text input
        line_edit = QLineEdit()
        line_edit.setText(current_text)
        layout.addWidget(line_edit)

        # Buttons
        button_box = QDialogButtonBox()
        button_box.addButton(t("common.ok"), QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton(t("common.cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.setLayout(layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            return line_edit.text(), True
        return "", False

    @staticmethod
    def create_progress_dialog(
        parent: QWidget,
        message: str,
        maximum: int = 100,
        cancelable: bool = True,
        title: str | None = None,
    ) -> QProgressDialog:
        """Create a standard progress dialog.

        Args:
            parent: Parent widget.
            message: Progress message text.
            maximum: Maximum progress value.
            cancelable: Whether dialog can be cancelled.
            title: Optional window title.

        Returns:
            Configured QProgressDialog.
        """
        dialog = QProgressDialog(
            message,
            t("common.cancel") if cancelable else "",
            0,
            maximum,
            parent,
        )
        if title:
            dialog.setWindowTitle(title)
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.setMinimumDuration(0)
        if not cancelable:
            dialog.setCancelButton(None)
        return dialog

    @staticmethod
    def show_choice(
        parent: QWidget,
        message: str,
        title: str,
        buttons: list[tuple[str, QMessageBox.ButtonRole]],
        icon: QMessageBox.Icon = QMessageBox.Icon.Question,
    ) -> int:
        """Show dialog with custom buttons.

        Args:
            parent: Parent widget.
            message: Dialog message text.
            title: Window title.
            buttons: List of (label, role) tuples.
            icon: Dialog icon type.

        Returns:
            Index of clicked button (0-based).
        """
        msg = QMessageBox(parent)
        msg.setIcon(icon)
        msg.setWindowTitle(title)
        msg.setText(message)
        btn_objects = [msg.addButton(label, role) for label, role in buttons]
        msg.exec()
        clicked = msg.clickedButton()
        return next((i for i, btn in enumerate(btn_objects) if btn == clicked), 0)

    @staticmethod
    def ask_save_file(
        parent: QWidget,
        title: str,
        filters: str,
        default_name: str = "",
    ) -> str | None:
        """Show standard save file dialog.

        Args:
            parent: Parent widget.
            title: Dialog title.
            filters: File type filters (e.g., "CSV Files (*.csv)").
            default_name: Default filename.

        Returns:
            Selected file path, or None if cancelled.
        """
        path, _ = QFileDialog.getSaveFileName(parent, title, default_name, filters)
        return path if path else None

    @staticmethod
    def ask_open_file(
        parent: QWidget,
        title: str,
        filters: str,
    ) -> str | None:
        """Show standard open file dialog.

        Args:
            parent: Parent widget.
            title: Dialog title.
            filters: File type filters.

        Returns:
            Selected file path, or None if cancelled.
        """
        path, _ = QFileDialog.getOpenFileName(parent, title, "", filters)
        return path if path else None
