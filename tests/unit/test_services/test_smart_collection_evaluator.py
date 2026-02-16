# tests/unit/test_services/test_smart_collection_evaluator.py

"""Tests for SmartCollectionEvaluator."""

from __future__ import annotations

import pytest

from src.core.game import Game
from src.services.smart_collections.evaluator import SmartCollectionEvaluator
from src.services.smart_collections.models import (
    FilterField,
    LogicOperator,
    Operator,
    SmartCollection,
    SmartCollectionRule,
    collection_from_json,
    collection_to_json,
    rule_from_dict,
    rule_to_dict,
)

# ========================================================================
# FIXTURES
# ========================================================================


@pytest.fixture
def evaluator() -> SmartCollectionEvaluator:
    """Creates a fresh evaluator instance."""
    return SmartCollectionEvaluator()


@pytest.fixture
def game_lego() -> Game:
    """A LEGO game with typical metadata."""
    return Game(
        app_id="100",
        name="LEGO Star Wars: The Complete Saga",
        tags=["LEGO", "Action", "Adventure", "Sci-Fi"],
        genres=["Action", "Adventure"],
        platforms=["windows", "linux"],
        developer="Traveller's Tales",
        publisher="Warner Bros.",
        release_year="2009",
        playtime_minutes=720,
        review_percentage=92,
        review_count=5000,
        installed=True,
        hidden=False,
        steam_deck_status="verified",
        proton_db_rating="platinum",
        hltb_main_story=12.5,
        categories=["Action Games", "LEGO Collection"],
        languages=["English", "German", "French"],
        achievement_total=50,
        achievement_unlocked=50,
        achievement_percentage=100.0,
        achievement_perfect=True,
        app_type="game",
    )


@pytest.fixture
def game_horror() -> Game:
    """A horror game with different metadata."""
    return Game(
        app_id="200",
        name="Resident Evil Village",
        tags=["Horror", "Action", "Shooter", "Survival"],
        genres=["Action", "Horror"],
        platforms=["windows"],
        developer="Capcom",
        publisher="Capcom",
        release_year="2021",
        playtime_minutes=1200,
        review_percentage=85,
        review_count=12000,
        installed=False,
        hidden=False,
        steam_deck_status="playable",
        proton_db_rating="gold",
        hltb_main_story=600.0,
        categories=["Horror"],
        languages=["English", "Japanese"],
        achievement_total=30,
        achievement_unlocked=15,
        achievement_percentage=50.0,
        achievement_perfect=False,
        app_type="game",
    )


@pytest.fixture
def game_empty() -> Game:
    """A minimal game with mostly empty/default fields."""
    return Game(
        app_id="300",
        name="Empty Game",
    )


# ========================================================================
# TESTS: MODELS & SERIALIZATION
# ========================================================================


class TestModels:
    """Tests for SmartCollection models and serialization."""

    def test_rule_to_dict_roundtrip(self) -> None:
        """Tests rule serialization and deserialization."""
        rule = SmartCollectionRule(
            field=FilterField.TAG,
            operator=Operator.CONTAINS,
            value="LEGO",
            negated=True,
        )
        data = rule_to_dict(rule)
        restored = rule_from_dict(data)
        assert restored.field == FilterField.TAG
        assert restored.operator == Operator.CONTAINS
        assert restored.value == "LEGO"
        assert restored.negated is True

    def test_rule_between_roundtrip(self) -> None:
        """Tests BETWEEN operator serialization."""
        rule = SmartCollectionRule(
            field=FilterField.RELEASE_YEAR,
            operator=Operator.BETWEEN,
            value="2020",
            value_max="2025",
        )
        data = rule_to_dict(rule)
        restored = rule_from_dict(data)
        assert restored.value == "2020"
        assert restored.value_max == "2025"

    def test_collection_to_json_roundtrip(self) -> None:
        """Tests full collection serialization and deserialization."""
        collection = SmartCollection(
            name="Test",
            logic=LogicOperator.OR,
            rules=[
                SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "LEGO"),
                SmartCollectionRule(FilterField.GENRE, Operator.EQUALS, "Action"),
            ],
        )
        json_str = collection_to_json(collection)
        restored = collection_from_json(json_str)
        assert restored.logic == LogicOperator.OR
        assert len(restored.rules) == 2
        assert restored.rules[0].field == FilterField.TAG
        assert restored.rules[1].field == FilterField.GENRE

    def test_collection_from_json_empty_string(self) -> None:
        """Tests deserialization with empty JSON string."""
        result = collection_from_json("")
        assert result.rules == []
        assert result.logic == LogicOperator.OR

    def test_collection_from_json_invalid_json(self) -> None:
        """Tests deserialization with invalid JSON string."""
        result = collection_from_json("{invalid json")
        assert result.rules == []

    def test_collection_from_json_skips_invalid_rules(self) -> None:
        """Tests that invalid rules are skipped during deserialization."""
        json_str = (
            '{"logic": "OR", "rules": [{"field": "invalid_field"},'
            ' {"field": "tag", "operator": "contains", "value": "test"}]}'
        )
        result = collection_from_json(json_str)
        assert len(result.rules) == 1
        assert result.rules[0].value == "test"

    def test_smart_collection_default_values(self) -> None:
        """Tests SmartCollection default values."""
        sc = SmartCollection()
        assert sc.collection_id == 0
        assert sc.name == ""
        assert sc.logic == LogicOperator.OR
        assert sc.rules == []
        assert sc.is_active is True
        assert sc.auto_sync is True

    def test_smart_collection_rule_frozen(self) -> None:
        """Tests that SmartCollectionRule is immutable."""
        rule = SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "test")
        with pytest.raises(AttributeError):
            rule.value = "other"  # type: ignore[misc]


# ========================================================================
# TESTS: EVALUATOR — TEXT LIST MATCHING
# ========================================================================


class TestTextListMatching:
    """Tests for text list field matching (tags, genres, platforms, etc.)."""

    def test_tag_contains_match(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests tag contains matching."""
        rule = SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "LEGO")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True

    def test_tag_contains_case_insensitive(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests that text matching is case-insensitive."""
        rule = SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "lego")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True

    def test_tag_contains_no_match(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests tag that doesn't match."""
        rule = SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "Horror")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is False

    def test_tag_equals_match(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests exact tag equality."""
        rule = SmartCollectionRule(FilterField.TAG, Operator.EQUALS, "Action")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True

    def test_tag_starts_with(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests tag starts_with operator."""
        rule = SmartCollectionRule(FilterField.TAG, Operator.STARTS_WITH, "Adv")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True

    def test_tag_ends_with(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests tag ends_with operator."""
        rule = SmartCollectionRule(FilterField.TAG, Operator.ENDS_WITH, "Fi")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True

    def test_genre_contains(self, evaluator: SmartCollectionEvaluator, game_horror: Game) -> None:
        """Tests genre list matching."""
        rule = SmartCollectionRule(FilterField.GENRE, Operator.CONTAINS, "Horror")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_horror, collection) is True

    def test_platform_equals(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests platform matching."""
        rule = SmartCollectionRule(FilterField.PLATFORM, Operator.EQUALS, "linux")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True

    def test_language_contains(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests language list matching."""
        rule = SmartCollectionRule(FilterField.LANGUAGE, Operator.CONTAINS, "German")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True

    def test_category_contains(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests category list matching."""
        rule = SmartCollectionRule(FilterField.CATEGORY, Operator.CONTAINS, "LEGO")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True

    def test_empty_list_returns_false(self, evaluator: SmartCollectionEvaluator, game_empty: Game) -> None:
        """Tests that empty list fields return False."""
        rule = SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "anything")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_empty, collection) is False

    def test_tag_regex_match(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests regex matching on list fields."""
        rule = SmartCollectionRule(FilterField.TAG, Operator.REGEX, "^Sci.*")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True

    def test_tag_regex_no_match(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests regex that doesn't match."""
        rule = SmartCollectionRule(FilterField.TAG, Operator.REGEX, "^Horror$")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is False


# ========================================================================
# TESTS: EVALUATOR — TEXT SINGLE MATCHING
# ========================================================================


class TestTextSingleMatching:
    """Tests for text single field matching (name, developer, publisher, etc.)."""

    def test_name_contains(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests name contains matching."""
        rule = SmartCollectionRule(FilterField.NAME, Operator.CONTAINS, "Star Wars")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True

    def test_name_starts_with(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests name starts_with matching."""
        rule = SmartCollectionRule(FilterField.NAME, Operator.STARTS_WITH, "LEGO")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True

    def test_name_ends_with(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests name ends_with matching."""
        rule = SmartCollectionRule(FilterField.NAME, Operator.ENDS_WITH, "Saga")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True

    def test_name_equals(self, evaluator: SmartCollectionEvaluator, game_horror: Game) -> None:
        """Tests exact name equality (case insensitive)."""
        rule = SmartCollectionRule(FilterField.NAME, Operator.EQUALS, "resident evil village")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_horror, collection) is True

    def test_developer_contains(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests developer matching."""
        rule = SmartCollectionRule(FilterField.DEVELOPER, Operator.CONTAINS, "Traveller")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True

    def test_publisher_equals(self, evaluator: SmartCollectionEvaluator, game_horror: Game) -> None:
        """Tests publisher matching."""
        rule = SmartCollectionRule(FilterField.PUBLISHER, Operator.EQUALS, "Capcom")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_horror, collection) is True

    def test_app_type_equals(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests app_type matching."""
        rule = SmartCollectionRule(FilterField.APP_TYPE, Operator.EQUALS, "game")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True

    def test_name_regex(self, evaluator: SmartCollectionEvaluator, game_horror: Game) -> None:
        """Tests regex matching on name field."""
        rule = SmartCollectionRule(FilterField.NAME, Operator.REGEX, r"Resident Evil \w+")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_horror, collection) is True

    def test_name_regex_invalid_pattern(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests that invalid regex pattern returns False."""
        rule = SmartCollectionRule(FilterField.NAME, Operator.REGEX, "[invalid")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is False

    def test_steam_deck_equals(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests Steam Deck status matching (enum field treated as text)."""
        rule = SmartCollectionRule(FilterField.STEAM_DECK, Operator.EQUALS, "verified")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True

    def test_protondb_contains(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests ProtonDB rating matching."""
        rule = SmartCollectionRule(FilterField.PROTONDB, Operator.CONTAINS, "plat")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True


# ========================================================================
# TESTS: EVALUATOR — NUMERIC MATCHING
# ========================================================================


class TestNumericMatching:
    """Tests for numeric field matching."""

    def test_playtime_greater_than(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests playtime_hours > 10."""
        rule = SmartCollectionRule(FilterField.PLAYTIME_HOURS, Operator.GREATER_THAN, "10")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True  # 720 min = 12.0 hours

    def test_playtime_less_than(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests playtime_hours < 5."""
        rule = SmartCollectionRule(FilterField.PLAYTIME_HOURS, Operator.LESS_THAN, "5")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is False  # 12.0 hours

    def test_release_year_between(self, evaluator: SmartCollectionEvaluator, game_horror: Game) -> None:
        """Tests release_year between 2020 and 2025."""
        rule = SmartCollectionRule(FilterField.RELEASE_YEAR, Operator.BETWEEN, "2020", "2025")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_horror, collection) is True  # 2021

    def test_release_year_between_outside(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests release_year outside the between range."""
        rule = SmartCollectionRule(FilterField.RELEASE_YEAR, Operator.BETWEEN, "2020", "2025")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is False  # 2009

    def test_review_score_greater_equal(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests review_score >= 90."""
        rule = SmartCollectionRule(FilterField.REVIEW_SCORE, Operator.GREATER_EQUAL, "90")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True  # 92

    def test_review_count_less_equal(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests review_count <= 5000."""
        rule = SmartCollectionRule(FilterField.REVIEW_COUNT, Operator.LESS_EQUAL, "5000")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True  # exactly 5000

    def test_hltb_main_greater_than(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests HLTB main story time > 10."""
        rule = SmartCollectionRule(FilterField.HLTB_MAIN, Operator.GREATER_THAN, "10")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True  # 12.5

    def test_achievement_pct_equals(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests achievement percentage equals 100."""
        rule = SmartCollectionRule(FilterField.ACHIEVEMENT_PCT, Operator.EQUALS, "100")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True

    def test_achievement_total_greater_than(self, evaluator: SmartCollectionEvaluator, game_horror: Game) -> None:
        """Tests achievement total > 20."""
        rule = SmartCollectionRule(FilterField.ACHIEVEMENT_TOTAL, Operator.GREATER_THAN, "20")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_horror, collection) is True  # 30

    def test_numeric_empty_value_returns_false(self, evaluator: SmartCollectionEvaluator, game_empty: Game) -> None:
        """Tests numeric matching with empty game fields."""
        rule = SmartCollectionRule(FilterField.PLAYTIME_HOURS, Operator.GREATER_THAN, "0")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_empty, collection) is False  # 0.0

    def test_numeric_invalid_target(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests that invalid target string returns False."""
        rule = SmartCollectionRule(FilterField.PLAYTIME_HOURS, Operator.GREATER_THAN, "not_a_number")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is False

    def test_release_year_equals(self, evaluator: SmartCollectionEvaluator, game_horror: Game) -> None:
        """Tests release year exact equality."""
        rule = SmartCollectionRule(FilterField.RELEASE_YEAR, Operator.EQUALS, "2021")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_horror, collection) is True


# ========================================================================
# TESTS: EVALUATOR — BOOLEAN MATCHING
# ========================================================================


class TestBooleanMatching:
    """Tests for boolean field matching."""

    def test_installed_is_true(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests installed is_true."""
        rule = SmartCollectionRule(FilterField.INSTALLED, Operator.IS_TRUE)
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True

    def test_installed_is_false(self, evaluator: SmartCollectionEvaluator, game_horror: Game) -> None:
        """Tests installed is_false."""
        rule = SmartCollectionRule(FilterField.INSTALLED, Operator.IS_FALSE)
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_horror, collection) is True

    def test_hidden_is_true(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests hidden is_true for non-hidden game."""
        rule = SmartCollectionRule(FilterField.HIDDEN, Operator.IS_TRUE)
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is False

    def test_achievement_perfect_is_true(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests achievement_perfect is_true for perfect game."""
        rule = SmartCollectionRule(FilterField.ACHIEVEMENT_PERFECT, Operator.IS_TRUE)
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True

    def test_achievement_perfect_is_false(self, evaluator: SmartCollectionEvaluator, game_horror: Game) -> None:
        """Tests achievement_perfect is_false for non-perfect game."""
        rule = SmartCollectionRule(FilterField.ACHIEVEMENT_PERFECT, Operator.IS_FALSE)
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_horror, collection) is True


# ========================================================================
# TESTS: EVALUATOR — LOGIC OPERATORS (AND/OR)
# ========================================================================


class TestLogicOperators:
    """Tests for AND/OR logic between rules."""

    def test_or_logic_any_matches(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests OR logic: at least one rule matches."""
        collection = SmartCollection(
            logic=LogicOperator.OR,
            rules=[
                SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "LEGO"),
                SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "Horror"),
            ],
        )
        assert evaluator.evaluate(game_lego, collection) is True

    def test_or_logic_none_matches(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests OR logic: no rules match."""
        collection = SmartCollection(
            logic=LogicOperator.OR,
            rules=[
                SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "Horror"),
                SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "RPG"),
            ],
        )
        assert evaluator.evaluate(game_lego, collection) is False

    def test_and_logic_all_match(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests AND logic: all rules must match."""
        collection = SmartCollection(
            logic=LogicOperator.AND,
            rules=[
                SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "LEGO"),
                SmartCollectionRule(FilterField.INSTALLED, Operator.IS_TRUE),
            ],
        )
        assert evaluator.evaluate(game_lego, collection) is True

    def test_and_logic_not_all_match(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests AND logic: one rule doesn't match."""
        collection = SmartCollection(
            logic=LogicOperator.AND,
            rules=[
                SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "LEGO"),
                SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "Horror"),
            ],
        )
        assert evaluator.evaluate(game_lego, collection) is False


# ========================================================================
# TESTS: EVALUATOR — NEGATION
# ========================================================================


class TestNegation:
    """Tests for rule negation (NOT)."""

    def test_negated_tag_match(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests NOT tag contains 'Horror' for a non-horror game."""
        rule = SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "Horror", negated=True)
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is True

    def test_negated_tag_no_match(self, evaluator: SmartCollectionEvaluator, game_horror: Game) -> None:
        """Tests NOT tag contains 'Horror' for a horror game."""
        rule = SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "Horror", negated=True)
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_horror, collection) is False

    def test_negated_installed(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests NOT installed is_true for installed game."""
        rule = SmartCollectionRule(FilterField.INSTALLED, Operator.IS_TRUE, negated=True)
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is False

    def test_negated_with_and_logic(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests negated rule combined with AND logic."""
        collection = SmartCollection(
            logic=LogicOperator.AND,
            rules=[
                SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "LEGO"),
                SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "Horror", negated=True),
            ],
        )
        # Has LEGO, does NOT have Horror -> both pass with AND
        assert evaluator.evaluate(game_lego, collection) is True


# ========================================================================
# TESTS: EVALUATOR — BATCH & EDGE CASES
# ========================================================================


class TestBatchAndEdgeCases:
    """Tests for evaluate_batch and edge cases."""

    def test_evaluate_batch_returns_matching(
        self,
        evaluator: SmartCollectionEvaluator,
        game_lego: Game,
        game_horror: Game,
        game_empty: Game,
    ) -> None:
        """Tests evaluate_batch returns only matching games."""
        collection = SmartCollection(rules=[SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "Action")])
        result = evaluator.evaluate_batch([game_lego, game_horror, game_empty], collection)
        assert len(result) == 2
        assert game_lego in result
        assert game_horror in result
        assert game_empty not in result

    def test_evaluate_batch_empty_games(self, evaluator: SmartCollectionEvaluator) -> None:
        """Tests evaluate_batch with empty game list."""
        collection = SmartCollection(rules=[SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "test")])
        result = evaluator.evaluate_batch([], collection)
        assert result == []

    def test_evaluate_empty_rules_returns_false(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests that empty rules returns False."""
        collection = SmartCollection(rules=[])
        assert evaluator.evaluate(game_lego, collection) is False

    def test_regex_invalid_in_list(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests that invalid regex in list field returns False."""
        rule = SmartCollectionRule(FilterField.TAG, Operator.REGEX, "(unclosed")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is False

    def test_empty_game_numeric_fields(self, evaluator: SmartCollectionEvaluator, game_empty: Game) -> None:
        """Tests numeric matching on empty game with default 0 values."""
        rule = SmartCollectionRule(FilterField.ACHIEVEMENT_TOTAL, Operator.EQUALS, "0")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_empty, collection) is True

    def test_empty_game_boolean_fields(self, evaluator: SmartCollectionEvaluator, game_empty: Game) -> None:
        """Tests boolean matching on empty game with default False values."""
        rule = SmartCollectionRule(FilterField.INSTALLED, Operator.IS_FALSE)
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_empty, collection) is True

    def test_mixed_rules_or_logic(
        self,
        evaluator: SmartCollectionEvaluator,
        game_lego: Game,
    ) -> None:
        """Tests OR logic with mixed field types."""
        collection = SmartCollection(
            logic=LogicOperator.OR,
            rules=[
                SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "LEGO"),
                SmartCollectionRule(FilterField.PLAYTIME_HOURS, Operator.GREATER_THAN, "100"),
                SmartCollectionRule(FilterField.INSTALLED, Operator.IS_FALSE),
            ],
        )
        # Tag contains LEGO -> first rule matches, OR logic -> True
        assert evaluator.evaluate(game_lego, collection) is True

    def test_mixed_rules_and_logic(
        self,
        evaluator: SmartCollectionEvaluator,
        game_lego: Game,
    ) -> None:
        """Tests AND logic with mixed field types."""
        collection = SmartCollection(
            logic=LogicOperator.AND,
            rules=[
                SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "LEGO"),
                SmartCollectionRule(FilterField.PLAYTIME_HOURS, Operator.GREATER_THAN, "10"),
                SmartCollectionRule(FilterField.INSTALLED, Operator.IS_TRUE),
            ],
        )
        assert evaluator.evaluate(game_lego, collection) is True

    def test_between_with_invalid_max(self, evaluator: SmartCollectionEvaluator, game_lego: Game) -> None:
        """Tests BETWEEN with invalid max value."""
        rule = SmartCollectionRule(FilterField.RELEASE_YEAR, Operator.BETWEEN, "2000", "not_a_number")
        collection = SmartCollection(rules=[rule])
        assert evaluator.evaluate(game_lego, collection) is False
