#
# steam_library_manager/ui/utils/qt_utils.py
# Low-level Qt utilities for layout and widget manipulation.
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from PyQt6.QtWidgets import QLayout, QWidget
from PyQt6.QtCore import QObject

__all__ = [
    "clear_layout",
    "count_visible_widgets",
    "disconnect_all_signals",
    "find_child_by_name",
    "find_children_by_type",
    "get_layout_widgets",
    "hide_all_children",
    "remove_widget_from_layout",
    "set_all_widgets_enabled",
    "show_all_children",
]


def clear_layout(target_layout: QLayout) -> None:
    """Remove and delete all widgets from a layout."""
    while target_layout.count():
        child = target_layout.takeAt(0)
        if child.widget():
            child.widget().deleteLater()


def find_child_by_name(parent: QWidget, name: str) -> QWidget | None:
    """Find a child widget by its object name (recursive)."""
    return parent.findChild(QWidget, name)


def find_children_by_type(parent: QWidget, widget_type: type) -> list[QWidget]:
    """Find all child widgets of a specific type (recursive)."""
    return parent.findChildren(widget_type)


def remove_widget_from_layout(widget_to_remove: QWidget) -> None:
    """Remove a widget from its parent layout without deleting it."""
    parent = widget_to_remove.parent()
    if parent and isinstance(parent, QWidget):
        parent_layout = parent.layout()
        if parent_layout:
            parent_layout.removeWidget(widget_to_remove)


def set_all_widgets_enabled(parent: QWidget, enabled: bool) -> None:
    """Enable or disable all child widgets recursively."""
    child: QWidget
    for child in parent.findChildren(QWidget):
        child.setEnabled(enabled)


def get_layout_widgets(target_layout: QLayout) -> list[QWidget]:
    """Return all widgets in a layout without removing them."""
    widgets = []
    for i in range(target_layout.count()):
        layout_item = target_layout.itemAt(i)
        if layout_item and layout_item.widget():
            widgets.append(layout_item.widget())
    return widgets


def hide_all_children(parent: QWidget) -> None:
    """Hide all child widgets recursively."""
    child: QWidget
    for child in parent.findChildren(QWidget):
        child.hide()


def show_all_children(parent: QWidget) -> None:
    """Show all child widgets recursively."""
    child: QWidget
    for child in parent.findChildren(QWidget):
        child.show()


def disconnect_all_signals(obj: QObject) -> None:
    """Block all signals on a QObject to prevent slot errors during teardown."""
    try:
        obj.blockSignals(True)
    except RuntimeError:
        pass


def count_visible_widgets(target_layout: QLayout) -> int:
    """Count visible widgets in a layout."""
    visible_count = 0
    for i in range(target_layout.count()):
        layout_item = target_layout.itemAt(i)
        if layout_item and layout_item.widget() and layout_item.widget().isVisible():
            visible_count += 1
    return visible_count
