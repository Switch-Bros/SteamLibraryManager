"""Tests for animated image loading throttling in ImageSelectionDialog."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _make_dialog_stub():
    """Creates a lightweight stub that has the throttling methods.

    Instead of instantiating the real QDialog subclass (which requires
    a QApplication), we bind the throttling methods to a simple namespace
    that carries the same attributes.
    """
    from src.ui.dialogs.image_selection_dialog import ImageSelectionDialog

    stub = MagicMock()
    stub._animated_load_queue = []
    stub._animated_loading_count = 0
    stub._MAX_CONCURRENT_ANIMATED = 3
    stub._ANIMATED_DELAY_MS = 150

    # Bind the real methods to our stub
    stub._queue_animated_load = lambda widget, url: ImageSelectionDialog._queue_animated_load(stub, widget, url)
    stub._process_animated_queue = lambda: ImageSelectionDialog._process_animated_queue(stub)
    stub._on_animated_load_finished = lambda: ImageSelectionDialog._on_animated_load_finished(stub)
    return stub


def _make_widget() -> MagicMock:
    """Creates a mock ClickableImage widget with load_finished signal."""
    widget = MagicMock()
    widget.load_finished = MagicMock()
    widget.load_finished.connect = MagicMock()
    widget.load_image = MagicMock()
    return widget


class TestImageBrowserThrottling:
    """Tests for the animated image throttling queue."""

    @pytest.fixture
    def dialog(self):
        """Creates a stub with the real throttling methods."""
        return _make_dialog_stub()

    def test_queue_starts_immediately_under_limit(self, dialog) -> None:
        """Queuing fewer than MAX_CONCURRENT should start all immediately."""
        w1 = _make_widget()
        w2 = _make_widget()

        dialog._queue_animated_load(w1, "https://example.com/1.webm")
        dialog._queue_animated_load(w2, "https://example.com/2.webm")

        w1.load_image.assert_called_once_with("https://example.com/1.webm")
        w2.load_image.assert_called_once_with("https://example.com/2.webm")
        assert dialog._animated_loading_count == 2
        assert len(dialog._animated_load_queue) == 0

    def test_queue_caps_at_max_concurrent(self, dialog) -> None:
        """Fourth animated image should be queued, not started immediately."""
        widgets = [_make_widget() for _ in range(4)]

        for i, w in enumerate(widgets):
            dialog._queue_animated_load(w, f"https://example.com/{i}.webm")

        # First 3 started
        for w in widgets[:3]:
            w.load_image.assert_called_once()

        # Fourth is queued, not started
        widgets[3].load_image.assert_not_called()
        assert dialog._animated_loading_count == 3
        assert len(dialog._animated_load_queue) == 1

    def test_completion_starts_queued_item(self, dialog) -> None:
        """When a load finishes, the next queued item should start."""
        widgets = [_make_widget() for _ in range(4)]

        for i, w in enumerate(widgets):
            dialog._queue_animated_load(w, f"https://example.com/{i}.webm")

        # Simulate one load finishing — decrement + process queue
        dialog._animated_loading_count -= 1
        dialog._process_animated_queue()

        widgets[3].load_image.assert_called_once_with("https://example.com/3.webm")
        assert dialog._animated_loading_count == 3  # Back to max
        assert len(dialog._animated_load_queue) == 0

    def test_queue_cleared_on_new_search(self, dialog) -> None:
        """Starting a new search should clear the queue and reset counter."""
        widgets = [_make_widget() for _ in range(5)]

        for i, w in enumerate(widgets):
            dialog._queue_animated_load(w, f"https://example.com/{i}.webm")

        assert len(dialog._animated_load_queue) == 2  # 5 - 3 = 2 queued

        # Simulate what _start_search does
        dialog._animated_load_queue.clear()
        dialog._animated_loading_count = 0

        assert len(dialog._animated_load_queue) == 0
        assert dialog._animated_loading_count == 0

    def test_on_animated_load_finished_decrements_count(self, dialog) -> None:
        """_on_animated_load_finished should decrement counter (min 0)."""
        dialog._animated_loading_count = 2

        with patch("src.ui.dialogs.image_selection_dialog.QTimer") as mock_timer:
            dialog._on_animated_load_finished()

        assert dialog._animated_loading_count == 1
        mock_timer.singleShot.assert_called_once()

    def test_on_animated_load_finished_clamps_to_zero(self, dialog) -> None:
        """Counter should never go below zero."""
        dialog._animated_loading_count = 0

        with patch("src.ui.dialogs.image_selection_dialog.QTimer"):
            dialog._on_animated_load_finished()

        assert dialog._animated_loading_count == 0

    def test_load_finished_signal_connected(self, dialog) -> None:
        """Processing queue should connect load_finished to handler."""
        w = _make_widget()
        dialog._queue_animated_load(w, "https://example.com/anim.webm")

        w.load_finished.connect.assert_called_once()
