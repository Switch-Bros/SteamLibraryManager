# tests/unit/test_services/test_smart_collection_templates.py

"""Tests for Smart Collection templates."""

from __future__ import annotations

import pytest

from src.core.game import Game
from src.services.smart_collections.evaluator import SmartCollectionEvaluator
from src.services.smart_collections.templates import (
    TEMPLATE_CATEGORIES,
    SmartCollectionTemplate,
    get_all_templates,
    get_template_by_key,
)

# ========================================================================
# FIXTURES
# ========================================================================


@pytest.fixture
def evaluator() -> SmartCollectionEvaluator:
    """Creates a fresh evaluator instance."""
    return SmartCollectionEvaluator()


@pytest.fixture
def game_highly_rated() -> Game:
    """A game with review score 95."""
    return Game(
        app_id="100",
        name="Great Game",
        review_percentage=95,
        review_count=1000,
        app_type="game",
    )


@pytest.fixture
def game_low_rated() -> Game:
    """A game with review score 40."""
    return Game(
        app_id="200",
        name="Bad Game",
        review_percentage=40,
        review_count=500,
        app_type="game",
    )


@pytest.fixture
def game_lego_linux() -> Game:
    """A LEGO game on linux with high review score."""
    return Game(
        app_id="300",
        name="LEGO Linux Game",
        tags=["LEGO", "Adventure"],
        genres=["Action", "Puzzle"],
        platforms=["linux", "windows"],
        review_percentage=88,
        review_count=2000,
        app_type="game",
    )


# ========================================================================
# TEMPLATE STRUCTURE TESTS
# ========================================================================


class TestTemplateStructure:
    """Tests for template definitions and structure."""

    def test_all_templates_have_valid_groups(self) -> None:
        """Every template's collection has at least one group with rules."""
        for tmpl in get_all_templates():
            assert tmpl.collection.groups, f"Template '{tmpl.key}' has no groups"
            for group in tmpl.collection.groups:
                assert group.rules, f"Template '{tmpl.key}' has an empty group"

    def test_all_templates_have_nonempty_key(self) -> None:
        """Every template has a non-empty key."""
        for tmpl in get_all_templates():
            assert tmpl.key.strip(), "Template has empty key"

    def test_all_templates_have_category(self) -> None:
        """Every template has a non-empty category."""
        for tmpl in get_all_templates():
            assert tmpl.category.strip(), f"Template '{tmpl.key}' has empty category"

    def test_template_keys_are_unique(self) -> None:
        """No two templates share the same key."""
        keys = [tmpl.key for tmpl in get_all_templates()]
        assert len(keys) == len(set(keys)), f"Duplicate keys found: {keys}"

    def test_expected_template_count(self) -> None:
        """We have exactly 12 templates."""
        assert len(get_all_templates()) == 12

    def test_expected_categories(self) -> None:
        """Templates are organized into 5 categories."""
        assert set(TEMPLATE_CATEGORIES.keys()) == {"quality", "completion", "time", "platform", "examples"}

    def test_get_template_by_key_found(self) -> None:
        """Lookup by key returns the correct template."""
        tmpl = get_template_by_key("highly_rated")
        assert tmpl is not None
        assert isinstance(tmpl, SmartCollectionTemplate)
        assert tmpl.category == "quality"

    def test_get_template_by_key_not_found(self) -> None:
        """Lookup with unknown key returns None."""
        assert get_template_by_key("nonexistent") is None

    def test_template_is_frozen(self) -> None:
        """SmartCollectionTemplate is immutable."""
        tmpl = get_template_by_key("highly_rated")
        assert tmpl is not None
        with pytest.raises(AttributeError):
            tmpl.key = "hacked"  # type: ignore[misc]


# ========================================================================
# TEMPLATE EVALUATOR TESTS
# ========================================================================


class TestTemplateEvaluation:
    """Tests that templates evaluate correctly against games."""

    def test_highly_rated_matches_high_score(
        self, evaluator: SmartCollectionEvaluator, game_highly_rated: Game
    ) -> None:
        """'highly_rated' template matches game with review 95."""
        tmpl = get_template_by_key("highly_rated")
        assert tmpl is not None
        assert evaluator.evaluate(game_highly_rated, tmpl.collection) is True

    def test_highly_rated_rejects_low_score(self, evaluator: SmartCollectionEvaluator, game_low_rated: Game) -> None:
        """'highly_rated' template rejects game with review 40."""
        tmpl = get_template_by_key("highly_rated")
        assert tmpl is not None
        assert evaluator.evaluate(game_low_rated, tmpl.collection) is False

    def test_mixed_negative_matches_low_score(self, evaluator: SmartCollectionEvaluator, game_low_rated: Game) -> None:
        """'mixed_negative' template matches game with review 40."""
        tmpl = get_template_by_key("mixed_negative")
        assert tmpl is not None
        assert evaluator.evaluate(game_low_rated, tmpl.collection) is True

    def test_mixed_negative_rejects_high_score(
        self, evaluator: SmartCollectionEvaluator, game_highly_rated: Game
    ) -> None:
        """'mixed_negative' template rejects game with review 95."""
        tmpl = get_template_by_key("mixed_negative")
        assert tmpl is not None
        assert evaluator.evaluate(game_highly_rated, tmpl.collection) is False

    def test_hybrid_demo_matches_lego_linux(self, evaluator: SmartCollectionEvaluator, game_lego_linux: Game) -> None:
        """'hybrid_demo' matches: Group1 (Tag=LEGO AND Platform=linux) -> True via OR."""
        tmpl = get_template_by_key("hybrid_demo")
        assert tmpl is not None
        assert evaluator.evaluate(game_lego_linux, tmpl.collection) is True

    def test_hybrid_demo_matches_action_high_review(self, evaluator: SmartCollectionEvaluator) -> None:
        """'hybrid_demo' matches: Group2 (Genre=Action AND Review>=80) -> True via OR."""
        game = Game(
            app_id="400",
            name="Action Hero",
            genres=["Action"],
            review_percentage=85,
            app_type="game",
        )
        tmpl = get_template_by_key("hybrid_demo")
        assert tmpl is not None
        assert evaluator.evaluate(game, tmpl.collection) is True

    def test_hybrid_demo_rejects_no_match(self, evaluator: SmartCollectionEvaluator) -> None:
        """'hybrid_demo' rejects game that matches neither group."""
        game = Game(
            app_id="500",
            name="Puzzle Game",
            genres=["Puzzle"],
            review_percentage=60,
            app_type="game",
        )
        tmpl = get_template_by_key("hybrid_demo")
        assert tmpl is not None
        assert evaluator.evaluate(game, tmpl.collection) is False
