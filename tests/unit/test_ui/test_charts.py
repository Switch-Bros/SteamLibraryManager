#
# tests/unit/test_ui/test_charts.py
# Tests for chart engine: ChartSlice, palettes, semantic colors, chart widgets
#

import pytest

from steam_library_manager.services.chart_data import ChartSlice, CHART_PALETTE, SEMANTIC_COLORS


def test_chart_slice_default_color_none():
    s = ChartSlice(label="Test", value=42.0)
    assert s.color is None


def test_chart_slice_with_value():
    s = ChartSlice(label="Action", value=100.0)
    assert s.label == "Action"
    assert s.value == 100.0


def test_palette_has_12_colors():
    assert len(CHART_PALETTE) == 12


def test_palette_all_hex():
    for c in CHART_PALETTE:
        assert c.startswith("#")
        assert len(c) == 7


def test_semantic_colors_deck_status():
    assert "verified" in SEMANTIC_COLORS
    assert "playable" in SEMANTIC_COLORS
    assert "unsupported" in SEMANTIC_COLORS


def test_semantic_colors_protondb():
    assert "platinum" in SEMANTIC_COLORS
    assert "gold" in SEMANTIC_COLORS
    assert "borked" in SEMANTIC_COLORS


def test_semantic_colors_perfect():
    assert SEMANTIC_COLORS["perfect"] == "#FDE100"


# -- Qt-dependent tests --

try:
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    HAS_QT = True
except Exception:
    HAS_QT = False

needs_qt = pytest.mark.skipif(not HAS_QT, reason="No Qt display available")


@needs_qt
def test_base_chart_set_data_assigns_colors():
    from steam_library_manager.ui.widgets.charts.base_chart import BaseChart

    chart = BaseChart()
    slices = [ChartSlice("A", 10), ChartSlice("B", 20)]
    chart.set_data(slices)
    assert chart._slices[0].color is not None
    assert chart._slices[1].color is not None


@needs_qt
def test_base_chart_total():
    from steam_library_manager.ui.widgets.charts.base_chart import BaseChart

    chart = BaseChart()
    chart.set_data([ChartSlice("A", 30), ChartSlice("B", 70)])
    assert chart._total() == 100.0


@needs_qt
def test_base_chart_total_empty():
    from steam_library_manager.ui.widgets.charts.base_chart import BaseChart

    chart = BaseChart()
    assert chart._total() == 1.0  # avoid division by zero


@needs_qt
def test_donut_chart_minimum_size():
    from steam_library_manager.ui.widgets.charts.donut_chart import DonutChart

    chart = DonutChart()
    assert chart.minimumSize().width() >= 200
    assert chart.minimumSize().height() >= 200


@needs_qt
def test_bar_chart_minimum_size():
    from steam_library_manager.ui.widgets.charts.bar_chart import BarChart

    chart = BarChart()
    assert chart.minimumSize().width() >= 200
    assert chart.minimumSize().height() >= 200
