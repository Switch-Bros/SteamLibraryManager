# Changelog

All notable changes to Steam Library Manager will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.2] - 2026-03-17

### Changed
- Split `game_service.load_and_prepare()` into focused submethods.
- Centralize timeout/delay constants in `utils/timeouts.py`.
- Standardize copyright headers on all source files.

### Added
- 24 database migration tests covering schema v3 through v9.

## [1.3.1] - 2026-03-15

### Fixed
- **Packaging:** Database schema SQL file was missing from built wheel/package,
  causing database creation to fail on first run (AUR, pip install).
- Removed unused legacy database_schema.sql (superseded by core/db/schema.sql).

## [1.3.0] - 2026-03-15

### Added
- **Smart Collections:** Automatic sidecar backup (smart_collections.json) on
  every create/update/delete. Auto-recovery on startup when the database is
  empty, so Smart Collections survive installation or device changes.
- **Curators:** Auto-register existing curators from Steam collections when
  opening the management dialog. Fuzzy name matching strips emojis, punctuation,
  and whitespace for reliable preset detection.
- **Curators:** Cloud storage parser as additional source for collection names,
  catching dynamic/filter-based collections that game_manager does not see.

### Fixed
- **Collections:** Steam-internal names "favorite" and "hidden" (lowercase
  English) are now recognized as protected system collections and sort
  correctly instead of appearing alphabetically in the sidebar.
- **Smart Collections:** Brain emoji now appears as suffix (after name, before
  count) consistent with dynamic and external platform collection emojis.
- **Smart Collections:** Name validation in SmartCollectionManager.create()
  prevents saving collections without a name.
- **Curators:** Popular/Top Curators dialogs now have scroll areas and a
  max height so they don't fill the entire screen on smaller displays.

## [1.2.8] - 2026-03-14

### Fixed
- **Smart Collections:** Achievement percentage, total, unlocked, and perfect
  were never loaded from database into Game objects at startup, causing
  achievement-based Smart Collections to always show 0 results.
- **Smart Collections:** tag_ids were not transferred during database
  enrichment, breaking tag-based filtering.
- **Smart Collections:** BETWEEN operator now auto-swaps reversed min/max
  values so "BETWEEN 50 30" works the same as "BETWEEN 30 50".

### Changed
- **Release Dates:** Refactored release_year from string to UNIX timestamp
  (int) across the entire codebase. Dates are now stored and compared as
  timestamps internally, displayed as localized strings only in the UI.
  Added to_timestamp() and year_from_timestamp() date conversion helpers.
- **Date Parsing:** Steam API date strings (English month names like
  "Oct 10, 2007") are now parsed correctly regardless of system locale.

## [1.2.7] - 2026-03-12

### Fixed
- **Security:** JWT access tokens no longer leak into log files when HTTP
  errors occur. Exception messages are now sanitized to show only the status
  code or exception type.
- **Security:** Token file (tokens.enc) and settings file (settings.json)
  are now written with owner-only permissions (0o600).
- **Enrichment:** Fixed PEGI track counter logic in EnrichAllCoordinator
  that could cause double-increment or missed completion signals.
- **Stability:** Fixed database connection leaks in menu builder and
  enrichment coordinator (could cause "database is locked" errors).
- **Thread Safety:** HLTB client endpoint discovery is now protected by a
  threading lock to prevent concurrent races.
- **Thread Cleanup:** External Games dialog now properly waits for
  background threads before closing.

### Changed
- Removed UIHelper dependency from CategoryService (service layer violation).
- Replaced silent exception swallowing with proper logging in achievement
  enrichment and HLTB API endpoint discovery.

## [1.2.6] - 2026-03-12

### Fixed
- **Dock Integration:** Unified StartupWMClass across all .desktop files
  to match Wayland app_id (io.github.switch_bros.SteamLibraryManager).
  Fixes Cairo Dock, Plank, and other docks not recognizing the app window.

## [1.2.5] - 2026-03-11

### Fixed
- **AppImage Update:** Desktop entry now updates after AppImage self-update,
  so the application launcher always points to the correct binary.
- **AppImage Naming:** Simplified to version-free filename
  (SteamLibraryManager-x86_64.AppImage) to avoid stale paths after updates.
- **Pyright:** Fixed type warnings in update service (QByteArray conversion,
  optional QNetworkReply checks).

### Changed
- **AUR:** Removed checkdepends/check() to fix paru dependency resolution.

## [1.2.4] - 2026-03-11

### Added
- **Steam Deck Support:** Responsive UI scaling for 1280x800 displays.
  Gallery images, metadata grid, and spacing automatically adapt to smaller screens.
  Handles rotated displays (Deck is natively 800x1280 portrait).
- **Library Auto-Sync:** Automatically reconcile saved library paths with
  Steam's libraryfolders.vdf on startup. Removes dead paths (e.g. after drive swap),
  adds new paths Steam reports. Skips dead VDF entries.
- **Multi-Format Packaging:** New .deb, .rpm, and tar.gz packages alongside
  existing AppImage and AUR. CI/CD builds all formats automatically on release.

### Fixed
- **Tests:** Fixed 3 pre-existing test failures in test_file_actions.py
  (Mock parent widget crash in force_save dialog)

## [1.2.0] - 2026-03-04

### Changed
- **Module Rename:** `src/` renamed to `steam_library_manager/` for PEP 423 compliance.
  The generic module name `src` conflicts with other packages when installed system-wide.
  `steam_library_manager` is globally unique and enables proper Python packaging.
  (Requested by AUR user yochananmarqos)

### Fixed
- **AUR:** DATA_DIR now uses XDG_DATA_HOME for all install types (fixes PermissionError crash)
- **AUR:** Icons use correct reverse-DNS names (io.github.switch_bros.SteamLibraryManager)
- **Images:** All PEGI icons, default placeholders, and QR login converted from PNG to WebP

## [1.1.1] - 2026-02-27

### Added
- **Steam Library Management:** Full collection management with cloud sync
- **16 AutoCat Types:** Genre, Tags, Playtime, HLTB, Review Score, Developer,
  Publisher, Platform, Language, Release Year, Store Tags, Flags, PEGI Rating,
  Steam Deck Compatibility, ProtonDB Rating, Hybrid Rule Groups
- **Smart Collections:** AND/OR/NOT boolean logic with 21 filter fields and
  12 operators (what Steam can't do)
- **External Games:** 9 platform parsers (Heroic Epic/GOG/Amazon, Lutris,
  Bottles, itch.io, Flatpak, ShortcutsVDF, ROM Emulation with 16 emulators
  across 10 systems)
- **Data Enrichment:** HLTB (94.8% match rate via Steam Import API), ProtonDB,
  Steam Deck compatibility, Steam Store metadata, Steam Curator recommendations
  with overlap scoring
- **Secure Auth:** QR code + password login, keyring + AES-GCM fallback token
  storage, automatic token refresh
- **Import/Export:** VDF, CSV (Simple + Full), JSON, Smart Collections JSON,
  Database backup with rotation
- **Library Health Check:** Store availability, data completeness, cache analysis
- **Curator Enhancement:** DB persistence, enrichment pipeline, management dialog,
  auto-discovery (top curators + subscribed), JSON export/import with merge logic
- **Game Discovery:** licensecache decryption (Valve XOR cipher) x packageinfo.vdf
  cross-reference for complete owned games detection (incl. F2P, gifted, key-redeemed)
- **Keyboard Shortcuts:** 15+ shortcuts, layered ESC, Konami code Easter egg
- **Multilingual:** Full English + German UI with zero hardcoded strings and
  separate tag language setting
- **Profiles:** Save/restore complete configuration states
- **AppImage Auto-Update:** GitHub Releases API check, download with progress,
  atomic replace + rollback
- **Dual-Language README:** English + German with dark/light theme support

### Technical
- 186 Python source files, 104 test files, 1567 tests passing
- SQLite database Schema v9 (curators, curator_recommendations tables,
  10 modular database modules using mixin pattern)
- Zero hardcoded strings (complete i18n with 17 JSON files)
- Linux-first with PyQt6 (Wayland + X11)
- Pre-commit hooks: Black, flake8, mypy enforced
