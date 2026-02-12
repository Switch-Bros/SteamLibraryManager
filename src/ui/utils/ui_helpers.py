"""
Generic UI helper functions for common widget patterns.

This module provides reusable functions for creating standard UI elements
with consistent styling and behavior across the application.
"""

from __future__ import annotations

from typing import Callable

from PyQt6.QtWidgets import (
    QSplitter,
    QWidget,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QProgressDialog,
    QVBoxLayout,
    QLabel,
)
from PyQt6.QtCore import Qt

from src.utils.i18n import t


def create_splitter(left_widget: QWidget, right_widget: QWidget, ratio: tuple[int, int] = (1, 3)) -> QSplitter:
    """Creates a horizontal QSplitter with two widgets.

    The splitter uses the given ratio to set initial sizes. For example,
    a ratio of (1, 3) means the left widget takes 25% and right takes 75%.

    Args:
        left_widget: Widget for the left pane.
        right_widget: Widget for the right pane.
        ratio: Size ratio as (left_parts, right_parts). Defaults to (1, 3).

    Returns:
        QSplitter: Configured splitter with both widgets.
    """
    splitter = QSplitter(Qt.Orientation.Horizontal)
    splitter.addWidget(left_widget)
    splitter.addWidget(right_widget)

    # Calculate sizes based on ratio (assume 1200px total width)
    total_parts = sum(ratio)
    base_width = 1200
    left_size = int(base_width * ratio[0] / total_parts)
    right_size = int(base_width * ratio[1] / total_parts)

    splitter.setSizes([left_size, right_size])
    splitter.setChildrenCollapsible(False)

    return splitter


def create_search_bar(
    parent: QWidget,
    on_search_callback: Callable[[str], None],
    on_clear_callback: Callable[[], None] | None = None,
    placeholder: str = "",
) -> tuple[QWidget, QLineEdit]:
    """Creates a search bar widget with search field and clear button.

    The search bar consists of a QLineEdit for text input and a clear button
    (X) that appears when text is entered. The search callback is triggered
    on every text change.

    Args:
        parent: Parent widget for the search bar.
        on_search_callback: Function called when search text changes.
        on_clear_callback: Optional function called when clear button is clicked.
        placeholder: Placeholder text for the search field.

    Returns:
        Tuple containing the container widget and the search input field.
    """
    # Container widget
    container = QWidget(parent)
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)

    # Search input field
    search_entry = QLineEdit()
    if placeholder:
        search_entry.setPlaceholderText(placeholder)
    else:
        search_entry.setPlaceholderText(t("ui.search.placeholder"))

    # Clear button (X icon)
    clear_button = QPushButton()
    clear_button.setText("✕")
    clear_button.setFixedSize(30, 30)
    clear_button.setStyleSheet(
        """
        QPushButton {
            border: none;
            background: transparent;
            color: #888;
            font-size: 16px;
        }
        QPushButton:hover {
            color: #fff;
            background: #555;
            border-radius: 15px;
        }
    """
    )
    clear_button.setToolTip(t("ui.search.clear"))

    # Initially hide clear button
    clear_button.hide()

    # Connect signals
    def on_text_changed(text: str):
        # Show/hide clear button based on text
        if text:
            clear_button.show()
        else:
            clear_button.hide()

        # Trigger search callback
        on_search_callback(text)

    def on_clear():
        search_entry.clear()
        if on_clear_callback:
            on_clear_callback()

    search_entry.textChanged.connect(on_text_changed)
    clear_button.clicked.connect(on_clear)

    # Add to layout
    layout.addWidget(search_entry)
    layout.addWidget(clear_button)

    return container, search_entry


def create_progress_dialog(
    parent: QWidget, title: str, message: str, maximum: int = 100, cancelable: bool = True
) -> QProgressDialog:
    """Creates a standardized progress dialog with consistent styling.

    The dialog uses the application's standard styling and i18n for buttons.
    It can be made non-cancelable for critical operations.

    Args:
        parent: Parent widget for the dialog.
        title: Window title for the progress dialog.
        message: Initial message text shown above the progress bar.
        maximum: Maximum value for the progress bar. Defaults to 100.
        cancelable: Whether the user can cancel the operation. Defaults to True.

    Returns:
        QProgressDialog: Configured progress dialog ready to show.
    """
    dialog = QProgressDialog(message, t("common.cancel") if cancelable else "", 0, maximum, parent)
    dialog.setWindowTitle(title)
    dialog.setWindowModality(Qt.WindowModality.WindowModal)
    dialog.setMinimumDuration(0)  # Show immediately

    if not cancelable:
        dialog.setCancelButton(None)

    # Style the progress bar
    dialog.setStyleSheet(
        """
        QProgressDialog {
            min-width: 400px;
            min-height: 100px;
        }
        QProgressBar {
            border: 1px solid #555;
            border-radius: 5px;
            text-align: center;
            background: #2b2b2b;
        }
        QProgressBar::chunk {
            background: #4a9eff;
            border-radius: 4px;
        }
    """
    )

    return dialog


def create_labeled_widget(label_text: str, widget: QWidget, layout_direction: str = "horizontal") -> QWidget:
    """Creates a labeled widget container with flexible layout.

    Combines a label and any widget into a single container with either
    horizontal (label on left) or vertical (label on top) layout.

    Args:
        label_text: Text for the label.
        widget: Widget to be labeled.
        layout_direction: Either "horizontal" or "vertical". Defaults to "horizontal".

    Returns:
        QWidget: Container with label and widget.
    """
    container = QWidget()

    if layout_direction == "horizontal":
        widget_layout = QHBoxLayout(container)
        widget_layout.setContentsMargins(0, 0, 0, 0)
    else:
        widget_layout = QVBoxLayout(container)
        widget_layout.setContentsMargins(0, 0, 0, 5)

    label = QLabel(label_text)
    label.setStyleSheet("color: #888;")

    widget_layout.addWidget(label)
    widget_layout.addWidget(widget)

    if layout_direction == "horizontal":
        widget_layout.setStretch(1, 1)  # Widget takes remaining space

    return container


def set_widget_margins(widget: QWidget, margins: tuple[int, int, int, int] = (0, 0, 0, 0)) -> None:
    """Sets margins on a widget with consistent parameter order.

    Args:
        widget: Widget to set margins on.
        margins: Margins as (left, top, right, bottom). Defaults to (0, 0, 0, 0).
    """
    widget.setContentsMargins(*margins)


def apply_dark_theme_to_widget(widget: QWidget) -> None:
    """Applies a consistent dark theme stylesheet to a widget.

    Uses the application's standard dark color scheme for consistency.

    Args:
        widget: Widget to apply dark theme to.
    """
    widget.setStyleSheet(
        """
        QWidget {
            background-color: #2b2b2b;
            color: #e0e0e0;
        }
        QLineEdit, QTextEdit, QPlainTextEdit {
            background-color: #1e1e1e;
            border: 1px solid #555;
            border-radius: 3px;
            padding: 5px;
            color: #e0e0e0;
        }
        QPushButton {
            background-color: #3a3a3a;
            border: 1px solid #555;
            border-radius: 3px;
            padding: 5px 15px;
            color: #e0e0e0;
        }
        QPushButton:hover {
            background-color: #4a4a4a;
        }
        QPushButton:pressed {
            background-color: #2a2a2a;
        }
        QLabel {
            color: #e0e0e0;
        }
    """
    )


def ask_save_changes(parent: QWidget, save_callback: Callable[[], bool]) -> bool:
    """Shows a 3-button save changes dialog on close.

    Handles the complete flow:
    1. Ask: Save / Discard / Cancel
    2. If Save fails: Ask retry or close anyway

    Args:
        parent: Parent widget for dialogs.
        save_callback: Function to call to save (returns True on success).

    Returns:
        bool: True to close window, False to stay open.
    """
    from PyQt6.QtWidgets import QMessageBox
    from src.utils.i18n import t

    # === 3-BUTTON DIALOG: Save / Discard / Cancel ===
    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Icon.Question)
    msg.setWindowTitle(t("ui.menu.file.unsaved_changes_title"))
    msg.setText(t("ui.menu.file.unsaved_changes_msg"))

    save_btn = msg.addButton(t("common.save"), QMessageBox.ButtonRole.AcceptRole)
    discard_btn = msg.addButton(t("common.discard"), QMessageBox.ButtonRole.DestructiveRole)
    msg.addButton(t("common.cancel"), QMessageBox.ButtonRole.RejectRole)
    msg.setDefaultButton(save_btn)

    msg.exec()
    clicked = msg.clickedButton()

    if clicked == save_btn:
        # Try to save
        if save_callback():
            return True  # Close

        # === SAVE FAILED - RETRY DIALOG ===
        retry_msg = QMessageBox(parent)
        retry_msg.setIcon(QMessageBox.Icon.Warning)
        retry_msg.setWindowTitle(t("ui.menu.file.save_failed_title"))
        retry_msg.setText(t("ui.menu.file.save_failed_msg"))

        yes_btn = retry_msg.addButton(t("common.yes"), QMessageBox.ButtonRole.YesRole)
        retry_msg.addButton(t("common.no"), QMessageBox.ButtonRole.NoRole)
        retry_msg.setDefaultButton(yes_btn)

        retry_msg.exec()
        return retry_msg.clickedButton() == yes_btn  # Close anyway if Yes

    elif clicked == discard_btn:
        return True  # Close without saving

    else:
        return False  # Cancel - stay open
