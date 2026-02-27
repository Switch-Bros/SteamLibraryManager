# Changelog

All notable changes to Steam Library Manager will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
