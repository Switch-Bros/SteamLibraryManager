#
# steam_library_manager/ui/widgets/ui_helper.py
# Static helpers for standardized QMessageBox / QInputDialog / QFileDialog usage
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

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

from steam_library_manager.utils.i18n import t
from steam_library_manager.version import __app_name__

__all__ = ["UIHelper"]


class UIHelper:
    """Static helpers for common UI dialogs."""

    @staticmethod
    def _show_message(
        parent: QWidget,
        message: str,
        title: str,
        icon: QMessageBox.Icon,
    ) -> None:
        msg = QMessageBox(parent)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(icon)
        msg.addButton(t("common.ok"), QMessageBox.ButtonRole.AcceptRole)
        msg.exec()

    @staticmethod
    def show_error(parent: QWidget, message: str, title: str | None = None) -> None:
        UIHelper._show_message(
            parent,
            message,
            title or t("common.error"),
            QMessageBox.Icon.Critical,
        )

    @staticmethod
    def show_success(parent: QWidget, message: str, title: str | None = None) -> None:
        UIHelper._show_message(
            parent,
            message,
            title or t("common.success"),
            QMessageBox.Icon.Information,
        )

    @staticmethod
    def show_warning(parent: QWidget, message: str, title: str | None = None) -> None:
        UIHelper._show_message(
            parent,
            message,
            title or t("common.warning"),
            QMessageBox.Icon.Warning,
        )

    @staticmethod
    def show_info(parent: QWidget, message: str, title: str | None = None) -> None:
        UIHelper._show_message(
            parent,
            message,
            title or t("common.info"),
            QMessageBox.Icon.Information,
        )

    @staticmethod
    def confirm(parent: QWidget, question: str, title: str | None = None) -> bool:
        """Yes/No dialog. Returns True on Yes.

        Uses addButton() because Qt6/Linux doesn't translate StandardButtons.
        """
        if title is None:
            title = __app_name__

        msg = QMessageBox(parent)
        msg.setWindowTitle(title)
        msg.setText(question)
        msg.setIcon(QMessageBox.Icon.Question)

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
        """Show result with optional force-refresh button. True = refresh clicked."""
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
        """Text input dialog. Returns (text, ok_pressed)."""
        dialog = QDialog(parent)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout()

        label_widget = QLabel(label)
        layout.addWidget(label_widget)

        line_edit = QLineEdit()
        line_edit.setText(current_text)
        layout.addWidget(line_edit)

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
        """Create a modal progress dialog."""
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
        """Show dialog with custom buttons. Returns 0-based button index."""
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
        """Save-file dialog. Returns path or None on cancel."""
        path, _ = QFileDialog.getSaveFileName(parent, title, default_name, filters)
        return path if path else None

    @staticmethod
    def ask_open_file(
        parent: QWidget,
        title: str,
        filters: str,
    ) -> str | None:
        """Open-file dialog. Returns path or None on cancel."""
        path, _ = QFileDialog.getOpenFileName(parent, title, "", filters)
        return path if path else None
