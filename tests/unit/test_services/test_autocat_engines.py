"""Tests for the generic AutoCat engines (_categorize_simple, _categorize_by_buckets).

Validates that the generic engines produce the same results as the
original method-specific implementations.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.core.game import Game
from src.services.autocat_configs import (
    BUCKET_METHOD_CONFIGS,
    SIMPLE_METHOD_CONFIGS,
    AutoCatMethodConfig,
    BucketConfig,
)


def _make_service():
    """Creates an AutoCategorizeService with mocked dependencies."""
    from src.services.autocategorize_service import AutoCategorizeService

    service = AutoCategorizeService.__new__(AutoCategorizeService)
    service.game_manager = MagicMock()
    service.category_service = MagicMock()
    service.category_service.add_app_to_category = MagicMock()
    service.steam_scraper = None
    return service


def _make_game(**kwargs) -> Game:
    """Helper to create a Game with given attributes."""
    g = Game(app_id=kwargs.pop("app_id", "1"), name=kwargs.pop("name", "Test"))
    g.categories = []
    for k, v in kwargs.items():
        setattr(g, k, v)
    return g


class TestSimpleEngine:
    """Tests for _categorize_simple generic engine."""

    def test_publisher_via_engine(self) -> None:
        """Publisher categorization works through the engine."""
        service = _make_service()
        games = [_make_game(publisher="Valve")]
        result = service.categorize_by_publisher(games)
        assert result == 1
        service.category_service.add_app_to_category.assert_called_once()

    def test_developer_via_engine(self) -> None:
        """Developer categorization works through the engine."""
        service = _make_service()
        games = [_make_game(developer="id Software")]
        result = service.categorize_by_developer(games)
        assert result == 1

    def test_genre_uses_raw_value(self) -> None:
        """Genre categories use the raw genre name, not wrapped in i18n."""
        service = _make_service()
        games = [_make_game(genres=["Action", "RPG"])]
        result = service.categorize_by_genre(games)
        assert result == 2
        calls = service.category_service.add_app_to_category.call_args_list
        assert calls[0][0][1] == "Action"
        assert calls[1][0][1] == "RPG"

    def test_platform_capitalizes_values(self) -> None:
        """Platform categories capitalize the platform name."""
        service = _make_service()
        games = [_make_game(platforms=["linux", "windows"])]
        result = service.categorize_by_platform(games)
        assert result == 2
        calls = service.category_service.add_app_to_category.call_args_list
        # Category names contain capitalized platform names
        assert "Linux" in calls[0][0][1]
        assert "Windows" in calls[1][0][1]

    def test_year_uses_year_kwarg(self) -> None:
        """Year categorization uses the year kwarg for i18n."""
        service = _make_service()
        games = [_make_game(release_year="2024")]
        result = service.categorize_by_year(games)
        assert result == 1

    def test_language_list_creates_multiple(self) -> None:
        """Language list creates one category per language."""
        service = _make_service()
        games = [_make_game(languages=["English", "German", "French"])]
        result = service.categorize_by_language(games)
        assert result == 3

    def test_vr_capitalizes(self) -> None:
        """VR categorization capitalizes the vr_support value."""
        service = _make_service()
        games = [_make_game(vr_support="required")]
        result = service.categorize_by_vr(games)
        assert result == 1

    def test_empty_attr_skipped(self) -> None:
        """Games with empty/falsy attribute are skipped."""
        service = _make_service()
        games = [_make_game(publisher="")]
        result = service.categorize_by_publisher(games)
        assert result == 0

    def test_none_attr_skipped(self) -> None:
        """Games with None attribute are skipped."""
        service = _make_service()
        game = _make_game()
        game.publisher = None  # type: ignore[assignment]
        result = service.categorize_by_publisher([game])
        assert result == 0

    def test_empty_list_attr_skipped(self) -> None:
        """Games with empty list attribute are skipped."""
        service = _make_service()
        games = [_make_game(genres=[])]
        result = service.categorize_by_genre(games)
        assert result == 0

    def test_progress_callback_invoked(self) -> None:
        """Progress callback is invoked for each game."""
        service = _make_service()
        cb = MagicMock()
        games = [_make_game(publisher="A"), _make_game(app_id="2", publisher="B")]
        service.categorize_by_publisher(games, progress_callback=cb)
        assert cb.call_count == 2

    def test_error_in_category_service_handled(self) -> None:
        """ValueError from category_service does not crash."""
        service = _make_service()
        service.category_service.add_app_to_category.side_effect = ValueError("test")
        games = [_make_game(publisher="Valve")]
        result = service.categorize_by_publisher(games)
        assert result == 0

    def test_unknown_method_key_raises(self) -> None:
        """Unknown method key raises KeyError."""
        service = _make_service()
        with pytest.raises(KeyError):
            service._categorize_simple("nonexistent", [])


class TestBucketEngine:
    """Tests for _categorize_by_buckets generic engine."""

    def test_user_score_high(self) -> None:
        """High review score maps to correct bucket."""
        service = _make_service()
        games = [_make_game(review_percentage=96)]
        result = service.categorize_by_user_score(games)
        assert result == 1

    def test_user_score_zero_skipped(self) -> None:
        """Zero review score is skipped (skip_falsy=True)."""
        service = _make_service()
        games = [_make_game(review_percentage=0)]
        result = service.categorize_by_user_score(games)
        assert result == 0

    def test_hours_never_played(self) -> None:
        """Zero playtime maps to 'Never Played' fallback."""
        service = _make_service()
        games = [_make_game(playtime_minutes=0)]
        result = service.categorize_by_hours_played(games)
        assert result == 1  # Falls to fallback_key, not skipped

    def test_hours_high_playtime(self) -> None:
        """High playtime maps to 100h+ bucket."""
        service = _make_service()
        games = [_make_game(playtime_minutes=7000)]
        result = service.categorize_by_hours_played(games)
        assert result == 1

    def test_hltb_zero_skipped(self) -> None:
        """Zero HLTB value is skipped (skip_falsy=True)."""
        service = _make_service()
        games = [_make_game(hltb_main_story=0.0)]
        result = service.categorize_by_hltb(games)
        assert result == 0

    def test_hltb_short_game(self) -> None:
        """Short game maps to under-5h bucket."""
        service = _make_service()
        games = [_make_game(hltb_main_story=3.5)]
        result = service.categorize_by_hltb(games)
        assert result == 1

    def test_hltb_boundary_5h(self) -> None:
        """Game at exactly 5h boundary falls into 5-15h bucket."""
        service = _make_service()
        games = [_make_game(hltb_main_story=5.0)]
        result = service.categorize_by_hltb(games)
        assert result == 1

    def test_bucket_progress_callback(self) -> None:
        """Progress callback is invoked in bucket engine."""
        service = _make_service()
        cb = MagicMock()
        games = [_make_game(review_percentage=80)]
        service.categorize_by_user_score(games, progress_callback=cb)
        cb.assert_called_once_with(0, "Test")

    def test_bucket_error_handled(self) -> None:
        """ValueError from category_service does not crash."""
        service = _make_service()
        service.category_service.add_app_to_category.side_effect = ValueError("test")
        games = [_make_game(review_percentage=80)]
        result = service.categorize_by_user_score(games)
        assert result == 0

    def test_unknown_bucket_key_raises(self) -> None:
        """Unknown bucket method key raises KeyError."""
        service = _make_service()
        with pytest.raises(KeyError):
            service._categorize_by_buckets("nonexistent", [])


class TestConfigDataclasses:
    """Tests for the frozen config dataclasses."""

    def test_simple_config_frozen(self) -> None:
        """AutoCatMethodConfig is frozen (immutable)."""
        cfg = AutoCatMethodConfig(attr="test")
        with pytest.raises(AttributeError):
            cfg.attr = "changed"  # type: ignore[misc]

    def test_bucket_config_frozen(self) -> None:
        """BucketConfig is frozen (immutable)."""
        cfg = BucketConfig(attr="test", buckets=(), i18n_wrapper_key="test")
        with pytest.raises(AttributeError):
            cfg.attr = "changed"  # type: ignore[misc]

    def test_all_simple_configs_have_valid_keys(self) -> None:
        """All SIMPLE_METHOD_CONFIGS entries have valid attr and i18n_key."""
        for key, cfg in SIMPLE_METHOD_CONFIGS.items():
            assert cfg.attr, f"{key} has empty attr"
            if not cfg.use_raw:
                assert cfg.i18n_key, f"{key} has empty i18n_key"

    def test_all_bucket_configs_have_descending_thresholds(self) -> None:
        """All BUCKET_METHOD_CONFIGS have thresholds in descending order."""
        for key, cfg in BUCKET_METHOD_CONFIGS.items():
            thresholds = [t for t, _ in cfg.buckets]
            assert thresholds == sorted(thresholds, reverse=True), f"{key} thresholds are not in descending order"

    def test_simple_configs_count(self) -> None:
        """Expected number of simple method configs."""
        assert len(SIMPLE_METHOD_CONFIGS) == 7

    def test_bucket_configs_count(self) -> None:
        """Expected number of bucket method configs."""
        assert len(BUCKET_METHOD_CONFIGS) == 3
