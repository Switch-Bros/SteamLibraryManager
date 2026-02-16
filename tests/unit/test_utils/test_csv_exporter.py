# tests/unit/test_utils/test_csv_exporter.py

"""Tests for CSVExporter simple and full export."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.core.game import Game
from src.utils.csv_exporter import CSVExporter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_game(
    app_id: str = "1",
    name: str = "TestGame",
    playtime_minutes: int = 0,
    developer: str = "",
    publisher: str = "",
    release_year: str = "",
    genres: list[str] | None = None,
    tags: list[str] | None = None,
    categories: list[str] | None = None,
    platforms: list[str] | None = None,
) -> Game:
    """Helper to create a Game for export tests."""
    return Game(
        app_id=app_id,
        name=name,
        playtime_minutes=playtime_minutes,
        developer=developer,
        publisher=publisher,
        release_year=release_year,
        genres=genres,
        tags=tags,
        categories=categories,
        platforms=platforms,
    )


@pytest.fixture
def sample_games() -> list[Game]:
    """Returns sample games for CSV export."""
    return [
        _make_game(
            "440",
            "Team Fortress 2",
            playtime_minutes=600,
            developer="Valve",
            publisher="Valve",
            release_year="2007",
            genres=["Action"],
            platforms=["windows", "linux"],
        ),
        _make_game(
            "570",
            "Dota 2",
            playtime_minutes=1200,
            developer="Valve",
            publisher="Valve",
            release_year="2013",
            genres=["Strategy"],
            platforms=["windows", "linux"],
        ),
    ]


# ---------------------------------------------------------------------------
# Simple export
# ---------------------------------------------------------------------------


class TestCSVSimpleExport:
    """Tests for CSVExporter.export_simple()."""

    def test_export_simple_creates_file(self, tmp_path: Path, sample_games: list[Game]) -> None:
        output = tmp_path / "simple.csv"
        CSVExporter.export_simple(sample_games, output)
        assert output.exists()

    def test_export_simple_has_correct_headers(self, tmp_path: Path, sample_games: list[Game]) -> None:
        output = tmp_path / "simple.csv"
        CSVExporter.export_simple(sample_games, output)

        with open(output, "r", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            headers = next(reader)
        assert headers == ["Name", "App ID", "Playtime (hours)"]

    def test_export_simple_correct_row_count(self, tmp_path: Path, sample_games: list[Game]) -> None:
        output = tmp_path / "simple.csv"
        CSVExporter.export_simple(sample_games, output)

        with open(output, "r", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            rows = list(reader)
        assert len(rows) == 3  # header + 2 games

    def test_export_simple_empty_list(self, tmp_path: Path) -> None:
        output = tmp_path / "empty.csv"
        CSVExporter.export_simple([], output)
        assert output.exists()

        with open(output, "r", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            rows = list(reader)
        assert len(rows) == 1  # header only

    def test_export_simple_creates_parent_dirs(self, tmp_path: Path, sample_games: list[Game]) -> None:
        output = tmp_path / "sub" / "dir" / "simple.csv"
        CSVExporter.export_simple(sample_games, output)
        assert output.exists()


# ---------------------------------------------------------------------------
# Full export
# ---------------------------------------------------------------------------


class TestCSVFullExport:
    """Tests for CSVExporter.export_full()."""

    def test_export_full_creates_file(self, tmp_path: Path, sample_games: list[Game]) -> None:
        output = tmp_path / "full.csv"
        CSVExporter.export_full(sample_games, output)
        assert output.exists()

    def test_export_full_has_all_headers(self, tmp_path: Path, sample_games: list[Game]) -> None:
        output = tmp_path / "full.csv"
        CSVExporter.export_full(sample_games, output)

        with open(output, "r", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            headers = next(reader)
        assert "Name" in headers
        assert "Developer" in headers
        assert "HLTB Main (hours)" in headers
        assert len(headers) == 22

    def test_export_full_correct_row_count(self, tmp_path: Path, sample_games: list[Game]) -> None:
        output = tmp_path / "full.csv"
        CSVExporter.export_full(sample_games, output)

        with open(output, "r", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            rows = list(reader)
        assert len(rows) == 3  # header + 2 games

    def test_export_full_genres_semicolon_separated(self, tmp_path: Path) -> None:
        game = _make_game("1", "Multi Genre", genres=["Action", "RPG", "Adventure"])
        output = tmp_path / "genres.csv"
        CSVExporter.export_full([game], output)

        with open(output, "r", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            next(reader)  # skip header
            row = next(reader)
        # Genres column should have semicolon-separated values
        assert "Action; RPG; Adventure" in row
