# tests/conftest.py

"""Pytest configuration and shared fixtures for SteamLibraryManager tests."""
import pytest
import json
from pathlib import Path


@pytest.fixture
def mock_config(tmp_path):
    """Provide a test configuration with temporary paths."""
    from src.config import Config

    config = Config()
    config.STEAM_PATH = tmp_path / "steam"
    config.DATA_DIR = tmp_path / "data"
    config.CACHE_DIR = tmp_path / "cache"

    config.STEAM_PATH.mkdir(parents=True, exist_ok=True)
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    return config


@pytest.fixture
def sample_game():
    """Provide a sample Game object for testing."""
    from src.core.game_manager import Game
    return Game(
        app_id='440',
        name='Team Fortress 2',
        playtime_minutes=1337
    )


@pytest.fixture
def mock_cloud_storage_file(tmp_path):
    """Create a temporary cloud storage file with proper Steam directory structure."""
    # Create proper Steam directory structure
    user_id = '123456789'
    steam_path = tmp_path / "steam"
    cloud_dir = steam_path / "userdata" / user_id / "config" / "cloudstorage"
    cloud_dir.mkdir(parents=True, exist_ok=True)

    # Create cloud storage file
    cloud_file = cloud_dir / "cloud-storage-namespace-1.json"

    cloud_data = [
        ["user-collections.from-tag-Action", {
            "key": "user-collections.from-tag-Action",
            "timestamp": 1234567890,
            "value": json.dumps({
                "id": "from-tag-Action",
                "name": "Action",
                "added": [440, 730],
                "removed": []
            })
        }]
    ]

    with open(cloud_file, 'w') as f:
        json.dump(cloud_data, f)

    return steam_path, user_id