# tests/unit/test_game_manager_uncategorized.py

"""
Unit tests for GameManager.get_uncategorized_games() method.

Tests the fix for UNCATEGORIZED games logic:
- System categories (Favorites, Hidden) should NOT count as "categorized"
- Only user-created collections should remove a game from Uncategorized
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from src.core.game_manager import GameManager, Game


@pytest.fixture
def game_manager():
    """Create a minimal GameManager instance for testing."""
    # Mock dependencies to avoid real API calls / file I/O
    with patch("src.core.game_manager.MetadataEnrichmentService"), patch("src.core.game_manager.GameDetailService"):
        manager = GameManager(steam_api_key=None, cache_dir=Path("/tmp/test_cache"), steam_path=Path("/tmp/test_steam"))

        # Disable NON_GAME filtering for tests (we want all games)
        manager.filter_non_games = False

        return manager


@pytest.fixture
def sample_games(game_manager):
    """Create test games with different category combinations."""
    # Game 1: NO categories (should be uncategorized)
    game1 = Game(app_id="100", name="Game No Categories")
    game1.categories = []

    # Game 2: ONLY Favorites (should be uncategorized)
    game2 = Game(app_id="200", name="Game Only Favorites")
    game2.categories = ["Favorites"]  # Will be translated by t() in real code

    # Game 3: ONLY Hidden (should be uncategorized)
    game3 = Game(app_id="300", name="Game Only Hidden")
    game3.categories = ["Hidden"]  # Will be translated by t() in real code

    # Game 4: Favorites AND Hidden (should be uncategorized)
    game4 = Game(app_id="400", name="Game Favorites and Hidden")
    game4.categories = ["Favorites", "Hidden"]

    # Game 5: User category "Action" (should NOT be uncategorized)
    game5 = Game(app_id="500", name="Game With Action Category")
    game5.categories = ["Action"]

    # Game 6: Favorites + User category (should NOT be uncategorized)
    game6 = Game(app_id="600", name="Game Favorites and Action")
    game6.categories = ["Favorites", "Action"]

    # Game 7: Hidden + User category (should NOT be uncategorized)
    game7 = Game(app_id="700", name="Game Hidden and RPG")
    game7.categories = ["Hidden", "RPG"]

    # Game 8: All three (should NOT be uncategorized)
    game8 = Game(app_id="800", name="Game All Categories")
    game8.categories = ["Favorites", "Hidden", "Strategy"]

    # Add all games to manager
    for game in [game1, game2, game3, game4, game5, game6, game7, game8]:
        game_manager.games[game.app_id] = game

    return {
        "no_categories": game1,
        "only_favorites": game2,
        "only_hidden": game3,
        "favorites_and_hidden": game4,
        "action": game5,
        "favorites_and_action": game6,
        "hidden_and_rpg": game7,
        "all_categories": game8,
    }


# ==================================================================
# CORE UNCATEGORIZED LOGIC TESTS
# ==================================================================


@patch("src.core.game_manager.t")
def test_uncategorized_no_categories(mock_t, game_manager, sample_games):
    """Test: Game with NO categories is uncategorized."""
    # Setup i18n mock
    mock_t.side_effect = lambda key: {"ui.categories.favorites": "Favorites", "ui.categories.hidden": "Hidden"}.get(
        key, key
    )

    # Execute
    uncategorized = game_manager.get_uncategorized_games()

    # Assert
    assert sample_games["no_categories"] in uncategorized


@patch("src.core.game_manager.t")
def test_uncategorized_only_favorites(mock_t, game_manager, sample_games):
    """Test: Game with ONLY Favorites is still uncategorized (Favorites is a system category)."""
    # Setup i18n mock
    mock_t.side_effect = lambda key: {"ui.categories.favorites": "Favorites", "ui.categories.hidden": "Hidden"}.get(
        key, key
    )

    # Execute
    uncategorized = game_manager.get_uncategorized_games()

    # Assert
    assert sample_games["only_favorites"] in uncategorized


@patch("src.core.game_manager.t")
def test_uncategorized_only_hidden(mock_t, game_manager, sample_games):
    """Test: Game with ONLY Hidden is still uncategorized (Hidden is a system category).

    This is the PRIMARY FIX! Before the fix, this test would FAIL.
    """
    # Setup i18n mock
    mock_t.side_effect = lambda key: {"ui.categories.favorites": "Favorites", "ui.categories.hidden": "Hidden"}.get(
        key, key
    )

    # Execute
    uncategorized = game_manager.get_uncategorized_games()

    # Assert
    assert (
        sample_games["only_hidden"] in uncategorized
    ), "CRITICAL BUG: Games with ONLY 'Hidden' should be uncategorized!"


@patch("src.core.game_manager.t")
def test_uncategorized_favorites_and_hidden(mock_t, game_manager, sample_games):
    """Test: Game with Favorites AND Hidden is still uncategorized (both are system categories).

    This is the SECONDARY FIX! Before the fix, this test would FAIL.
    """
    # Setup i18n mock
    mock_t.side_effect = lambda key: {"ui.categories.favorites": "Favorites", "ui.categories.hidden": "Hidden"}.get(
        key, key
    )

    # Execute
    uncategorized = game_manager.get_uncategorized_games()

    # Assert
    assert (
        sample_games["favorites_and_hidden"] in uncategorized
    ), "CRITICAL BUG: Games with ONLY system categories should be uncategorized!"


@patch("src.core.game_manager.t")
def test_not_uncategorized_with_user_category(mock_t, game_manager, sample_games):
    """Test: Game with a user category is NOT uncategorized."""
    # Setup i18n mock
    mock_t.side_effect = lambda key: {"ui.categories.favorites": "Favorites", "ui.categories.hidden": "Hidden"}.get(
        key, key
    )

    # Execute
    uncategorized = game_manager.get_uncategorized_games()

    # Assert
    assert sample_games["action"] not in uncategorized


@patch("src.core.game_manager.t")
def test_not_uncategorized_favorites_plus_user_category(mock_t, game_manager, sample_games):
    """Test: Game with Favorites + user category is NOT uncategorized."""
    # Setup i18n mock
    mock_t.side_effect = lambda key: {"ui.categories.favorites": "Favorites", "ui.categories.hidden": "Hidden"}.get(
        key, key
    )

    # Execute
    uncategorized = game_manager.get_uncategorized_games()

    # Assert
    assert sample_games["favorites_and_action"] not in uncategorized


@patch("src.core.game_manager.t")
def test_not_uncategorized_hidden_plus_user_category(mock_t, game_manager, sample_games):
    """Test: Game with Hidden + user category is NOT uncategorized."""
    # Setup i18n mock
    mock_t.side_effect = lambda key: {"ui.categories.favorites": "Favorites", "ui.categories.hidden": "Hidden"}.get(
        key, key
    )

    # Execute
    uncategorized = game_manager.get_uncategorized_games()

    # Assert
    assert sample_games["hidden_and_rpg"] not in uncategorized


@patch("src.core.game_manager.t")
def test_not_uncategorized_all_categories(mock_t, game_manager, sample_games):
    """Test: Game with system categories + user category is NOT uncategorized."""
    # Setup i18n mock
    mock_t.side_effect = lambda key: {"ui.categories.favorites": "Favorites", "ui.categories.hidden": "Hidden"}.get(
        key, key
    )

    # Execute
    uncategorized = game_manager.get_uncategorized_games()

    # Assert
    assert sample_games["all_categories"] not in uncategorized


# ==================================================================
# COMPREHENSIVE SCENARIO TEST
# ==================================================================


@patch("src.core.game_manager.t")
def test_uncategorized_comprehensive_count(mock_t, game_manager, sample_games):
    """Test: Verify the EXACT count of uncategorized games.

    Expected: 4 games should be uncategorized:
    1. No categories
    2. Only Favorites
    3. Only Hidden
    4. Favorites + Hidden
    """
    # Setup i18n mock
    mock_t.side_effect = lambda key: {"ui.categories.favorites": "Favorites", "ui.categories.hidden": "Hidden"}.get(
        key, key
    )

    # Execute
    uncategorized = game_manager.get_uncategorized_games()

    # Assert
    assert (
        len(uncategorized) == 4
    ), f"Expected 4 uncategorized games, got {len(uncategorized)}: {[g.name for g in uncategorized]}"


# ==================================================================
# SORTING TEST
# ==================================================================


@patch("src.core.game_manager.t")
def test_uncategorized_sorted_by_sort_name(mock_t, game_manager, sample_games):
    """Test: Uncategorized games are sorted by sort_name (lowercase)."""
    # Setup i18n mock
    mock_t.side_effect = lambda key: {"ui.categories.favorites": "Favorites", "ui.categories.hidden": "Hidden"}.get(
        key, key
    )

    # Execute
    uncategorized = game_manager.get_uncategorized_games()

    # Assert: Check if sorted
    names = [g.sort_name.lower() for g in uncategorized]
    assert names == sorted(names), "Uncategorized games should be sorted alphabetically!"


# ==================================================================
# EDGE CASE: Empty Game Library
# ==================================================================


@patch("src.core.game_manager.t")
def test_uncategorized_empty_library(mock_t, game_manager):
    """Test: Empty game library returns empty uncategorized list."""
    # Setup i18n mock
    mock_t.side_effect = lambda key: {"ui.categories.favorites": "Favorites", "ui.categories.hidden": "Hidden"}.get(
        key, key
    )

    # Ensure library is empty
    game_manager.games = {}

    # Execute
    uncategorized = game_manager.get_uncategorized_games()

    # Assert
    assert uncategorized == []


# ==================================================================
# REGRESSION TEST: Old Logic Would Fail
# ==================================================================


@patch("src.core.game_manager.t")
def test_regression_old_logic_would_fail(mock_t, game_manager, sample_games):
    """Regression test: Verify the old logic would have FAILED this test.

    Old logic:
    ```python
    games = [g for g in self.get_real_games()
             if not g.categories or (len(g.categories) == 1 and favorites_key in g.categories)]
    ```

    This would MISS:
    - Games with ONLY "Hidden"
    - Games with "Favorites + Hidden"
    """
    # Setup i18n mock
    mock_t.side_effect = lambda key: {"ui.categories.favorites": "Favorites", "ui.categories.hidden": "Hidden"}.get(
        key, key
    )

    # Execute
    uncategorized = game_manager.get_uncategorized_games()

    # OLD LOGIC would have returned ONLY 2 games:
    # - No categories
    # - Only Favorites

    # NEW LOGIC returns 4 games:
    # - No categories
    # - Only Favorites
    # - Only Hidden (← FIX!)
    # - Favorites + Hidden (← FIX!)

    assert len(uncategorized) == 4, "Old logic would have returned 2, new logic returns 4!"

    assert sample_games["only_hidden"] in uncategorized, "Old logic MISSED games with only 'Hidden'!"

    assert sample_games["favorites_and_hidden"] in uncategorized, "Old logic MISSED games with 'Favorites + Hidden'!"
