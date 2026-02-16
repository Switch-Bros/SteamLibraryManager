# tests/unit/test_utils/test_json_exporter.py

"""Tests for JSONExporter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.core.game import Game
from src.utils.json_exporter import JSONExporter

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_game(
    app_id: str = "1",
    name: str = "TestGame",
    playtime_minutes: int = 0,
    developer: str = "",
    genres: list[str] | None = None,
    platforms: list[str] | None = None,
) -> Game:
    """Helper to create a Game for JSON export tests."""
    return Game(
        app_id=app_id,
        name=name,
        playtime_minutes=playtime_minutes,
        developer=developer,
        genres=genres,
        platforms=platforms,
    )


@pytest.fixture
def sample_games() -> list[Game]:
    """Returns sample games for JSON export."""
    return [
        _make_game(
            "440",
            "Team Fortress 2",
            playtime_minutes=600,
            developer="Valve",
            genres=["Action"],
            platforms=["windows", "linux"],
        ),
        _make_game("570", "Dota 2", playtime_minutes=1200, developer="Valve", genres=["Strategy"]),
    ]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestJSONExporter:
    """Tests for JSONExporter.export()."""

    def test_export_creates_file(self, tmp_path: Path, sample_games: list[Game]) -> None:
        output = tmp_path / "games.json"
        JSONExporter.export(sample_games, output)
        assert output.exists()

    def test_export_valid_json(self, tmp_path: Path, sample_games: list[Game]) -> None:
        output = tmp_path / "games.json"
        JSONExporter.export(sample_games, output)

        with open(output, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        assert "games" in data
        assert "count" in data

    def test_export_correct_count(self, tmp_path: Path, sample_games: list[Game]) -> None:
        output = tmp_path / "games.json"
        JSONExporter.export(sample_games, output)

        with open(output, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        assert data["count"] == 2
        assert len(data["games"]) == 2

    def test_export_game_fields(self, tmp_path: Path) -> None:
        game = _make_game("440", "TF2", developer="Valve", genres=["Action"])
        output = tmp_path / "single.json"
        JSONExporter.export([game], output)

        with open(output, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        entry = data["games"][0]
        assert entry["app_id"] == "440"
        assert entry["name"] == "TF2"
        assert entry["developer"] == "Valve"
        assert entry["genres"] == ["Action"]

    def test_export_empty_list(self, tmp_path: Path) -> None:
        output = tmp_path / "empty.json"
        JSONExporter.export([], output)

        with open(output, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        assert data["count"] == 0
        assert data["games"] == []

    def test_export_creates_parent_dirs(self, tmp_path: Path, sample_games: list[Game]) -> None:
        output = tmp_path / "deep" / "nested" / "games.json"
        JSONExporter.export(sample_games, output)
        assert output.exists()
