# tests/unit/test_services/test_smart_collection_groups.py

"""Tests for SmartCollectionRuleGroup: dataclass, serialization, and evaluator group logic."""

from __future__ import annotations

import json

import pytest

from src.core.game import Game
from src.services.smart_collections.evaluator import SmartCollectionEvaluator
from src.services.smart_collections.models import (
    FilterField,
    LogicOperator,
    Operator,
    SmartCollection,
    SmartCollectionRule,
    SmartCollectionRuleGroup,
    collection_from_json,
    collection_to_json,
    group_from_dict,
    group_to_dict,
)

# ========================================================================
# FIXTURES
# ========================================================================


@pytest.fixture
def evaluator() -> SmartCollectionEvaluator:
    """Creates a fresh evaluator instance."""
    return SmartCollectionEvaluator()


@pytest.fixture
def rule_tag_lego() -> SmartCollectionRule:
    """Rule: tag contains LEGO."""
    return SmartCollectionRule(
        field=FilterField.TAG,
        operator=Operator.CONTAINS,
        value="LEGO",
    )


@pytest.fixture
def rule_platform_linux() -> SmartCollectionRule:
    """Rule: platform equals linux."""
    return SmartCollectionRule(
        field=FilterField.PLATFORM,
        operator=Operator.EQUALS,
        value="linux",
    )


@pytest.fixture
def rule_genre_action() -> SmartCollectionRule:
    """Rule: genre contains Action."""
    return SmartCollectionRule(
        field=FilterField.GENRE,
        operator=Operator.CONTAINS,
        value="Action",
    )


@pytest.fixture
def rule_review_high() -> SmartCollectionRule:
    """Rule: review score >= 80."""
    return SmartCollectionRule(
        field=FilterField.REVIEW_SCORE,
        operator=Operator.GREATER_EQUAL,
        value="80",
    )


@pytest.fixture
def rule_genre_horror() -> SmartCollectionRule:
    """Rule: genre contains Horror."""
    return SmartCollectionRule(
        field=FilterField.GENRE,
        operator=Operator.CONTAINS,
        value="Horror",
    )


@pytest.fixture
def rule_installed() -> SmartCollectionRule:
    """Rule: installed is true."""
    return SmartCollectionRule(
        field=FilterField.INSTALLED,
        operator=Operator.IS_TRUE,
    )


@pytest.fixture
def game_lego() -> Game:
    """A LEGO game: tag=LEGO, platform=linux, genre=Action, review=92, installed."""
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
    """A horror game: no LEGO, windows-only, genre=Horror+Action, review=85, not installed."""
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
    """A minimal game with defaults."""
    return Game(
        app_id="300",
        name="Empty Game",
    )


# ========================================================================
# GROUP DATACLASS TESTS
# ========================================================================


class TestSmartCollectionRuleGroup:
    """Tests for SmartCollectionRuleGroup dataclass."""

    def test_default_values(self) -> None:
        """Group defaults to AND logic with empty rules tuple."""
        group = SmartCollectionRuleGroup()
        assert group.logic == LogicOperator.AND
        assert group.rules == ()

    def test_frozen(self) -> None:
        """Group is immutable."""
        group = SmartCollectionRuleGroup()
        with pytest.raises(AttributeError):
            group.logic = LogicOperator.OR  # type: ignore[misc]

    def test_with_rules(self, rule_tag_lego: SmartCollectionRule, rule_platform_linux: SmartCollectionRule) -> None:
        """Group stores rules as a tuple."""
        group = SmartCollectionRuleGroup(
            logic=LogicOperator.OR,
            rules=(rule_tag_lego, rule_platform_linux),
        )
        assert group.logic == LogicOperator.OR
        assert len(group.rules) == 2
        assert group.rules[0].field == FilterField.TAG
        assert group.rules[1].field == FilterField.PLATFORM

    def test_equality(self, rule_tag_lego: SmartCollectionRule) -> None:
        """Two groups with same data are equal."""
        g1 = SmartCollectionRuleGroup(logic=LogicOperator.AND, rules=(rule_tag_lego,))
        g2 = SmartCollectionRuleGroup(logic=LogicOperator.AND, rules=(rule_tag_lego,))
        assert g1 == g2


# ========================================================================
# GROUP SERIALIZATION TESTS
# ========================================================================


class TestGroupSerialization:
    """Tests for group_to_dict and group_from_dict."""

    def test_group_to_dict_basic(self, rule_tag_lego: SmartCollectionRule) -> None:
        """Serializes a group with one rule."""
        group = SmartCollectionRuleGroup(
            logic=LogicOperator.AND,
            rules=(rule_tag_lego,),
        )
        result = group_to_dict(group)
        assert result["logic"] == "AND"
        assert len(result["rules"]) == 1
        assert result["rules"][0]["field"] == "tag"
        assert result["rules"][0]["operator"] == "contains"
        assert result["rules"][0]["value"] == "LEGO"

    def test_group_from_dict_basic(self) -> None:
        """Deserializes a group from a dict."""
        data = {
            "logic": "OR",
            "rules": [
                {"field": "tag", "operator": "contains", "value": "LEGO", "value_max": "", "negated": False},
            ],
        }
        group = group_from_dict(data)
        assert group.logic == LogicOperator.OR
        assert len(group.rules) == 1
        assert group.rules[0].field == FilterField.TAG

    def test_group_roundtrip(
        self, rule_tag_lego: SmartCollectionRule, rule_platform_linux: SmartCollectionRule
    ) -> None:
        """Roundtrip: group -> dict -> group preserves data."""
        original = SmartCollectionRuleGroup(
            logic=LogicOperator.AND,
            rules=(rule_tag_lego, rule_platform_linux),
        )
        data = group_to_dict(original)
        restored = group_from_dict(data)
        assert restored.logic == original.logic
        assert len(restored.rules) == len(original.rules)
        assert restored.rules[0].field == original.rules[0].field
        assert restored.rules[1].field == original.rules[1].field

    def test_group_from_dict_empty_rules(self) -> None:
        """Deserializes a group with no rules."""
        data = {"logic": "AND", "rules": []}
        group = group_from_dict(data)
        assert group.logic == LogicOperator.AND
        assert group.rules == ()

    def test_group_from_dict_missing_logic_defaults_to_and(self) -> None:
        """Missing logic key defaults to AND."""
        data = {"rules": []}
        group = group_from_dict(data)
        assert group.logic == LogicOperator.AND

    def test_group_from_dict_invalid_logic_defaults_to_and(self) -> None:
        """Invalid logic value defaults to AND."""
        data = {"logic": "XOR", "rules": []}
        group = group_from_dict(data)
        assert group.logic == LogicOperator.AND

    def test_group_from_dict_skips_invalid_rules(self) -> None:
        """Invalid rules within a group are skipped."""
        data = {
            "logic": "AND",
            "rules": [
                {"field": "tag", "operator": "contains", "value": "LEGO"},
                {"field": "INVALID_FIELD", "operator": "contains", "value": "bad"},
            ],
        }
        group = group_from_dict(data)
        assert len(group.rules) == 1
        assert group.rules[0].field == FilterField.TAG


# ========================================================================
# COLLECTION WITH GROUPS SERIALIZATION TESTS
# ========================================================================


class TestCollectionGroupSerialization:
    """Tests for collection_to_json and collection_from_json with groups."""

    def test_collection_to_json_with_groups(
        self, rule_tag_lego: SmartCollectionRule, rule_genre_action: SmartCollectionRule
    ) -> None:
        """Collection with groups produces 'groups' key, not 'rules'."""
        collection = SmartCollection(
            name="Test",
            logic=LogicOperator.OR,
            groups=[
                SmartCollectionRuleGroup(logic=LogicOperator.AND, rules=(rule_tag_lego,)),
                SmartCollectionRuleGroup(logic=LogicOperator.AND, rules=(rule_genre_action,)),
            ],
        )
        json_str = collection_to_json(collection)
        data = json.loads(json_str)
        assert "groups" in data
        assert "rules" not in data
        assert data["logic"] == "OR"
        assert len(data["groups"]) == 2

    def test_collection_to_json_without_groups_produces_rules(self, rule_tag_lego: SmartCollectionRule) -> None:
        """Collection without groups falls back to 'rules' key."""
        collection = SmartCollection(
            name="Test",
            logic=LogicOperator.OR,
            rules=[rule_tag_lego],
        )
        json_str = collection_to_json(collection)
        data = json.loads(json_str)
        assert "rules" in data
        assert "groups" not in data

    def test_collection_from_json_with_groups(self) -> None:
        """Deserializes a collection with groups from v2 JSON."""
        payload = {
            "logic": "OR",
            "groups": [
                {
                    "logic": "AND",
                    "rules": [
                        {"field": "tag", "operator": "contains", "value": "LEGO"},
                        {"field": "platform", "operator": "equals", "value": "linux"},
                    ],
                },
                {
                    "logic": "AND",
                    "rules": [
                        {"field": "genre", "operator": "contains", "value": "Action"},
                    ],
                },
            ],
        }
        json_str = json.dumps(payload)
        collection = collection_from_json(json_str)
        assert collection.logic == LogicOperator.OR
        assert len(collection.groups) == 2
        assert len(collection.groups[0].rules) == 2
        assert len(collection.groups[1].rules) == 1
        assert collection.rules == []

    def test_collection_from_json_legacy_rules_still_works(self) -> None:
        """v1 format with 'rules' key still deserializes correctly."""
        payload = {
            "logic": "AND",
            "rules": [
                {"field": "tag", "operator": "contains", "value": "LEGO"},
            ],
        }
        json_str = json.dumps(payload)
        collection = collection_from_json(json_str)
        assert collection.logic == LogicOperator.AND
        assert len(collection.rules) == 1
        assert collection.groups == []

    def test_collection_groups_roundtrip(
        self,
        rule_tag_lego: SmartCollectionRule,
        rule_platform_linux: SmartCollectionRule,
        rule_genre_action: SmartCollectionRule,
        rule_review_high: SmartCollectionRule,
    ) -> None:
        """Roundtrip: collection with groups -> JSON -> collection preserves structure."""
        original = SmartCollection(
            name="Hybrid Test",
            logic=LogicOperator.OR,
            groups=[
                SmartCollectionRuleGroup(
                    logic=LogicOperator.AND,
                    rules=(rule_tag_lego, rule_platform_linux),
                ),
                SmartCollectionRuleGroup(
                    logic=LogicOperator.AND,
                    rules=(rule_genre_action, rule_review_high),
                ),
            ],
        )
        json_str = collection_to_json(original)
        restored = collection_from_json(json_str)

        assert restored.logic == original.logic
        assert len(restored.groups) == 2
        assert len(restored.groups[0].rules) == 2
        assert len(restored.groups[1].rules) == 2
        assert restored.groups[0].logic == LogicOperator.AND
        assert restored.groups[1].logic == LogicOperator.AND
        assert restored.groups[0].rules[0].field == FilterField.TAG
        assert restored.groups[0].rules[1].field == FilterField.PLATFORM
        assert restored.groups[1].rules[0].field == FilterField.GENRE
        assert restored.groups[1].rules[1].field == FilterField.REVIEW_SCORE


# ========================================================================
# EVALUATOR GROUP TESTS
# ========================================================================


class TestEvaluatorGroups:
    """Tests for SmartCollectionEvaluator with groups."""

    def test_two_groups_or_one_matches(
        self,
        evaluator: SmartCollectionEvaluator,
        game_lego: Game,
        rule_tag_lego: SmartCollectionRule,
        rule_platform_linux: SmartCollectionRule,
        rule_genre_horror: SmartCollectionRule,
    ) -> None:
        """OR between groups: game_lego matches group1 (LEGO AND linux) but not group2 (Horror)."""
        collection = SmartCollection(
            name="OR Test",
            logic=LogicOperator.OR,
            groups=[
                SmartCollectionRuleGroup(logic=LogicOperator.AND, rules=(rule_tag_lego, rule_platform_linux)),
                SmartCollectionRuleGroup(logic=LogicOperator.AND, rules=(rule_genre_horror,)),
            ],
        )
        assert evaluator.evaluate(game_lego, collection) is True

    def test_two_groups_or_none_matches(
        self,
        evaluator: SmartCollectionEvaluator,
        game_empty: Game,
        rule_tag_lego: SmartCollectionRule,
        rule_genre_horror: SmartCollectionRule,
    ) -> None:
        """OR between groups: game_empty matches neither group."""
        collection = SmartCollection(
            name="OR No Match",
            logic=LogicOperator.OR,
            groups=[
                SmartCollectionRuleGroup(logic=LogicOperator.AND, rules=(rule_tag_lego,)),
                SmartCollectionRuleGroup(logic=LogicOperator.AND, rules=(rule_genre_horror,)),
            ],
        )
        assert evaluator.evaluate(game_empty, collection) is False

    def test_two_groups_and_both_match(
        self,
        evaluator: SmartCollectionEvaluator,
        game_lego: Game,
        rule_tag_lego: SmartCollectionRule,
        rule_genre_action: SmartCollectionRule,
    ) -> None:
        """AND between groups: game_lego matches both groups."""
        collection = SmartCollection(
            name="AND Both Match",
            logic=LogicOperator.AND,
            groups=[
                SmartCollectionRuleGroup(logic=LogicOperator.AND, rules=(rule_tag_lego,)),
                SmartCollectionRuleGroup(logic=LogicOperator.AND, rules=(rule_genre_action,)),
            ],
        )
        assert evaluator.evaluate(game_lego, collection) is True

    def test_two_groups_and_one_fails(
        self,
        evaluator: SmartCollectionEvaluator,
        game_lego: Game,
        rule_tag_lego: SmartCollectionRule,
        rule_genre_horror: SmartCollectionRule,
    ) -> None:
        """AND between groups: game_lego matches group1 but not group2 -> False."""
        collection = SmartCollection(
            name="AND One Fails",
            logic=LogicOperator.AND,
            groups=[
                SmartCollectionRuleGroup(logic=LogicOperator.AND, rules=(rule_tag_lego,)),
                SmartCollectionRuleGroup(logic=LogicOperator.AND, rules=(rule_genre_horror,)),
            ],
        )
        assert evaluator.evaluate(game_lego, collection) is False

    def test_group_internal_or(
        self,
        evaluator: SmartCollectionEvaluator,
        game_horror: Game,
        rule_tag_lego: SmartCollectionRule,
        rule_genre_horror: SmartCollectionRule,
    ) -> None:
        """Group with internal OR: game_horror matches Horror but not LEGO -> True."""
        collection = SmartCollection(
            name="Internal OR",
            logic=LogicOperator.AND,
            groups=[
                SmartCollectionRuleGroup(logic=LogicOperator.OR, rules=(rule_tag_lego, rule_genre_horror)),
            ],
        )
        assert evaluator.evaluate(game_horror, collection) is True

    def test_group_internal_and_fails(
        self,
        evaluator: SmartCollectionEvaluator,
        game_horror: Game,
        rule_tag_lego: SmartCollectionRule,
        rule_genre_horror: SmartCollectionRule,
    ) -> None:
        """Group with internal AND: game_horror matches Horror but not LEGO -> False."""
        collection = SmartCollection(
            name="Internal AND Fail",
            logic=LogicOperator.AND,
            groups=[
                SmartCollectionRuleGroup(logic=LogicOperator.AND, rules=(rule_tag_lego, rule_genre_horror)),
            ],
        )
        assert evaluator.evaluate(game_horror, collection) is False

    def test_empty_group_returns_false(
        self,
        evaluator: SmartCollectionEvaluator,
        game_lego: Game,
    ) -> None:
        """A group with no rules evaluates to False."""
        collection = SmartCollection(
            name="Empty Group",
            logic=LogicOperator.OR,
            groups=[
                SmartCollectionRuleGroup(logic=LogicOperator.AND, rules=()),
            ],
        )
        assert evaluator.evaluate(game_lego, collection) is False

    def test_batch_with_groups(
        self,
        evaluator: SmartCollectionEvaluator,
        game_lego: Game,
        game_horror: Game,
        game_empty: Game,
        rule_tag_lego: SmartCollectionRule,
        rule_platform_linux: SmartCollectionRule,
        rule_genre_horror: SmartCollectionRule,
    ) -> None:
        """Batch evaluation with groups: (LEGO AND linux) OR (Horror)."""
        collection = SmartCollection(
            name="Batch Test",
            logic=LogicOperator.OR,
            groups=[
                SmartCollectionRuleGroup(logic=LogicOperator.AND, rules=(rule_tag_lego, rule_platform_linux)),
                SmartCollectionRuleGroup(logic=LogicOperator.AND, rules=(rule_genre_horror,)),
            ],
        )
        matching = evaluator.evaluate_batch([game_lego, game_horror, game_empty], collection)
        assert len(matching) == 2
        assert game_lego in matching
        assert game_horror in matching
        assert game_empty not in matching

    def test_legacy_flat_rules_still_work(
        self,
        evaluator: SmartCollectionEvaluator,
        game_lego: Game,
        rule_tag_lego: SmartCollectionRule,
    ) -> None:
        """Legacy flat rules (no groups) still evaluate correctly."""
        collection = SmartCollection(
            name="Legacy",
            logic=LogicOperator.OR,
            rules=[rule_tag_lego],
            groups=[],
        )
        assert evaluator.evaluate(game_lego, collection) is True

    def test_groups_take_priority_over_rules(
        self,
        evaluator: SmartCollectionEvaluator,
        game_lego: Game,
        rule_tag_lego: SmartCollectionRule,
        rule_genre_horror: SmartCollectionRule,
    ) -> None:
        """When both groups and rules are present, groups take priority."""
        collection = SmartCollection(
            name="Priority",
            logic=LogicOperator.OR,
            rules=[rule_tag_lego],  # Would match
            groups=[
                SmartCollectionRuleGroup(logic=LogicOperator.AND, rules=(rule_genre_horror,)),  # Won't match
            ],
        )
        # Groups take priority, and Horror doesn't match game_lego
        assert evaluator.evaluate(game_lego, collection) is False

    def test_hybrid_demo_scenario(
        self,
        evaluator: SmartCollectionEvaluator,
        game_lego: Game,
        game_horror: Game,
    ) -> None:
        """Complex hybrid: (Tag=LEGO AND Platform=linux) OR (Genre=Horror AND Review>=80)."""
        collection = SmartCollection(
            name="Hybrid Demo",
            logic=LogicOperator.OR,
            groups=[
                SmartCollectionRuleGroup(
                    logic=LogicOperator.AND,
                    rules=(
                        SmartCollectionRule(field=FilterField.TAG, operator=Operator.CONTAINS, value="LEGO"),
                        SmartCollectionRule(field=FilterField.PLATFORM, operator=Operator.EQUALS, value="linux"),
                    ),
                ),
                SmartCollectionRuleGroup(
                    logic=LogicOperator.AND,
                    rules=(
                        SmartCollectionRule(field=FilterField.GENRE, operator=Operator.CONTAINS, value="Horror"),
                        SmartCollectionRule(
                            field=FilterField.REVIEW_SCORE, operator=Operator.GREATER_EQUAL, value="80"
                        ),
                    ),
                ),
            ],
        )
        # game_lego: LEGO + linux -> group1 matches -> True
        assert evaluator.evaluate(game_lego, collection) is True
        # game_horror: Horror + review=85 -> group2 matches -> True
        assert evaluator.evaluate(game_horror, collection) is True
