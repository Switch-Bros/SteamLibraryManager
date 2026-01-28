# CLAUDE.md - AI Assistant Guidelines for Steam Library Manager

This document provides comprehensive guidance for AI assistants working on the Steam Library Manager codebase.

## Project Overview

Steam Library Manager is a Python-based desktop application for managing Steam game libraries on **Linux and Steam Deck**. It features auto-categorization, metadata editing, cover customization, and integration with Steam APIs.

- **Language:** Python 3.10+
- **GUI Framework:** PyQt6
- **License:** MIT
- **Status:** Active Development (Alpha/Beta)
- **Platform:** Linux-only (Steam Deck compatible)

## Quick Start

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-user.txt

# Run
python src/main.py
```

**Important:** Steam must NOT be running when the application starts.

## Directory Structure

```
SteamLibraryManager/
├── src/
│   ├── main.py                 # Entry point
│   ├── config.py               # Global configuration (singleton dataclass)
│   ├── core/                   # Business logic & data management
│   │   ├── game_manager.py     # Game model & collection management
│   │   ├── appinfo_manager.py  # Steam appinfo.vdf metadata handling
│   │   ├── localconfig_parser.py # Parse localconfig.vdf (categories)
│   │   ├── local_games_loader.py # Load games from Steam directories
│   │   ├── steam_auth.py       # Steam OpenID authentication
│   │   ├── backup_manager.py   # Rolling backup system (default: 5 backups)
│   │   └── steam_assets.py     # Asset & image management
│   ├── ui/                     # PyQt6 GUI components
│   │   ├── main_window.py      # Primary UI window
│   │   ├── components/         # Reusable UI widgets
│   │   │   ├── category_tree.py     # Game tree with multi-select
│   │   │   └── clickable_image.py   # Interactive image widget
│   │   ├── auto_categorize_dialog.py
│   │   ├── metadata_dialogs.py
│   │   ├── game_details_widget.py
│   │   ├── settings_dialog.py
│   │   ├── steam_login_dialog.py
│   │   ├── image_selection_dialog.py
│   │   └── missing_metadata_dialog.py
│   ├── integrations/           # External API clients
│   │   ├── steam_store.py      # Steam Store web scraper
│   │   └── steamgrid_api.py    # SteamGridDB API client
│   └── utils/                  # Utility modules
│       ├── i18n.py             # Internationalization system
│       ├── appinfo.py          # Binary appinfo.vdf parser (complex)
│       ├── acf.py              # Text-based VDF parser
│       ├── manifest.py         # Steam manifest parser
│       ├── manifest_pb2.py     # Protobuf definitions (auto-generated)
│       ├── date_utils.py
│       ├── merge_tags.py
│       └── steam_config_merger.py
├── locales/                    # i18n translation files (JSON)
│   ├── en.json                 # English (primary/fallback)
│   └── de.json                 # German
├── resources/images/           # Static image assets
├── tests/                      # Test files (pytest)
├── requirements-user.txt       # Runtime dependencies
├── requirements-dev.txt        # Development dependencies
└── data/                       # Runtime data (gitignored)
    ├── settings.json           # User settings
    ├── cache/                  # API response cache
    └── custom_metadata.json    # User metadata overrides
```

## Critical Dependencies

**IMPORTANT VERSION CONSTRAINTS:**

| Package | Version | Reason |
|---------|---------|--------|
| `protobuf` | **3.20.3** | v4.x+ breaks `manifest_pb2.py` - DO NOT UPGRADE |
| `PyQt6` | 6.7.1 | Stable version, 6.10.x has issues |
| `pywebview` | 5.3.2 | 6.x has Linux compatibility issues |
| `psutil` | 6.1.0 | 7.x has API changes |

When modifying dependencies, preserve these version pins.

## Architecture Patterns

### Data Model

The `Game` dataclass in `src/core/game_manager.py` is the central model:
- Basic info: `app_id`, `name`, `playtime_minutes`
- Metadata: `developer`, `publisher`, `release_year`, `genres`, `tags`
- Status: `hidden`, `categories`, `favorites`
- Images: `icon_url`, `cover_url`

### Manager Pattern

Core business logic uses manager classes:
- `GameManager` - Game collection operations
- `AppInfoManager` - Binary metadata file handling
- `LocalConfigParser` - VDF category parsing
- `BackupManager` - Rolling backup system

### Configuration

Global config is a singleton dataclass (`src/config.py`):
```python
from src.config import config

# Access settings
config.STEAM_PATH
config.UI_LANGUAGE
config.STEAMGRIDDB_API_KEY

# Save changes
config.save()
```

### Internationalization (i18n)

All user-facing strings MUST use the translation system:

```python
from src.utils.i18n import t

# Simple translation
message = t('ui.menu.file')

# Parameterized translation
message = t('ui.main.games_count', count=42)
```

Translation keys use dot notation. Files are in `locales/*.json`.

**When adding new UI text:**
1. Add the key to `locales/en.json` (required)
2. Add the key to `locales/de.json` (required)
3. Use `t('your.new.key')` in code

### Threading

Long operations use Qt threads with signals:
```python
class GameLoadThread(QThread):
    progress = pyqtSignal(str, int, int)  # message, current, total
    finished = pyqtSignal(bool)
```

Never perform blocking operations on the main thread.

### File Parsing

Two VDF formats are supported:
1. **Text VDF** (`.acf`, `localconfig.vdf`) - Use `src/utils/acf.py`
2. **Binary VDF** (`appinfo.vdf`) - Use `src/utils/appinfo.py`

The binary parser supports versions: 28, 29, 39, 40, 41

## Code Conventions

### Style
- **PEP 8** compliant (enforced via flake8)
- **Type hints** throughout (mypy compatible)
- **Black** for formatting (line length: default)
- Docstrings on classes and key methods

### Imports
```python
# Standard library
import json
from pathlib import Path
from typing import Optional, Dict, List

# Third-party
from PyQt6.QtWidgets import QMainWindow
import requests

# Local
from src.config import config
from src.utils.i18n import t
from src.core.game_manager import Game, GameManager
```

### Error Handling
Always use localized error messages:
```python
try:
    # operation
except (OSError, ValueError) as e:
    print(t('logs.manager.error', error=e))
```

### Circular Import Prevention
Use local imports when needed:
```python
def some_method(self):
    from src.utils.i18n import t  # Local import to avoid circular dependency
```

## Development Workflow

### Running Tests
```bash
pytest tests/
```

### Code Quality
```bash
# Formatting
black src/

# Linting
flake8 src/

# Type checking
mypy src/
```

### Adding New Features

1. **UI Changes**: Modify files in `src/ui/`
2. **Business Logic**: Add to `src/core/`
3. **API Integration**: Add to `src/integrations/`
4. **Utilities**: Add to `src/utils/`
5. **Translations**: Update both `locales/en.json` and `locales/de.json`

### Steam Path Detection

The app auto-detects Steam at:
- `~/.steam/steam`
- `~/.local/share/Steam`

### API Rate Limiting

When scraping Steam Store: **minimum 1.5 seconds between requests**

## Key Files Reference

| File | Purpose |
|------|---------|
| `src/main.py` | Entry point, Steam running check |
| `src/config.py` | Configuration singleton |
| `src/ui/main_window.py` | Main application window |
| `src/core/game_manager.py` | Game model and manager |
| `src/core/appinfo_manager.py` | Metadata editing |
| `src/utils/appinfo.py` | Binary VDF parser |
| `src/utils/i18n.py` | Translation system |
| `locales/en.json` | English translations |

## External Services

| Service | Purpose | Auth Required |
|---------|---------|---------------|
| Steam OpenID | User authentication | No |
| SteamGridDB | Cover images | API key |
| ProtonDB | Linux compatibility | No |
| Steam Store | Tags/metadata scraping | No |

## Common Tasks

### Adding a New Dialog

1. Create `src/ui/your_dialog.py`
2. Import and instantiate from `main_window.py`
3. Add translations to both locale files
4. Connect signals/slots for Qt communication

### Modifying Game Metadata

Use `AppInfoManager`:
```python
from src.core.appinfo_manager import AppInfoManager

manager = AppInfoManager(config.STEAM_PATH)
manager.load_appinfo()
manager.modify_app_metadata(app_id, {'name': 'New Name'})
```

### Adding Translation Keys

1. Edit `locales/en.json`:
```json
{
  "ui": {
    "new_feature": {
      "title": "My Feature",
      "description": "Description with {param}"
    }
  }
}
```

2. Mirror structure in `locales/de.json`

3. Use in code:
```python
title = t('ui.new_feature.title')
desc = t('ui.new_feature.description', param='value')
```

## Gotchas and Warnings

1. **Steam must not be running** when the app starts (checked in `main.py`)
2. **Never upgrade protobuf** beyond 3.20.3
3. **Binary appinfo.vdf** requires CRC32 checksums on write
4. **main_window.py is large** (~49KB) - consider the impact of changes
5. **API keys are Base64-encoded** in settings.json (not encrypted)
6. **Backup system** keeps max 5 backups by default

## Git Workflow

- Main development happens on feature branches
- Commits should be descriptive
- The `data/` directory is gitignored (user data)
- `.env` files are gitignored (API keys)

## Testing Checklist

Before submitting changes:
- [ ] Steam not running check still works
- [ ] i18n keys exist in both locale files
- [ ] No breaking changes to Game dataclass
- [ ] Backup system still functions
- [ ] Type hints are correct (run mypy)
- [ ] Code is formatted (run black)
- [ ] No lint errors (run flake8)
