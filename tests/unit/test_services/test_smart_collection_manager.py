# tests/unit/test_services/test_smart_collection_manager.py

"""Tests for SmartCollectionManager service."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from src.core.game import Game
from src.services.smart_collections.models import (
    FilterField,
    LogicOperator,
    Operator,
    SmartCollection,
    SmartCollectionRule,
)
from src.services.smart_collections.smart_collection_manager import SmartCollectionManager

# ========================================================================
# FIXTURES
# ========================================================================


@pytest.fixture
def mock_db() -> Mock:
    """Creates a mock Database with smart collection methods."""
    db = Mock()
    db.create_smart_collection.return_value = 1
    db.get_all_smart_collections.return_value = []
    db.get_smart_collection.return_value = None
    db.get_smart_collection_by_name.return_value = None
    db.populate_smart_collection.return_value = 0
    db.commit.return_value = None
    return db


@pytest.fixture
def mock_game_manager() -> Mock:
    """Creates a mock GameManager with test games."""
    gm = Mock()
    games = [
        Game(
            app_id="100",
            name="LEGO Star Wars",
            tags=["LEGO", "Action"],
            genres=["Action"],
            installed=True,
            app_type="game",
        ),
        Game(
            app_id="200",
            name="Resident Evil",
            tags=["Horror", "Action"],
            genres=["Horror"],
            installed=False,
            app_type="game",
        ),
        Game(
            app_id="300",
            name="The Sims 4",
            tags=["Simulation"],
            genres=["Simulation"],
            installed=True,
            app_type="game",
        ),
    ]
    gm.get_real_games.return_value = games
    gm.get_games_by_category.return_value = []
    return gm


@pytest.fixture
def mock_category_service() -> Mock:
    """Creates a mock CategoryService."""
    cs = Mock()
    cs.add_app_to_category.return_value = True
    cs.remove_app_from_category.return_value = True
    return cs


@pytest.fixture
def manager(mock_db: Mock, mock_game_manager: Mock, mock_category_service: Mock) -> SmartCollectionManager:
    """Creates a SmartCollectionManager with mock dependencies."""
    return SmartCollectionManager(
        database=mock_db,
        game_manager=mock_game_manager,
        category_service=mock_category_service,
    )


# ========================================================================
# TESTS: CREATE
# ========================================================================


class TestCreate:
    """Tests for creating smart collections."""

    def test_create_evaluates_and_syncs(self, manager: SmartCollectionManager, mock_db: Mock) -> None:
        """Tests that create evaluates rules, populates DB, and syncs."""
        collection = SmartCollection(
            name="Action Games",
            logic=LogicOperator.OR,
            rules=[SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "Action")],
        )
        cid = manager.create(collection)

        assert cid == 1
        mock_db.create_smart_collection.assert_called_once()
        mock_db.populate_smart_collection.assert_called_once()
        mock_db.commit.assert_called()

    def test_create_returns_correct_id(self, manager: SmartCollectionManager, mock_db: Mock) -> None:
        """Tests that create returns the database-generated ID."""
        mock_db.create_smart_collection.return_value = 42
        collection = SmartCollection(
            name="Test",
            rules=[SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "x")],
        )
        assert manager.create(collection) == 42

    def test_create_syncs_matching_games(self, manager: SmartCollectionManager, mock_category_service: Mock) -> None:
        """Tests that create syncs matching games to Steam."""
        collection = SmartCollection(
            name="Action",
            auto_sync=True,
            rules=[SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "Action")],
        )
        manager.create(collection)

        # Should sync games that match (100 and 200 have "Action" tag)
        assert mock_category_service.add_app_to_category.call_count >= 1

    def test_create_no_sync_when_disabled(self, manager: SmartCollectionManager, mock_category_service: Mock) -> None:
        """Tests that create skips sync when auto_sync is False."""
        collection = SmartCollection(
            name="NoSync",
            auto_sync=False,
            rules=[SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "Action")],
        )
        manager.create(collection)
        mock_category_service.add_app_to_category.assert_not_called()


# ========================================================================
# TESTS: UPDATE
# ========================================================================


class TestUpdate:
    """Tests for updating smart collections."""

    def test_update_re_evaluates(self, manager: SmartCollectionManager, mock_db: Mock) -> None:
        """Tests that update re-evaluates rules and re-populates."""
        collection = SmartCollection(
            collection_id=1,
            name="Updated",
            rules=[SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "LEGO")],
        )
        count = manager.update(collection)

        mock_db.update_smart_collection.assert_called_once()
        mock_db.populate_smart_collection.assert_called_once()
        # Only "LEGO Star Wars" matches
        assert count == 1

    def test_update_rename_cleans_old_steam_category(
        self,
        manager: SmartCollectionManager,
        mock_db: Mock,
        mock_category_service: Mock,
    ) -> None:
        """Tests that renaming a collection removes the old Steam category."""
        mock_db.get_smart_collection.return_value = {"name": "Old Name", "collection_id": 1}
        collection = SmartCollection(
            collection_id=1,
            name="New Name",
            auto_sync=True,
            rules=[SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "Action")],
        )
        manager.update(collection)

        # Should have called _remove_from_steam for old name
        mock_db.get_smart_collection.assert_called_with(1)

    def test_update_same_name_no_cleanup(
        self,
        manager: SmartCollectionManager,
        mock_db: Mock,
        mock_game_manager: Mock,
    ) -> None:
        """Tests that updating without renaming does NOT clean up Steam category."""
        mock_db.get_smart_collection.return_value = {"name": "Same Name", "collection_id": 1}
        # Track calls to get_games_by_category (used by _remove_from_steam)
        initial_call_count = mock_game_manager.get_games_by_category.call_count

        collection = SmartCollection(
            collection_id=1,
            name="Same Name",
            auto_sync=False,
            rules=[SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "RPG")],
        )
        manager.update(collection)

        # _remove_from_steam should NOT have been called for "Same Name"
        # get_games_by_category is only called by sync_to_steam and _remove_from_steam
        # Since auto_sync=False, any call would be from _remove_from_steam
        assert mock_game_manager.get_games_by_category.call_count == initial_call_count


# ========================================================================
# TESTS: DELETE
# ========================================================================


class TestDelete:
    """Tests for deleting smart collections."""

    def test_delete_removes_from_db(self, manager: SmartCollectionManager, mock_db: Mock) -> None:
        """Tests that delete removes the collection from DB."""
        mock_db.get_smart_collection.return_value = {"name": "ToDelete", "collection_id": 1}
        manager.delete(1)

        mock_db.delete_smart_collection.assert_called_once_with(1)
        mock_db.commit.assert_called()

    def test_delete_removes_from_steam(
        self,
        manager: SmartCollectionManager,
        mock_db: Mock,
        mock_category_service: Mock,
        mock_game_manager: Mock,
    ) -> None:
        """Tests that delete cleans up the Steam category."""
        mock_db.get_smart_collection.return_value = {"name": "CleanMe", "collection_id": 1}
        # Simulate some games being in the category
        mock_game_manager.get_games_by_category.return_value = [
            Game(app_id="100", name="G1"),
            Game(app_id="200", name="G2"),
        ]
        manager.delete(1)

        assert mock_category_service.remove_app_from_category.call_count == 2


# ========================================================================
# TESTS: GET
# ========================================================================


class TestGet:
    """Tests for retrieving smart collections."""

    def test_get_all_empty(self, manager: SmartCollectionManager) -> None:
        """Tests get_all with no collections."""
        assert manager.get_all() == []

    def test_get_all_returns_collections(self, manager: SmartCollectionManager, mock_db: Mock) -> None:
        """Tests get_all returns deserialized collections."""
        mock_db.get_all_smart_collections.return_value = [
            {
                "collection_id": 1,
                "name": "Alpha",
                "description": "desc",
                "icon": "\U0001f9e0",
                "rules": '{"logic": "OR", "rules": [{"field": "tag", "operator": "contains", "value": "test"}]}',
                "created_at": 1000,
            },
        ]
        result = manager.get_all()
        assert len(result) == 1
        assert result[0].name == "Alpha"
        assert len(result[0].rules) == 1
        assert result[0].logic == LogicOperator.OR

    def test_get_by_name_found(self, manager: SmartCollectionManager, mock_db: Mock) -> None:
        """Tests get_by_name returns the collection."""
        mock_db.get_smart_collection_by_name.return_value = {
            "collection_id": 5,
            "name": "FindMe",
            "description": "",
            "icon": "",
            "rules": '{"logic": "AND", "rules": []}',
            "created_at": 0,
        }
        result = manager.get_by_name("FindMe")
        assert result is not None
        assert result.collection_id == 5
        assert result.logic == LogicOperator.AND

    def test_get_by_name_not_found(self, manager: SmartCollectionManager) -> None:
        """Tests get_by_name returns None for unknown name."""
        assert manager.get_by_name("DoesNotExist") is None


# ========================================================================
# TESTS: EVALUATE
# ========================================================================


class TestEvaluate:
    """Tests for rule evaluation."""

    def test_evaluate_collection_returns_matching(self, manager: SmartCollectionManager) -> None:
        """Tests evaluate_collection returns correct games."""
        collection = SmartCollection(
            rules=[SmartCollectionRule(FilterField.TAG, Operator.CONTAINS, "Horror")],
        )
        result = manager.evaluate_collection(collection)
        assert len(result) == 1
        assert result[0].app_id == "200"

    def test_evaluate_all_returns_dict(self, manager: SmartCollectionManager, mock_db: Mock) -> None:
        """Tests evaluate_all returns dict of all collections."""
        mock_db.get_all_smart_collections.return_value = [
            {
                "collection_id": 1,
                "name": "Action",
                "rules": '{"logic": "OR", "rules": [{"field": "tag", "operator": "contains", "value": "Action"}]}',
                "created_at": 0,
            },
            {
                "collection_id": 2,
                "name": "Sim",
                "rules": '{"logic": "OR", "rules": [{"field": "tag", "operator": "contains", "value": "Simulation"}]}',
                "created_at": 0,
            },
        ]
        result = manager.evaluate_all()
        assert "Action" in result
        assert "Sim" in result
        assert len(result["Action"]) == 2  # LEGO + RE
        assert len(result["Sim"]) == 1  # Sims


# ========================================================================
# TESTS: SYNC
# ========================================================================


class TestSync:
    """Tests for Steam sync."""

    def test_sync_adds_new_games(
        self, manager: SmartCollectionManager, mock_category_service: Mock, mock_game_manager: Mock
    ) -> None:
        """Tests that sync adds games not yet in the Steam category."""
        mock_game_manager.get_games_by_category.return_value = []  # no games yet
        collection = SmartCollection(name="SyncTest")
        manager.sync_to_steam(collection, ["100", "200"])

        assert mock_category_service.add_app_to_category.call_count == 2

    def test_sync_removes_stale_games(
        self, manager: SmartCollectionManager, mock_category_service: Mock, mock_game_manager: Mock
    ) -> None:
        """Tests that sync removes games that no longer match."""
        # Games 100 and 200 are currently in the category
        mock_game_manager.get_games_by_category.return_value = [
            Game(app_id="100", name="G1"),
            Game(app_id="200", name="G2"),
        ]
        collection = SmartCollection(name="SyncTest")
        # Only 100 matches now
        manager.sync_to_steam(collection, ["100"])

        mock_category_service.remove_app_from_category.assert_called_once_with("200", "SyncTest")

    def test_sync_no_category_service(self, mock_db: Mock, mock_game_manager: Mock) -> None:
        """Tests that sync does nothing without category service."""
        mgr = SmartCollectionManager(mock_db, mock_game_manager, category_service=None)
        collection = SmartCollection(name="NoService")
        # Should not raise
        mgr.sync_to_steam(collection, ["100"])


# ========================================================================
# TESTS: REFRESH
# ========================================================================


class TestRefresh:
    """Tests for auto-update refresh."""

    def test_refresh_updates_all(self, manager: SmartCollectionManager, mock_db: Mock) -> None:
        """Tests refresh evaluates and syncs all collections."""
        mock_db.get_all_smart_collections.return_value = [
            {
                "collection_id": 1,
                "name": "Action",
                "rules": '{"logic": "OR", "rules": [{"field": "tag", "operator": "contains", "value": "Action"}]}',
                "created_at": 0,
            },
        ]
        result = manager.refresh()

        assert "Action" in result
        assert result["Action"] == 2  # LEGO + RE match
        mock_db.populate_smart_collection.assert_called()
        mock_db.commit.assert_called()

    def test_refresh_empty_collections(self, manager: SmartCollectionManager) -> None:
        """Tests refresh with no collections returns empty dict."""
        result = manager.refresh()
        assert result == {}
