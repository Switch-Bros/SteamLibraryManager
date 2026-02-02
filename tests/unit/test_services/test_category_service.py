# tests/unit/test_services/test_category_service.py

"""Tests for CategoryService."""
import pytest
from pathlib import Path
from src.services.category_service import CategoryService
from src.core.game_manager import GameManager, Game
from src.core.localconfig_parser import LocalConfigParser


class TestCategoryService:
    """Tests for CategoryService operations."""

    @pytest.fixture
    def mock_game_manager(self):
        """Create a mock GameManager with test games."""
        manager = GameManager(
            steam_api_key=None,
            cache_dir=Path("/tmp/test_cache"),
            steam_path=Path("/tmp/test_steam")
        )

        # Add test games
        manager.games['100'] = Game(app_id='100', name='Game 1')
        manager.games['100'].categories = ['Action', 'RPG']

        manager.games['200'] = Game(app_id='200', name='Game 2')
        manager.games['200'].categories = ['Action']

        manager.games['300'] = Game(app_id='300', name='Game 3')
        manager.games['300'].categories = ['RPG', 'Strategy']

        return manager

    @pytest.fixture
    def mock_parser(self, tmp_path):
        """Create a mock LocalConfigParser."""
        # Create a minimal VDF structure
        vdf_content = {
            'UserLocalConfigStore': {
                'Software': {
                    'Valve': {
                        'Steam': {
                            'Apps': {
                                '100': {'tags': {'0': 'Action', '1': 'RPG'}},
                                '200': {'tags': {'0': 'Action'}},
                                '300': {'tags': {'0': 'RPG', '1': 'Strategy'}}
                            }
                        }
                    }
                }
            }
        }

        parser = LocalConfigParser(tmp_path, "test_user")
        parser.apps = vdf_content['UserLocalConfigStore']['Software']['Valve']['Steam']['Apps']
        return parser

    @pytest.fixture
    def category_service(self, mock_parser, mock_game_manager):
        """Create a CategoryService with mock dependencies."""
        return CategoryService(
            vdf_parser=mock_parser,
            cloud_parser=None,
            game_manager=mock_game_manager
        )

    def test_rename_category_success(self, category_service, mock_game_manager):
        """Test successful category rename."""
        result = category_service.rename_category('Action', 'Action Games')

        assert result is True

        # Check in-memory games
        assert 'Action Games' in mock_game_manager.games['100'].categories
        assert 'Action' not in mock_game_manager.games['100'].categories
        assert 'Action Games' in mock_game_manager.games['200'].categories

    def test_rename_category_duplicate_name(self, category_service):
        """Test rename fails when new name exists."""
        with pytest.raises(ValueError):
            category_service.rename_category('Action', 'RPG')

    def test_delete_category(self, category_service, mock_game_manager):
        """Test category deletion."""
        result = category_service.delete_category('Action')

        assert result is True

        # Check in-memory games
        assert 'Action' not in mock_game_manager.games['100'].categories
        assert 'Action' not in mock_game_manager.games['200'].categories
        # Other categories should remain
        assert 'RPG' in mock_game_manager.games['100'].categories

    def test_delete_multiple_categories(self, category_service, mock_game_manager):
        """Test deleting multiple categories at once."""
        result = category_service.delete_multiple_categories(['Action', 'RPG'])

        assert result is True

        # Check all games
        assert 'Action' not in mock_game_manager.games['100'].categories
        assert 'RPG' not in mock_game_manager.games['100'].categories
        assert 'Action' not in mock_game_manager.games['200'].categories
        # Strategy should remain
        assert 'Strategy' in mock_game_manager.games['300'].categories

    def test_merge_categories(self, category_service, mock_game_manager):
        """Test merging multiple categories into one."""
        result = category_service.merge_categories(
            ['Action', 'RPG', 'Strategy'],
            'Action'  # Merge all into Action
        )

        assert result is True

        # All games should have Action
        assert 'Action' in mock_game_manager.games['100'].categories
        assert 'Action' in mock_game_manager.games['200'].categories
        assert 'Action' in mock_game_manager.games['300'].categories

        # Source categories should be removed
        assert 'RPG' not in mock_game_manager.games['100'].categories
        assert 'Strategy' not in mock_game_manager.games['300'].categories

    def test_create_collection_success(self, category_service):
        """Test creating new collection."""
        result = category_service.create_collection('New Category')

        assert result is True

    def test_create_collection_duplicate(self, category_service):
        """Test creating collection with existing name fails."""
        with pytest.raises(ValueError):
            category_service.create_collection('Action')

    def test_add_app_to_category(self, category_service, mock_game_manager):
        """Test adding app to category."""
        result = category_service.add_app_to_category('200', 'Strategy')

        assert result is True
        assert 'Strategy' in mock_game_manager.games['200'].categories

    def test_remove_app_from_category(self, category_service, mock_game_manager):
        """Test removing app from category."""
        result = category_service.remove_app_from_category('100', 'Action')

        assert result is True
        assert 'Action' not in mock_game_manager.games['100'].categories
        # Other categories should remain
        assert 'RPG' in mock_game_manager.games['100'].categories

    def test_get_all_categories(self, category_service, mock_game_manager):
        """Test getting all categories."""
        categories = category_service.get_all_categories()

        assert isinstance(categories, dict)
        assert 'Action' in categories
        assert 'RPG' in categories
        assert 'Strategy' in categories
        assert categories['Action'] == 2  # Games 100 and 200
        assert categories['RPG'] == 2  # Games 100 and 300

    def test_get_active_parser_with_cloud(self):
        """Test that cloud parser is preferred when available."""
        from unittest.mock import Mock

        vdf_parser = Mock()
        cloud_parser = Mock()
        game_manager = Mock()

        service = CategoryService(vdf_parser, cloud_parser, game_manager)

        assert service.get_active_parser() == cloud_parser

    def test_get_active_parser_without_cloud(self):
        """Test that VDF parser is used when cloud not available."""
        from unittest.mock import Mock

        vdf_parser = Mock()
        game_manager = Mock()

        service = CategoryService(vdf_parser, None, game_manager)

        assert service.get_active_parser() == vdf_parser