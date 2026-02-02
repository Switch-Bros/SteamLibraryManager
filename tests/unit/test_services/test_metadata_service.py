"""
Unit tests for MetadataService.

Tests cover:
- Single game metadata operations
- Bulk metadata operations with name modifications
- Finding games with missing metadata
- Restoring metadata modifications
"""
import pytest
from unittest.mock import Mock

from src.services.metadata_service import MetadataService
from src.core.game_manager import Game, GameManager
from src.core.appinfo_manager import AppInfoManager


@pytest.fixture
def mock_appinfo_manager():
    """Create a mock AppInfoManager."""
    manager = Mock(spec=AppInfoManager)
    manager.modifications = {}
    manager.get_modification_count = Mock(return_value=0)
    manager.get_app_metadata = Mock(return_value={})
    manager.set_app_metadata = Mock()
    manager.save_appinfo = Mock()
    manager.restore_modifications = Mock(return_value=0)
    return manager


@pytest.fixture
def mock_game_manager():
    """Create a mock GameManager with sample games."""
    manager = Mock(spec=GameManager)

    # Create sample games
    game1 = Game(
        app_id="1",
        name="Test Game 1",
        developer="Dev 1",
        publisher="Pub 1",
        release_year="2020"
    )
    game2 = Game(
        app_id="2",
        name="Test Game 2",
        developer="Dev 2",
        publisher="Pub 2",
        release_year="2021"
    )
    game3 = Game(
        app_id="3",
        name="Test Game 3",
        developer="",  # Missing developer
        publisher="Pub 3",
        release_year=""  # Missing release year
    )

    manager.get_real_games = Mock(return_value=[game1, game2, game3])
    return manager


@pytest.fixture
def metadata_service(mock_appinfo_manager, mock_game_manager):
    """Create a MetadataService instance with mocks."""
    return MetadataService(mock_appinfo_manager, mock_game_manager)


class TestMetadataService:
    """Test suite for MetadataService."""

    # === SINGLE GAME METADATA ===

    def test_get_game_metadata_with_defaults(self, metadata_service, mock_appinfo_manager):
        """Test getting metadata with defaults from game object."""
        # Setup
        mock_appinfo_manager.get_app_metadata.return_value = {'name': 'Original Name'}
        game = Game(
            app_id="1",
            name="Test Game",
            developer="Test Dev",
            publisher="Test Pub",
            release_year="2020"
        )

        # Execute
        result = metadata_service.get_game_metadata("1", game)

        # Assert
        assert result['name'] == 'Original Name'  # From appinfo
        assert result['developer'] == 'Test Dev'  # From game (default)
        assert result['publisher'] == 'Test Pub'  # From game (default)
        assert result['release_date'] == '2020'  # From game (default)

    def test_get_game_metadata_no_defaults(self, metadata_service, mock_appinfo_manager):
        """Test getting metadata without game object."""
        # Setup
        mock_appinfo_manager.get_app_metadata.return_value = {'name': 'Test', 'developer': 'Dev'}

        # Execute
        result = metadata_service.get_game_metadata("1")

        # Assert
        assert result == {'name': 'Test', 'developer': 'Dev'}

    def test_set_game_metadata(self, metadata_service, mock_appinfo_manager):
        """Test setting metadata for a single game."""
        # Setup
        metadata = {'name': 'New Name', 'developer': 'New Dev'}

        # Execute
        metadata_service.set_game_metadata("1", metadata)

        # Assert
        mock_appinfo_manager.set_app_metadata.assert_called_once_with("1", metadata)
        mock_appinfo_manager.save_appinfo.assert_called_once()

    def test_get_original_metadata(self, metadata_service, mock_appinfo_manager):
        """Test getting original unmodified metadata."""
        # Setup
        mock_appinfo_manager.modifications = {
            "1": {
                "original": {"name": "Original", "developer": "Original Dev"}
            }
        }

        # Execute
        result = metadata_service.get_original_metadata("1")

        # Assert
        assert result == {"name": "Original", "developer": "Original Dev"}

    def test_get_original_metadata_with_fallback(self, metadata_service, mock_appinfo_manager):
        """Test getting original metadata with fallback."""
        # Setup
        mock_appinfo_manager.modifications = {}
        fallback = {"name": "Fallback", "developer": "Fallback Dev"}

        # Execute
        result = metadata_service.get_original_metadata("1", fallback)

        # Assert
        assert result == fallback

    # === BULK METADATA ===

    def test_apply_bulk_metadata_simple(self, metadata_service, mock_appinfo_manager):
        """Test applying metadata to multiple games without name modifications."""
        # Setup
        games = [
            Game(app_id="1", name="Game 1"),
            Game(app_id="2", name="Game 2"),
            Game(app_id="3", name="Game 3")
        ]
        metadata = {'developer': 'Bulk Dev', 'publisher': 'Bulk Pub'}

        # Execute
        count = metadata_service.apply_bulk_metadata(games, metadata)

        # Assert
        assert count == 3
        assert mock_appinfo_manager.set_app_metadata.call_count == 3
        mock_appinfo_manager.save_appinfo.assert_called_once()

    def test_apply_bulk_metadata_with_name_mods(self, metadata_service, mock_appinfo_manager):
        """Test applying metadata with name modifications."""
        # Setup
        games = [Game(app_id="1", name="Game")]
        metadata = {'developer': 'Dev'}
        name_mods = {'prefix': '[TEST] ', 'suffix': ' (2024)', 'remove': 'Game'}

        # Execute
        count = metadata_service.apply_bulk_metadata(games, metadata, name_mods)

        # Assert
        assert count == 1
        # Check that set_app_metadata was called with modified name
        call_args = mock_appinfo_manager.set_app_metadata.call_args[0]
        assert call_args[0] == "1"
        assert call_args[1]['name'] == '[TEST]  (2024)'  # "Game" removed, prefix/suffix added
        assert call_args[1]['developer'] == 'Dev'

    def test_apply_bulk_metadata_empty_list(self, metadata_service):
        """Test applying metadata to empty game list."""
        # Execute
        count = metadata_service.apply_bulk_metadata([], {'developer': 'Dev'})

        # Assert
        assert count == 0

    # === NAME MODIFICATIONS ===

    def test_apply_name_modifications_prefix(self, metadata_service):
        """Test applying prefix modification."""
        # Execute
        result = metadata_service._apply_name_modifications("Game", {'prefix': '[TEST] '})

        # Assert
        assert result == '[TEST] Game'

    def test_apply_name_modifications_suffix(self, metadata_service):
        """Test applying suffix modification."""
        # Execute
        result = metadata_service._apply_name_modifications("Game", {'suffix': ' (2024)'})

        # Assert
        assert result == 'Game (2024)'

    def test_apply_name_modifications_remove(self, metadata_service):
        """Test applying remove modification."""
        # Execute
        result = metadata_service._apply_name_modifications("Test Game Demo", {'remove': ' Demo'})

        # Assert
        assert result == 'Test Game'

    def test_apply_name_modifications_all(self, metadata_service):
        """Test applying all modifications combined."""
        # Execute
        result = metadata_service._apply_name_modifications(
            "Game Demo",
            {'prefix': '[TEST] ', 'suffix': ' (2024)', 'remove': ' Demo'}
        )

        # Assert
        assert result == '[TEST] Game (2024)'

    # === MISSING METADATA ===

    def test_find_missing_metadata_some(self, metadata_service, mock_game_manager):
        """Test finding games with missing metadata."""
        # Execute
        result = metadata_service.find_missing_metadata()

        # Assert
        assert len(result) == 1
        assert result[0].app_id == "3"  # Game 3 has missing developer and release_year

    def test_find_missing_metadata_none(self, metadata_service, mock_game_manager):
        """Test finding missing metadata when all games are complete."""
        # Setup - all games have complete metadata
        game1 = Game(app_id="1", name="Game 1", developer="Dev", publisher="Pub", release_year="2020")
        game2 = Game(app_id="2", name="Game 2", developer="Dev", publisher="Pub", release_year="2021")
        mock_game_manager.get_real_games.return_value = [game1, game2]

        # Execute
        result = metadata_service.find_missing_metadata()

        # Assert
        assert len(result) == 0

    def test_find_missing_metadata_all(self, metadata_service, mock_game_manager):
        """Test finding missing metadata when all games are incomplete."""
        # Setup - all games missing metadata
        game1 = Game(app_id="1", name="Game 1", developer="", publisher="", release_year="")
        game2 = Game(app_id="2", name="Game 2", developer="", publisher="", release_year="")
        mock_game_manager.get_real_games.return_value = [game1, game2]

        # Execute
        result = metadata_service.find_missing_metadata()

        # Assert
        assert len(result) == 2

    # === RESTORE ===

    def test_get_modification_count_zero(self, metadata_service, mock_appinfo_manager):
        """Test getting modification count when no modifications exist."""
        # Setup
        mock_appinfo_manager.get_modification_count.return_value = 0

        # Execute
        count = metadata_service.get_modification_count()

        # Assert
        assert count == 0

    def test_get_modification_count_some(self, metadata_service, mock_appinfo_manager):
        """Test getting modification count when modifications exist."""
        # Setup
        mock_appinfo_manager.get_modification_count.return_value = 5

        # Execute
        count = metadata_service.get_modification_count()

        # Assert
        assert count == 5

    def test_restore_modifications(self, metadata_service, mock_appinfo_manager):
        """Test restoring all metadata modifications."""
        # Setup
        mock_appinfo_manager.restore_modifications.return_value = 3

        # Execute
        restored = metadata_service.restore_modifications()

        # Assert
        assert restored == 3
        mock_appinfo_manager.restore_modifications.assert_called_once()
