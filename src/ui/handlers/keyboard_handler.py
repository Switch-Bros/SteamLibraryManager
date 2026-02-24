"""Keyboard shortcut and Easter egg handler for MainWindow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QKeyEvent, QKeySequence, QShortcut, QWindow
from PyQt6.QtWidgets import QApplication

from src.ui.widgets.ui_helper import UIHelper
from src.utils.enigma import EasterEggManager
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow

__all__ = ["KeyboardHandler"]


class KeyboardHandler:
    """Manages keyboard shortcuts, key events, and Easter egg delegation.

    Easter egg detection is handled by EasterEggManager (enigma.py).
    This class handles: Ctrl+F/A/B/I, F2/F5, ESC layers, Del, Space.

    Attributes:
        _mw: The parent MainWindow instance.
    """

    def __init__(self, mw: MainWindow) -> None:
        self._mw = mw
        self._egg_manager = EasterEggManager(mw)

    def register_shortcuts(self) -> None:
        """Registers keyboard shortcuts not bound to menu actions."""
        mw = self._mw
        QShortcut(QKeySequence("Ctrl+F"), mw).activated.connect(lambda: mw.search_entry.setFocus())
        QShortcut(QKeySequence("F5"), mw).activated.connect(mw.file_actions.refresh_data)
        QShortcut(QKeySequence("Ctrl+Shift+S"), mw).activated.connect(mw.file_actions.export_db_backup)
        QShortcut(QKeySequence("Ctrl+A"), mw).activated.connect(self._select_all_in_category)
        QShortcut(QKeySequence("Ctrl+B"), mw).activated.connect(lambda: mw.tree.setVisible(not mw.tree.isVisible()))
        QShortcut(QKeySequence("Ctrl+I"), mw).activated.connect(self._open_image_browser)

    def install_event_filter(self) -> None:
        """Installs application-wide event filter for Easter egg detection."""
        app = QApplication.instance()
        if app:
            app.installEventFilter(self._mw)

    def remove_event_filter(self) -> None:
        """Removes the application-wide event filter."""
        app = QApplication.instance()
        if app:
            app.removeEventFilter(self._mw)

    def handle_event_filter(self, obj: object, event: QEvent) -> bool:
        """Processes application-wide key events for Easter egg detection.

        Args:
            obj: The object that received the event.
            event: The event to filter.

        Returns:
            False always — never consumes the event.
        """
        if (
            isinstance(obj, QWindow)
            and event.type() == QEvent.Type.KeyPress
            and isinstance(event, QKeyEvent)
            and not event.isAutoRepeat()
        ):
            self._egg_manager.on_key_event(int(event.key()))
        return False

    def handle_key_press(self, event: QKeyEvent) -> bool:
        """Handles key press events for MainWindow shortcuts.

        Args:
            event: The key press event.

        Returns:
            True if event was handled, False to pass through.
        """
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
                categories = mw.tree.get_selected_categories()
                if categories:
                    category = categories[0]
                    count = len(mw.selected_games)
                    msg = t("ui.dialogs.confirm_bulk", count=count)
                    if UIHelper.confirm(mw, msg, category):
                        mw.category_change_handler.apply_category_to_games(mw.selected_games, category, False)
                        mw.category_populator.populate()
            return True

        if key == Qt.Key.Key_F2:
            categories = mw.tree.get_selected_categories()
            if categories:
                mw.category_handler.rename_category(categories[0])
            return True

        if key == Qt.Key.Key_Space:
            if not mw.tree.hasFocus():
                mw.details_widget.setVisible(not mw.details_widget.isVisible())
                return True

        return False

    # --- Private helpers ---

    def _select_all_in_category(self) -> None:
        """Selects all game items under the currently active category."""
        mw = self._mw
        if mw.search_entry.hasFocus():
            mw.search_entry.selectAll()
            return
        categories = mw.tree.get_selected_categories()
        if not categories:
            return
        for i in range(mw.tree.topLevelItemCount()):
            item = mw.tree.topLevelItem(i)
            if item and item.text(0) in categories:
                for j in range(item.childCount()):
                    child = item.child(j)
                    if child:
                        child.setSelected(True)

    def _open_image_browser(self) -> None:
        """Opens the Image Browser for the currently selected game."""
        if not self._mw.selected_game:
            self._mw.set_status(t("ui.errors.no_selection"))
            return
        self._mw.details_widget.on_image_click("grids")
