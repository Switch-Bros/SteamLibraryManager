#
# steam_library_manager/ui/handlers/keyboard_handler.py
# Keyboard shortcut handler for main window actions
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QKeyEvent, QKeySequence, QShortcut, QWindow
from PyQt6.QtWidgets import QApplication

from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.enigma import EasterEggManager
from steam_library_manager.utils.i18n import t

__all__ = ["KeyboardHandler"]


class KeyboardHandler:
    """Keyboard shortcuts, key events, and Easter egg delegation.
    Handles Ctrl+F/A/B/I, F2/F5, ESC layers, Del, Space.
    """

    def __init__(self, mw):
        self._mw = mw
        self._egg_mgr = EasterEggManager(mw)

    def register_shortcuts(self):
        # Register keyboard shortcuts not bound to menu actions
        mw = self._mw
        QShortcut(QKeySequence("Ctrl+F"), mw).activated.connect(lambda: mw.search_entry.setFocus())
        QShortcut(QKeySequence("F5"), mw).activated.connect(mw.file_actions.refresh_data)
        QShortcut(QKeySequence("Ctrl+Shift+S"), mw).activated.connect(mw.file_actions.export_db_backup)
        QShortcut(QKeySequence("Ctrl+A"), mw).activated.connect(self._sel_all)
        QShortcut(QKeySequence("Ctrl+B"), mw).activated.connect(lambda: mw.tree.setVisible(not mw.tree.isVisible()))
        QShortcut(QKeySequence("Ctrl+I"), mw).activated.connect(self._open_imgs)

    def install_event_filter(self):
        # Install application-wide event filter for Easter egg detection
        app = QApplication.instance()
        if app:
            app.installEventFilter(self._mw)

    def remove_event_filter(self):
        # Remove the application-wide event filter
        app = QApplication.instance()
        if app:
            app.removeEventFilter(self._mw)

    def handle_event_filter(self, obj, event):
        # Process app-wide key events for Easter egg detection. Never consumes.
        if (
            isinstance(obj, QWindow)
            and event.type() == QEvent.Type.KeyPress
            and isinstance(event, QKeyEvent)
            and not event.isAutoRepeat()
        ):
            self._egg_mgr.on_key_event(int(event.key()))
        return False

    def handle_key_press(self, event):
        # Handle key press events for MainWindow shortcuts
        mw = self._mw
        key = event.key()

        if key == Qt.Key.Key_Escape:
            if mw.search_entry.text():
                mw.search_entry.clear()
                mw.category_populator.populate()
                return True
            if mw.selected_games:
                mw.selected_games = []
                mw.tree.clearSelection()
                mw.details_widget.clear()
                mw.set_status(t("ui.main_window.status_ready"))
            return True

        if key == Qt.Key.Key_Delete:
            if mw.selected_games:
                cats = mw.tree.get_selected_categories()
                if cats:
                    cat = cats[0]
                    n = len(mw.selected_games)
                    msg = t("ui.dialogs.confirm_bulk", count=n)
                    if UIHelper.confirm(mw, msg, cat):
                        mw.category_change_handler.apply_category_to_games(mw.selected_games, cat, False)
                        mw.category_populator.populate()
            return True

        if key == Qt.Key.Key_F2:
            cats = mw.tree.get_selected_categories()
            if cats:
                mw.category_handler.rename_category(cats[0])
            return True

        if key == Qt.Key.Key_Space:
            if not mw.tree.hasFocus():
                mw.details_widget.setVisible(not mw.details_widget.isVisible())
                return True

        return False

    # --- Private helpers ---

    def _sel_all(self):
        # Select all game items under the active category
        mw = self._mw
        if mw.search_entry.hasFocus():
            mw.search_entry.selectAll()
            return
        cats = mw.tree.get_selected_categories()
        if not cats:
            return
        for i in range(mw.tree.topLevelItemCount()):
            item = mw.tree.topLevelItem(i)
            if item and item.text(0) in cats:
                for j in range(item.childCount()):
                    child = item.child(j)
                    if child:
                        child.setSelected(True)

    def _open_imgs(self):
        # Open Image Browser for the currently selected game
        if not self._mw.selected_game:
            self._mw.set_status(t("ui.errors.no_selection"))
            return
        self._mw.details_widget.on_image_click("grids")
