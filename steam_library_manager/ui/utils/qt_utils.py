#
# steam_library_manager/ui/utils/qt_utils.py
# Qt utility functions for widgets and layouts
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from PyQt6.QtWidgets import QWidget

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


def clear_layout(target_layout):
    # remove and delete all widgets from layout
    while target_layout.count():
        child = target_layout.takeAt(0)
        if child.widget():
            child.widget().deleteLater()


def find_child_by_name(parent, name):
    # recursive search by objectName
    return parent.findChild(QWidget, name)


def find_children_by_type(parent, widget_type):
    # all children matching type
    return parent.findChildren(widget_type)


def remove_widget_from_layout(widget_to_remove):
    # remove without deleting
    par = widget_to_remove.parent()
    if par and isinstance(par, QWidget):
        lay = par.layout()
        if lay:
            lay.removeWidget(widget_to_remove)


def set_all_widgets_enabled(parent, enabled):
    # enable/disable all children recursively
    for child in parent.findChildren(QWidget):
        child.setEnabled(enabled)


def get_layout_widgets(target_layout):
    # extract widgets without removing
    out = []
    for i in range(target_layout.count()):
        li = target_layout.itemAt(i)
        if li and li.widget():
            out.append(li.widget())
    return out


def hide_all_children(parent):
    for child in parent.findChildren(QWidget):
        child.hide()


def show_all_children(parent):
    for child in parent.findChildren(QWidget):
        child.show()


def disconnect_all_signals(obj):
    # safety measure before deleting objects
    try:
        obj.blockSignals(True)
    except RuntimeError:
        pass  # already deleted


def count_visible_widgets(target_layout):
    n = 0
    for i in range(target_layout.count()):
        li = target_layout.itemAt(i)
        if li and li.widget() and li.widget().isVisible():
            n += 1
    return n
