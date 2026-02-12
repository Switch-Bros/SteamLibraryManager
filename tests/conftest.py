# tests/conftest.py
import tempfile
from pathlib import Path
from typing import Generator

import pytest
from pytestqt.qtbot import QtBot
from PyQt6.QtWidgets import QApplication


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
    return '''
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
'''


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