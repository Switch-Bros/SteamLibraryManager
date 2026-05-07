# Changelog

All notable changes to Steam Library Manager will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.5] - 2026-05-07

### Fixed
- **Critical: Metadata edits now actually visible to Steam.** A latent bug
  caused `update_app_metadata` to write into `data["common"]` (top-level)
  while Steam reads from `data["appinfo"]["common"]`. As a result, every
  metadata edit since the feature was introduced silently went into a
  parallel section that Steam ignored - users saw the change in SLM but
  never in the Steam Library. The writer now targets the correct path,
  cleans up stale `data["common"]` entries from older SLM versions, and
  the drift detector compares against the path Steam actually reads.
- The `_find_common_section` lookup order is reversed to match Steam's
  reading order (`appinfo.common` first, top-level `common` as fallback).

### Added
- **Auto-Reapply on startup**: `AppInfoManager.verify_and_reapply()` runs
  after every `load_appinfo`. If Steam overwrote the file with fresh CDN
  data and wiped out the user's edits, SLM detects the drift and re-applies
  the saved modifications immediately - no manual restore button needed.
- **Live file watcher** on `appinfo.vdf` via `QFileSystemWatcher`. While
  SLM is running, any external rewrite of the file (Steam refresh, manual
  edit, etc.) is detected and re-applied. Debounced 800 ms to coalesce
  Steam's burst writes; self-write suppression via timestamp window so the
  watcher does not loop on our own writes.
- **Immediate VDF write after every save**. Previously the binary VDF was
  only flushed on SLM exit, so a crash between save and exit would lose
  the edit. `save_appinfo()` now writes the VDF as soon as the in-memory
  state is dirty.
- **16 new unit tests** covering drift detection, partial drift across
  multiple apps, fallback paths, and the new save-triggers-write behavior.

### Changed
- `update_app_metadata` no longer creates a top-level `common` block;
  always targets `appinfo.common`. Stale top-level blocks are removed on
  the next write so the file converges back to Steam's expected layout.

## [1.4.4] - 2026-05-06

### Added
- **Smart Emulator Detection** - SLM detects 9 emulators (Eden, Citron, Ryujinx,
  Cemu, Dolphin, Azahar, RetroArch, PPSSPP, melonDS, DOSBox) by reading their
  own config files for game directories. No more hardcoded ROM search paths.
- **Settings tab "Emulators"** - per-emulator status, custom game directories,
  default-emulator-per-system picker, executable override.
- **EmuDeck hint provider** - reads `~/emudeck/settings.sh` as a fallback for
  emulators that have no library config of their own. Works around EmuDeck's
  known concatenation bug by parsing `emulationPath` and deriving rom dirs
  ourselves.
- **AppImage auto-discovery** in standard Linux user locations (`~/Applications`,
  `~/AppImages`, `~/Apps`, `~/.local/bin`, `~/bin`) - covers the common case
  where users park AppImages outside the system PATH.
- **Shortcuts importer** - `shortcuts.vdf` non-Steam entries now show up in the
  main library, with their tags surfaced as SLM categories.
- **Bidirectional category sync for shortcuts** - SLM-side category changes
  write back to both `shortcuts.vdf` (Steam UI live read) and `cloud-storage`
  `from-tag-X` collections (Steam library sidebar). Steam shows the collection
  populated after a restart, no manual tagging needed.
- **Manual SteamGridDB search** - the cover picker now has a search box that
  lets you look up a game by name. For non-Steam shortcuts (whose hash appids
  are unknown to SteamGridDB) it auto-runs the name lookup on open.
- **External Games dialog**: deselect-all / select-all toggle button and
  user-resizable column headers.
- DB Schema **v12** with new tables `emulator_settings` and `emulator_games`.

### Fixed
- **Crash on click on non-Steam shortcuts** - Steam Store API was being called
  with negative shortcut appids and crashed on the `None` JSON response. Now
  guarded: appids outside the positive int32 range skip the remote fetch, and
  malformed responses no longer index into `None`.
- **Cover filenames for non-Steam shortcuts** - SLM now writes covers under
  the unsigned uint32 form of the shortcut appid, which is what Steam expects.
  Old signed-form covers are still found by the lookup so existing setups
  keep working.

### Changed
- `ROM_SEARCH_PATHS`, `APPIMAGE_DIRS`, `EMUDECK_LAUNCHER_DIRS` constants
  removed in favour of config-driven emulator discovery.
- `Game.app_id` for shortcuts is now the canonical unsigned uint32 form,
  matching Steam's own convention for cover paths and cloud-storage collection
  entries. Conversion to/from the signed form happens at the shortcuts.vdf
  boundary only.
- `RomParser` is now a thin facade over `EmulatorService`.

## [1.4.3] - 2026-05-05

### Fixed
- **AppImage on Mint 21.3 / Ubuntu 22.04** (GH #13) - Qt 6.5+ requires
  `libxcb-cursor.so.0` for the xcb platform plugin, which older Debian/Ubuntu/
  Mint releases do not ship by default. The library is now bundled into the
  AppImage via `linuxdeploy --library`. Build aborts early if the dependency
  is missing on the build host.

### Changed
- `build-appimage.sh` and `.github/workflows/build-appimage.yml` resolve
  `libxcb-cursor.so.0` via `ldconfig -p` and pass the path to linuxdeploy.
- CI installs `libxcb-cursor0` so the workflow finds the library.

### Added
- Bug-Report-Template Versions-Dropdown auf v1.4.3, v1.4.2, v1.4.0, v1.3.9
  erweitert.

## [1.4.2] - 2026-04-16

### Fixed
- **Statistics i18n** - all chart labels fully translated (Deck status, ProtonDB
  tiers, review scores, PEGI ratings, achievement buckets, playtime ranges).
  Labels built lazily to avoid circular import issues at module init.
- **Genre tab** - falls back to Steam tags when game_genres table is empty.
- **Comparison tab** - triggers on autocomplete selection (not just Enter).
  HLTB values rounded to 1 decimal place.
- **Donut "Others"** overflow bucket label translated.
- **Readable bucket labels** - all internal keys (op_95, lt_1h, etc.) replaced
  with human-readable text in all chart legends.

### Added
- Statistics screenshots (EN + DE) in README.

## [1.4.0] - 2026-04-16

### Added
- **Statistics Dashboard** - complete overhaul with 7 interactive tabs:
  - Overview: 4 metric cards (total games, playtime, never played, perfect games)
    + genre donut chart + top 5 most played bar chart
  - Genre: side-by-side donuts (by count vs by playtime) with insight text
    showing "You own most RPGs but play Shooters the most"
  - Platform: 3 donuts showing real per-platform playtime (Windows/Linux/
    Steam Deck/Mac), Deck compatibility status, and ProtonDB tier distribution
  - Achievements: metric cards (unlocked, rare, ultra-rare, perfect) +
    completion buckets donut + almost-done bar + Trophy Wall with cover art
  - Playtime: playtime buckets + HLTB analysis + shame pile (installed
    never-played games sorted by HLTB estimate)
  - Ratings: PEGI distribution + review score buckets + top 10 developers
  - Comparison: search and compare any 2 games side-by-side across all metrics
- **Chart Engine** - custom QPainter-based DonutChart and BarChart widgets
  with hover effects, responsive legends, and "Others" bucketing. No external
  charting dependencies.
- **Platform Playtime Tracking** - per-platform playtime (Windows, Linux, Mac,
  Steam Deck) persisted in database from Steam API. Shows where you actually
  play instead of just "supported platforms".
- **Playtime Persistence** - game playtime and last-played timestamps saved to
  SQLite database, surviving Steam API outages.

### Changed
- **DB Schema v11** - added playtime_minutes, last_played, playtime_windows,
  playtime_linux, playtime_mac, playtime_deck columns to games table.
- Statistics dialog rebuilt as tabbed package (`ui/dialogs/statistics/`)
  replacing the old 177-line monolithic dialog.

### Fixed
- **API keys not loading from keyring** - circular import at module init time
  prevented TokenStore from loading keys. Now deferred to bootstrap phase.

## [1.3.9] - 2026-04-13

### Improved
- **i18n: Massive cleanup** - eliminated 120+ duplicate translation keys across
  all JSON files. Common terms (Username, Password, Settings, Name, Platform,
  etc.) consolidated into `common.json`. Cloud Sync keys moved from `main.json`
  to `settings.json` where they belong.
- **i18n: rclone setup dialog** - German labels ("Passwort", "Benutzername")
  hardcoded in Python source replaced with proper `t()` calls. English users
  no longer see German UI text.

### Changed
- **DRY: User-Agent constants** - Chrome and app User-Agent strings centralized
  in `config.py` (`USER_AGENT_BROWSER`, `USER_AGENT_APP`), replacing 7 scattered
  hardcoded copies.
- **DRY: Database path** - duplicated `_get_db_path()` in 4 action files replaced
  with a single `MainWindow.db_path` property.

### Fixed
- **Steam Store rate limiting** - increased request interval to 1.5s and added
  automatic 30s backoff on HTTP 429 responses. Prevents Steam from DNS-blocking
  the client during bulk PEGI rating fetches.
- **Network error abort** - all enrichment threads now abort after 3 consecutive
  DNS resolution or rate-limit errors instead of pointlessly retrying thousands
  of requests against an unreachable server.

### Security
- **API keys moved to system keyring** - `STEAM_API_KEY` and `STEAMGRIDDB_API_KEY`
  are now stored in the OS keyring (or encrypted file fallback) instead of
  plaintext `settings.json`. Existing keys are auto-migrated on first launch.

## [1.3.8] - 2026-04-09

### Fixed
- **Steam-Running false positive:** `steam.pipe` persists after Steam exits,
  causing SLM to always detect Steam as running. Now uses non-blocking pipe
  open to check if Steam is actually reading the pipe (ENXIO = not running).
  Fixes GitHub #12.

## [1.3.7] - 2026-04-08

### Fixed
- **Flatpak: Steam-Running detection:** The Steam-running warning never appeared
  when running as Flatpak because `psutil.process_iter()` cannot see host
  processes from inside the sandbox. Now checks for Steam's named pipe
  (`~/.steam/steam.pipe`) first, which is visible via `--filesystem=~/.steam:ro`.
  Falls back to psutil for native installations.

### Changed
- **Flatpak dependencies:** Added missing `pybind11` (Pillow build dependency)
  and `six` (steam library dependency) to Flatpak manifest.

## [1.3.6] - 2026-04-05

### Fixed
- **Crash on First Run (again):** Profile setup dialog crashed with
  `AttributeError: 'ProfileSetupDialog' object has no attribute 'selected_steam_id_64'`.
  The AI-slop refactoring shortened `selected_steam_id_64` to `sid` and
  `selected_display_name` to `name` but main.py still used the old names (GitHub #11).
- **Force Refresh broken:** After HLTB or Steam API enrichment, the force-refresh
  prompt never appeared because `enrichment_starters.py` referenced
  `dialog.wants_force_refresh` instead of the renamed `dialog.force_refresh`.
- **Crash on category drag-drop:** Dragging games onto a category in the sidebar
  crashed because `category_change_handler.py` referenced
  `details_widget.current_game` instead of the renamed `details_widget.game`.
- **Pre-update save broken:** The update dialog tried to call the non-existent
  `game_manager.save_to_cloud()` before restarting. Now correctly calls
  `MainWindow.save_collections()` to persist collections before auto-update.

## [1.3.5] - 2026-03-30

### Fixed
- **Crash on First Run:** Profile setup dialog crashed on startup for new
  users (GitHub #10). The `_found` list attribute shadowed the `_found()`
  signal handler, causing a TypeError when connecting the account scan signal.

## [1.3.4] - 2026-03-24

### Fixed
- **PEGI Enrichment:** Age rating enrichment never worked due to a parameter
  name mismatch in configure() (silent TypeError). Both individual and
  bulk enrichment are now functional.
- **New Games:** Newly purchased games are now automatically synced to the
  database on startup with full metadata and tags from appinfo.vdf.
- **Smart Collections:** Games matched by smart collections no longer appear
  in "Ohne Kategorie" (uncategorized).
- **Enrich All Dialog:** PEGI chain failure no longer blocks the progress
  dialog from closing.

### Added
- **Smart Collections:** PEGI age rating (Altersfreigabe) available as
  filter field (3, 7, 12, 16, 18).

### Changed
- **Flatpak:** Manifest updated with all required finish-args for Lutris,
  Heroic, Bottles, itch.io, and Flatpak game detection.

## [1.3.3] - 2026-03-17

### Fixed
- **Crash:** Games with integer developer/publisher fields in appinfo.vdf
  (e.g. Cherry Tree Comedy Club) caused a TypeError on startup.

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
