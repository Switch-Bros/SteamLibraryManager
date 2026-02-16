 Projektfortschritt: SteamLibraryManager

  ┌────────┬──────────────────────────┬──────────────────────────────────────┐
  │ Phase  │       Fortschritt        │               Status                 │
  ├────────┼──────────────────────────┼──────────────────────────────────────┤
  │ GESAMT │ ██████████████████░░ 72% │ Phase 0-4 komplett, Phase 5.1+5.2 done │
  └────────┴──────────────────────────┴──────────────────────────────────────┘

  ---
  Phase 0 — Stability & Groundwork ████████████████████ 100%

  ┌───────────────┬───────────────────────┬──────────────────────────────────────────────┐
  │   Sub-Phase   │      Fortschritt      │                   Details                    │
  ├───────────────┼───────────────────────┼──────────────────────────────────────────────┤
  │ 0.1 i18n CI   │ ████████████████████  │ scripts/validate_i18n.py (240 Zeilen),       │
  │ Check         │ 100%                  │ 5-Pass-Validation, in GitHub Actions         │
  ├───────────────┼───────────────────────┼──────────────────────────────────────────────┤
  │ 0.2 Smoke     │ ████████████████████  │ tests/test_smoke.py (81 Tests), inkl.        │
  │ Tests in CI   │ 100%                  │ Circular-Import-Check                        │
  ├───────────────┼───────────────────────┼──────────────────────────────────────────────┤
  │ 0.3 Central   │ ████████████████████  │ src/core/logging.py, i18n-kompatibel, in     │
  │ Logging       │ 100%                  │ main.py integriert                           │
  └───────────────┴───────────────────────┴──────────────────────────────────────────────┘

  ---
  Phase 1 — Critical Fixes & Performance ████████████████████ 100%

  Sub-Phase: 1.1 UNCATEGORIZED Fix
  Fortschritt: ████████████████████ 100%
  Details: Depressurizer-kompatible Logik, game_query_service.py, Ghost-App-Filter
  ────────────────────────────────────────
  Sub-Phase: 1.2 Game Type Field
  Fortschritt: ████████████████████ 100%
  Details: app_type in Game dataclass, 8 Typen erkannt, is_real_game()
  ────────────────────────────────────────
  Sub-Phase: 1.3 Lokale Datenbank
  Fortschritt: ████████████████████ 100%
  Details: 34 Tabellen, Schema v2, 26 Indexes, 7 Views, 3 Trigger, Batch-Import

  ---
  Phase 2 — Cloud Sync & Auth ████████████████████ 100%

  Sub-Phase: 2.1 Cloud Sync
  Fortschritt: ████████████████████ 100%
  Details: Read/Write/Backup funktioniert, mtime-Konflikterkennung.
  ────────────────────────────────────────
  Sub-Phase: 2.2 Auth Hardening
  Fortschritt: ████████████████████ 100%
  Details: Keyring + AES-GCM Fallback, Token-Refresh mit Retry.

  ---
  Phase 3 — Architecture & Refactoring ████████████████████ 100%

  Sub-Phase: 3.1 Split Large Classes
  Fortschritt: ████████████████████ 100%
  Details: main_window.py = 491 Zeilen! 4 Builders, 10 Actions, 7 Handlers
  ────────────────────────────────────────
  Sub-Phase: 3.2 Bootstrap Service
  Fortschritt: ████████████████████ 100%
  Details: Progressive Loading, Non-Blocking UI, 4 Phasen, Concurrent Workers

  ---
  Phase 3.5 — Menu Redesign ████████████████████ 100%

  Sub-Phase: Menu-Struktur
  Fortschritt: ████████████████████ 100%
  Details: 5 Top-Menus, 25+ Submenus, komplett aufgebaut
  ────────────────────────────────────────
  Sub-Phase: Typ-/Plattform-/Status-Filter
  Fortschritt: ████████████████████ 100%
  Details: Alle wired zu FilterService, funktioniert!
  ────────────────────────────────────────
  Sub-Phase: Sprach-Filter
  Fortschritt: ████████████████████ 100%
  Details: 15 Sprachen, OR-Logik, funktioniert
  ────────────────────────────────────────
  Sub-Phase: Sortierung
  Fortschritt: ████████████████████ 100%
  Details: SortKey enum (Name/Playtime/LastPlayed/ReleaseDate), Radio-Buttons im Menu,
    dynamische Sortierung in CategoryPopulator + SearchResults. Tests: 10 neue.
  ────────────────────────────────────────
  Sub-Phase: Statistiken
  Fortschritt: ████████████████████ 100%
  Details: StatisticsDialog mit 4 Tabs (Overview, Genre, Plattform, Top 10),
    echte Daten aus GameManager, i18n komplett (en+de).
  ────────────────────────────────────────
  Sub-Phase: Ansichtsmodi + Theme
  Fortschritt: — GESTRICHEN —
  Details: KDE/Qt6 Theme reicht. View-Mode-Code + i18n-Keys entfernt.

  ---
  Phase 3.6 — Enhanced Export ████████████████████ 100%

  Sub-Phase: 3.6.1 Batch Steam API
  Fortschritt: ████████████████████ 100%
  Details: IStoreBrowseService/GetItems/v1, 50er-Batches, Rate-Limiting, Retry
  ────────────────────────────────────────
  Sub-Phase: 3.6.2 CSV Export
  Fortschritt: ████████████████████ 100%
  Details: csv_exporter.py — Simple (3 Spalten) + Full (22 Spalten), im Menu wired.
    Tests: 9 neue.
  ────────────────────────────────────────
  Sub-Phase: 3.6.3 JSON Export
  Fortschritt: ████████████████████ 100%
  Details: json_exporter.py — Alle Metadaten, strukturiert. Tests: 6 neue.
  ────────────────────────────────────────
  Sub-Phase: 3.6.4 VDF Import
  Fortschritt: ████████████████████ 100%
  Details: vdf_importer.py — Collections aus VDF laden, im Menu wired. Tests: 7 neue.
  ────────────────────────────────────────
  Sub-Phase: 3.6.5 DB Backup UI
  Fortschritt: ████████████████████ 100%
  Details: Export + Import im Menu wired zu BackupManager.

  ---
  Phase 3.7 — shortcuts.vdf Manager → VERSCHOBEN auf Phase 6

  ---
  Phase 4 — Depressurizer Parity ████████████████████ 100%

  ┌──────────────┬───────────────────────┬───────────────────────────────────────────────┐
  │  Sub-Phase   │      Fortschritt      │                    Details                    │
  ├──────────────┼───────────────────────┼───────────────────────────────────────────────┤
  │ 4.1 AutoCat  │ ████████████████████  │ 15/15 fertig! Inkl. Curator (Steam Store      │
  │ Types (15    │ 100%                  │ API, URL-History, Emoji) + Group/Presets       │
  │ Ziel)        │                       │ (Save/Load/Delete, JSON-Persistenz)            │
  ├──────────────┼───────────────────────┼───────────────────────────────────────────────┤
  │ 4.2 Advanced │ ████████████████████  │ Typ/Plattform/Status/Sprache-Toggle +         │
  │  Filter      │ 100%                  │ Regex-Suche (/pattern). SortKey in State.     │
  ├──────────────┼───────────────────────┼───────────────────────────────────────────────┤
  │ 4.3 Backup & │ ████████████████████  │ Timestamped Backups, Auto-Rotation, Restore   │
  │  Restore     │ 100%                  │ mit Safety-Backup, DB-Backup im Menu          │
  ├──────────────┼───────────────────────┼───────────────────────────────────────────────┤
  │ 4.4 Profile  │ ████████████████████  │ CRUD, Import/Export, UI-Dialog, alles wired   │
  │ System       │ 100%                  │ sort_key statt view_mode                      │
  └──────────────┴───────────────────────┴───────────────────────────────────────────────┘

  ---
  Phase 5 — Unique Features ████████░░░░░░░░░░░░ 40%

  Sub-Phase: 5.1 Steam Deck Optimizer
  Fortschritt: ████████████████████ 100%
  Details: DeckEnrichmentThread, Deck-Filter, AutoCat by Deck, 32 Tests
  ────────────────────────────────────────
  Sub-Phase: 5.2 Achievement Hunter
  Fortschritt: ████████████████████ 100%
  Details: ISteamUserStats API (Schema + Player + Global Rarity),
    AchievementEnrichmentThread, Achievement-Filter (5 Buckets), AutoCat by Achievements,
    UI-Progress im Detail-Panel (Gold #FDE100 bei Perfect Games), 64 neue Tests.
    Refactoring: game_details_widget.py 1014→458 Zeilen (4 Module: info_label.py,
    category_list.py, details_ui_builder.py). build_detail_grid() Helper für
    wiederverwendbare QGridLayout-Rows mit col_widths-Steuerung.
  ────────────────────────────────────────
  Sub-Phase: 5.3 Smart Collections
  Fortschritt: ░░░░░░░░░░░░░░░░░░░░ 0%
  Details: Design-Dokument existiert, kein Code
  ────────────────────────────────────────
  Sub-Phase: 5.4 Hybrid AutoCat
  Fortschritt: ░░░░░░░░░░░░░░░░░░░░ 0%
  Details: —
  ────────────────────────────────────────
  Sub-Phase: (5.5 HLTB — eigentlich Phase 6.1)
  Fortschritt: ███████████████████░ 95%
  Details: Komplett! 75.4% Match-Rate, 60 Tests

  ---
  Phase 6 — Data & Performance ████████░░░░░░░░░░░░ 40%

  Sub-Phase: 6.1 HLTB Integration
  Fortschritt: ███████████████████░ 95%
  Details: Client komplett, AutoCat, DB, UI. Fehlt: Steam Import API (optional)
  ────────────────────────────────────────
  Sub-Phase: 6.2 ProtonDB Integration
  Fortschritt: █████░░░░░░░░░░░░░░░ 25%
  Details: Felder in Game-Dataclass, Test-File. Fehlt: API-Client, Enrichment
  ────────────────────────────────────────
  Sub-Phase: 6.5 External Games (Epic/GOG)
  Fortschritt: ░░░░░░░░░░░░░░░░░░░░ 0%
  Details: —

  ---
  Phase 7 — Polish & Release ████████░░░░░░░░░░░░ 43%

  Sub-Phase: 7.1 UI/UX Polish
  Fortschritt: ████████████░░░░░░░░ 55%
  Details: Inter-Font, FontHelper, Context-Menus, Detail-Panel Refactoring
    (4 Module, alle <500 Zeilen). Fehlt: Drag&Drop, Keyboard-Shortcuts,
    ImageBrowser Pagination (SteamGridDB seitenweise laden)
  ────────────────────────────────────────
  Sub-Phase: 7.2 Documentation
  Fortschritt: ██████░░░░░░░░░░░░░░ 30%
  Details: README, CLAUDE.md. Fehlt: User Manual, Tutorials, FAQ
  ────────────────────────────────────────
  Sub-Phase: 7.3 Packaging
  Fortschritt: ██████████░░░░░░░░░░ 50%
  Details: Flatpak-Config + AppImage-Script. Fehlt: CI/CD, Release-Automation
  ────────────────────────────────────────
  Sub-Phase: 7.4 Testing & Hardening
  Fortschritt: ██████████████░░░░░░ 70%
  Details: 801 Tests (827 collected), 0 Failures. Fehlt: Coverage-Audit, ruff/mypy-Enforcement

  ---
  Zahlen auf einen Blick

  ┌─────────────────────┬───────────────────────────────────────────┐
  │       Metrik        │                   Wert                    │
  ├─────────────────────┼───────────────────────────────────────────┤
  │ Python-Quelldateien │ 111                                       │
  ├─────────────────────┼───────────────────────────────────────────┤
  │ Testdateien         │ 55                                        │
  ├─────────────────────┼───────────────────────────────────────────┤
  │ Tests (passed)      │ 801                                       │
  ├─────────────────────┼───────────────────────────────────────────┤
  │ DB-Tabellen         │ 34                                        │
  ├─────────────────────┼───────────────────────────────────────────┤
  │ i18n-Sprachen       │ 2 (EN/DE)                                 │
  ├─────────────────────┼───────────────────────────────────────────┤
  │ AutoCat-Typen       │ 16/16                                     │
  ├─────────────────────┼───────────────────────────────────────────┤
  │ API-Integrationen   │ 6 (Steam, HLTB, SteamGridDB, Steam Store, │
  │                     │   Steam Curator, ISteamUserStats)          │
  ├─────────────────────┼───────────────────────────────────────────┤
  │ Export-Formate      │ 4 (VDF, CSV Simple, CSV Full, JSON)        │
  ├─────────────────────┼───────────────────────────────────────────┤
  │ Import-Formate      │ 2 (VDF, DB Backup)                         │
  └─────────────────────┴───────────────────────────────────────────┘
