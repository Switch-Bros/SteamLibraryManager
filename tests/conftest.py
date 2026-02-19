# tests/conftest.py
import os
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

# Ensure Qt can run headless (CI runners have no display server)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot


@pytest.fixture(scope="session")
def qapp():
    """QApplication instance for all Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def qtbot(qapp, request):
    """Provide qtbot fixture with automatic cleanup."""
    bot = QtBot(request)
    yield bot
    if hasattr(bot, "cleanup"):
        bot.cleanup()


@pytest.fixture
def temp_db_path() -> Generator[Path, None, None]:
    """Temporary SQLite database file path."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = Path(f.name)
    yield path
    if path.exists():
        path.unlink()


@pytest.fixture
def temp_vdf_content() -> str:
    """Minimal valid VDF content for testing."""
    return """
"appinfo"
{
    "12345"
    {
        "common"
        {
            "name" "Test Game"
            "developer" "TestDev"
            "publisher" "TestPub"
        }
    }
}
"""


@pytest.fixture
def temp_vdf_file(temp_vdf_content) -> Generator[Path, None, None]:
    """Write temporary VDF file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".vdf", delete=False) as f:
        f.write(temp_vdf_content)
        path = Path(f.name)
    yield path
    if path.exists():
        path.unlink()


@pytest.fixture
def isolated_token_store(tmp_path) -> Path:
    """Simulate a token storage directory."""
    token_dir = tmp_path / "tokens"
    token_dir.mkdir()
    return token_dir


@pytest.fixture
def mock_cloud_storage_file(tmp_path):
    """Create a temporary cloud storage JSON file for testing.

    Returns:
        Tuple of (steam_path, user_id) for initializing CloudStorageParser.
    """
    import json

    user_id = "12345678"
    cloud_dir = tmp_path / "userdata" / user_id / "config" / "cloudstorage"
    cloud_dir.mkdir(parents=True)

    cloud_data = [
        [
            "user-collections.from-tag-Action",
            {
                "key": "user-collections.from-tag-Action",
                "timestamp": 1700000000,
                "value": json.dumps(
                    {
                        "id": "from-tag-Action",
                        "name": "Action",
                        "added": [440],
                        "removed": [],
                    }
                ),
                "version": "1234",
            },
        ]
    ]

    cloud_file = cloud_dir / "cloud-storage-namespace-1.json"
    cloud_file.write_text(json.dumps(cloud_data))

    return tmp_path, user_id


@pytest.fixture
def database(tmp_path):
    """In-memory-style Database using a temp file (schema loaded from SQL)."""
    from src.core.database import Database

    db_path = tmp_path / "test_metadata.db"
    db = Database(db_path)
    yield db
    db.close()


@pytest.fixture
def sample_database_entries():
    """Sample DatabaseEntry objects for testing."""
    from src.core.database import DatabaseEntry

    return [
        DatabaseEntry(
            app_id=440,
            name="Team Fortress 2",
            app_type="game",
            developer="Valve",
            publisher="Valve",
            genres=["Action", "Free to Play"],
            platforms=["windows", "linux", "mac"],
            is_free=True,
            last_updated=1700000000,
        ),
        DatabaseEntry(
            app_id=570,
            name="Dota 2",
            app_type="game",
            developer="Valve",
            publisher="Valve",
            genres=["Strategy", "Free to Play"],
            platforms=["windows", "linux", "mac"],
            is_free=True,
            release_date=1373328000,
            last_updated=1700000000,
        ),
        DatabaseEntry(
            app_id=730,
            name="Counter-Strike 2",
            app_type="game",
            developer="Valve",
            publisher="Valve",
            genres=["Action", "FPS"],
            tags=["Competitive", "Shooter"],
            platforms=["windows", "linux"],
            review_score=9,  # Overwhelmingly Positive category
            review_percentage=83,
            review_count=7000000,
            last_updated=1700000000,
        ),
    ]


@pytest.fixture
def mock_config():
    """Mock the global config object from src.config.

    Provides a MagicMock that stands in for the Config singleton so that
    tests which instantiate GameManager (or other classes that import
    ``src.config.config`` at runtime) do not depend on a real Steam
    installation or settings file.
    """
    fake_config = MagicMock()
    fake_config.get_detected_user.return_value = (None, None)
    fake_config.STEAM_ACCESS_TOKEN = None
    with patch("src.config.config", fake_config):
        yield fake_config
