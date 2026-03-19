"""Tests for animated image loading throttling in ImageSelectionDialog."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _make_dialog_stub():
    # stub with real throttling methods
    from steam_library_manager.ui.dialogs.image_selection_dialog import ImageSelectionDialog

    stub = MagicMock()
    stub._aq = []
    stub._aa = 0
    stub._MAXA = 3
    stub._DA = 150

    stub._q_anim = lambda widget, url: ImageSelectionDialog._q_anim(stub, widget, url)
    stub._d_anim = lambda: ImageSelectionDialog._d_anim(stub)
    stub._on_a_done = lambda: ImageSelectionDialog._on_a_done(stub)
    return stub


def _make_widget():
    w = MagicMock()
    w.load_finished = MagicMock()
    w.load_finished.connect = MagicMock()
    w.load_image = MagicMock()
    return w


class TestImageBrowserThrottling:

    @pytest.fixture
    def dialog(self):
        return _make_dialog_stub()

    def test_queue_starts_immediately_under_limit(self, dialog):
        w1 = _make_widget()
        w2 = _make_widget()

        dialog._q_anim(w1, "https://example.com/1.webm")
        dialog._q_anim(w2, "https://example.com/2.webm")

        w1.load_image.assert_called_once_with("https://example.com/1.webm")
        w2.load_image.assert_called_once_with("https://example.com/2.webm")
        assert dialog._aa == 2
        assert len(dialog._aq) == 0

    def test_queue_caps_at_max_concurrent(self, dialog):
        widgets = [_make_widget() for _ in range(4)]

        for i, w in enumerate(widgets):
            dialog._q_anim(w, "https://example.com/%d.webm" % i)

        for w in widgets[:3]:
            w.load_image.assert_called_once()

        widgets[3].load_image.assert_not_called()
        assert dialog._aa == 3
        assert len(dialog._aq) == 1

    def test_completion_starts_queued_item(self, dialog):
        widgets = [_make_widget() for _ in range(4)]

        for i, w in enumerate(widgets):
            dialog._q_anim(w, "https://example.com/%d.webm" % i)

        dialog._aa -= 1
        dialog._d_anim()

        widgets[3].load_image.assert_called_once_with("https://example.com/3.webm")
        assert dialog._aa == 3
        assert len(dialog._aq) == 0

    def test_queue_cleared_on_new_search(self, dialog):
        widgets = [_make_widget() for _ in range(5)]

        for i, w in enumerate(widgets):
            dialog._q_anim(w, "https://example.com/%d.webm" % i)

        assert len(dialog._aq) == 2

        dialog._aq.clear()
        dialog._aa = 0

        assert len(dialog._aq) == 0
        assert dialog._aa == 0

    def test_on_anim_done_decrements_count(self, dialog):
        dialog._aa = 2

        with patch("steam_library_manager.ui.dialogs.image_selection_dialog.QTimer") as mt:
            dialog._on_a_done()

        assert dialog._aa == 1
        mt.singleShot.assert_called_once()

    def test_on_anim_done_clamps_to_zero(self, dialog):
        dialog._aa = 0

        with patch("steam_library_manager.ui.dialogs.image_selection_dialog.QTimer"):
            dialog._on_a_done()

        assert dialog._aa == 0

    def test_load_finished_signal_connected(self, dialog):
        w = _make_widget()
        dialog._q_anim(w, "https://example.com/anim.webm")

        w.load_finished.connect.assert_called_once()
