"""
Qt-specific utility functions for layout and widget manipulation.

This module provides low-level Qt utilities for common operations like
clearing layouts, finding child widgets, and managing widget hierarchies.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QLayout, QWidget
from PyQt6.QtCore import QObject


def clear_layout(target_layout: QLayout) -> None:
    """Removes and deletes all widgets from a layout.

    This completely clears the layout by removing all items and deleting
    their associated widgets. Use this when rebuilding a dynamic UI section.

    Args:
        target_layout: The layout to clear.
    """
    while target_layout.count():
        child = target_layout.takeAt(0)
        if child.widget():
            child.widget().deleteLater()


def find_child_by_name(parent: QWidget, name: str) -> QWidget | None:
    """Finds a child widget by its object name.

    Searches recursively through all child widgets to find one with
    the matching objectName property.

    Args:
        parent: Parent widget to search in.
        name: Object name to search for.

    Returns:
        QWidget | None: The found widget, or None if not found.
    """
    return parent.findChild(QWidget, name)


def find_children_by_type(parent: QWidget, widget_type: type) -> list[QWidget]:
    """Finds all child widgets of a specific type.

    Searches recursively through all child widgets and returns all that
    match the specified type.

    Args:
        parent: Parent widget to search in.
        widget_type: The widget class to search for.

    Returns:
        list[QWidget]: List of matching child widgets.
    """
    return parent.findChildren(widget_type)


def remove_widget_from_layout(widget_to_remove: QWidget) -> None:
    """Removes a widget from its parent layout without deleting it.

    The widget is removed from the layout but not deleted, so it can be
    re-added elsewhere or deleted manually later.

    Args:
        widget_to_remove: Widget to remove from its layout.
    """
    parent = widget_to_remove.parent()
    if parent and isinstance(parent, QWidget):
        parent_layout = parent.layout()
        if parent_layout:
            parent_layout.removeWidget(widget_to_remove)


def set_all_widgets_enabled(parent: QWidget, enabled: bool) -> None:
    """Enables or disables all child widgets recursively.

    Useful for disabling an entire section of UI during async operations.

    Args:
        parent: Parent widget whose children should be enabled/disabled.
        enabled: True to enable, False to disable.
    """
    child: QWidget
    for child in parent.findChildren(QWidget):
        child.setEnabled(enabled)


def get_layout_widgets(target_layout: QLayout) -> list[QWidget]:
    """Returns a list of all widgets in a layout.

    Extracts all widgets from the layout without removing them.

    Args:
        target_layout: Layout to extract widgets from.

    Returns:
        list[QWidget]: List of widgets in the layout.
    """
    widgets = []
    for i in range(target_layout.count()):
        layout_item = target_layout.itemAt(i)
        if layout_item and layout_item.widget():
            widgets.append(layout_item.widget())
    return widgets


def hide_all_children(parent: QWidget) -> None:
    """Hides all child widgets recursively.

    Does not disable the widgets, only makes them invisible.

    Args:
        parent: Parent widget whose children should be hidden.
    """
    child: QWidget
    for child in parent.findChildren(QWidget):
        child.hide()


def show_all_children(parent: QWidget) -> None:
    """Shows all child widgets recursively.

    Makes all previously hidden child widgets visible again.

    Args:
        parent: Parent widget whose children should be shown.
    """
    child: QWidget
    for child in parent.findChildren(QWidget):
        child.show()


def disconnect_all_signals(obj: QObject) -> None:
    """Disconnects all signals from a QObject.

    This is a safety measure to prevent signal/slot errors when
    deleting objects or rebuilding UI sections.

    Args:
        obj: QObject to disconnect all signals from.
    """
    try:
        obj.blockSignals(True)
    except RuntimeError:
        # Object already deleted
        pass


def count_visible_widgets(target_layout: QLayout) -> int:
    """Counts how many visible widgets are in a layout.

    Only counts widgets that are currently visible (not hidden).

    Args:
        target_layout: Layout to count visible widgets in.

    Returns:
        int: Number of visible widgets.
    """
    visible_count = 0
    for i in range(target_layout.count()):
        layout_item = target_layout.itemAt(i)
        if layout_item and layout_item.widget() and layout_item.widget().isVisible():
            visible_count += 1
    return visible_count
