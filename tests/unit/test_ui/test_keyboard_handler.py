"""Tests for KeyboardHandler."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QKeyEvent


class TestKeyboardHandlerKeyPress:
    """Tests for handle_key_press delegation."""

    def _make_handler(self):
        """Creates a KeyboardHandler with a mocked MainWindow."""
        with patch("src.ui.handlers.keyboard_handler.EasterEggManager"):
            from src.ui.handlers.keyboard_handler import KeyboardHandler

            mw = MagicMock()
            mw.search_entry.text.return_value = ""
            mw.selected_games = []
            handler = KeyboardHandler(mw)
        return handler, mw

    def test_escape_clears_search(self):
        """ESC clears search bar when it has text."""
        handler, mw = self._make_handler()
        mw.search_entry.text.return_value = "test"
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        result = handler.handle_key_press(event)
        assert result is True
        mw.search_entry.clear.assert_called_once()

    def test_escape_clears_selection(self):
        """ESC clears game selection when no search text."""
        handler, mw = self._make_handler()
        mw.search_entry.text.return_value = ""
        mw.selected_games = [MagicMock()]
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier)
        result = handler.handle_key_press(event)
        assert result is True
        assert mw.selected_games == []

    def test_f2_renames_category(self):
        """F2 triggers category rename."""
        handler, mw = self._make_handler()
        mw.tree.get_selected_categories.return_value = ["Action"]
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_F2, Qt.KeyboardModifier.NoModifier)
        result = handler.handle_key_press(event)
        assert result is True
        mw.category_handler.rename_category.assert_called_once_with("Action")

    def test_unhandled_key_returns_false(self):
        """Unhandled keys return False for pass-through."""
        handler, mw = self._make_handler()
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_A, Qt.KeyboardModifier.NoModifier)
        result = handler.handle_key_press(event)
        assert result is False
