 Projektfortschritt: SteamLibraryManager

  ┌────────┬──────────────────────────┬──────────────────────────────────────┐
  │ Phase  │       Fortschritt        │               Status                 │
  ├────────┼──────────────────────────┼──────────────────────────────────────┤
  │ GESAMT │ ████████████████████ 99% │ Phase 0-8 komplett, Flatpak PR pending │
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
Phase 5 — Unique Features ████████████████████ 100%

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
  Fortschritt: ████████████████████ 100%
  Details: Full Boolean-Logic (AND/OR/NOT), 21 FilterFields, 12 Operators,
  Evaluator Engine, SmartCollectionManager (CRUD + Evaluate + Steam Sync),
  Builder Dialog mit Live-Preview, 🧠 Emoji im Tree, Auto-Refresh,
  6 neue Dateien (models, evaluator, manager, dialog, rule_row, __init__),
  100 neue Tests (66 Evaluator + 16 DB + 18 Manager). i18n komplett (EN+DE).
  ────────────────────────────────────────
  Sub-Phase: 5.4 Hybrid AutoCat (Rule Grouping + Templates)
  Fortschritt: ████████████████████ 100%
  Details: Rule Grouping mit verschachtelter Logik: (A AND B) OR (C AND D).
    SmartCollectionRuleGroup (frozen dataclass), Evaluator mit Groups-Priorität,
    12 Templates (Quality/Completion/Time/Platform/Examples), Templates-Menü im Dialog,
    RuleGroupWidget (QGroupBox + RuleRowWidget), Dialog-Umbau auf Gruppen-UI,
    Export/Import v1.1 (Groups + backward-compat v1.0), 54 neue Tests,
    5 neue Dateien, 7 modifizierte. i18n komplett (EN+DE, ~50 Keys).
  ────────────────────────────────────────
  Sub-Phase: 5.5 HLTB Steam Import API
  Fortschritt: ████████████████████ 100%
  Details: Steam Import API (Bulk-Mapping einer gesamten Steam-Bibliothek),
    3-Level-Lookup: ID-Cache → Name-Search → Edition-Fallback,
    fetch_game_by_id() via Next.js Data Route, _discover_build_id(),
    hltb_id_cache DB-Tabelle (Schema v4, 30 Tage TTL),
    Automatischer Prefetch in Enrichment-Pipeline mit Steam-ID-Erkennung,
    Not-Found-Marker (verhindert sinnlose Retries),
    Match-Rate: 75% → 94.8%, 22 neue Tests (73 HLTB-Tests total)

  ---
  Phase 6 — Data & Performance ████████████████████ 100%

  Sub-Phase: 6.1 HLTB Integration
  Fortschritt: ████████████████████ 100%
  Details: Client komplett, AutoCat, DB, UI, Steam Import API (3-Level-Lookup,
    94.8% Match-Rate, Not-Found-Marker, hltb_id_cache mit 30d TTL)
  ────────────────────────────────────────
  Sub-Phase: 6.2 ProtonDB Integration
  Fortschritt: ████████████████████ 100%
  Details: ProtonDBClient (protondb_api.py), ProtonDBResult frozen dataclass,
    ProtonDBEnrichmentThread (BaseEnrichmentThread), DB-Tabelle protondb_ratings
    (Schema v5, 7d TTL), game_detail_service Refactoring (DB-Lookup zuerst),
    Menu wiring, i18n komplett (EN+DE), 15 Tests.
  ────────────────────────────────────────
  Sub-Phase: 6.3 SteamKit2 API Erweiterungen
  Fortschritt: ████████████████████ 100%
  Details: 10 neue API-Endpoints (GetTagList, GetLocalizedNameForTags,
    GetAchievementsProgress, GetDLCForApps, GetMostPopularTags, PrivateApps,
    ClientComm, Wishlist + Stubs). SteamAppDetails erweitert (description,
    short_description, age_ratings, dlc_ids, asset_urls). GetItems Flags
    erweitert (include_release, _ratings, _full_description, _included_items).
    Game dataclass erweitert (description, is_private, dlc_ids, family_sharing).
    Detail-Panel: Description-Section, DLC-Section, Private Badge.
    Language-Parser Bugfix ("English*" → "English"). 36 Tests.
  ────────────────────────────────────────
  Sub-Phase: 6.4 Enrichment Force Refresh + Batch Menu Redesign
  Fortschritt: ████████████████████ 100%
  Details: force_refresh Flag in BaseEnrichmentThread + alle 5 Enrichment-Threads
    (HLTB, Steam API, Deck, Achievements, ProtonDB). Confirm-Dialog via UIHelper,
    get_all_game_ids() DB-Methode.
    Batch Menu Redesign: 5 Force-Refresh-Menueintraege entfernt, show_batch_result()
    Pattern (Completion-Dialog mit "Alle neu einlesen"-Button), EnrichAllCoordinator
    (Tags Phase 0 + 4 parallele Tracks: Steam API→Achievements, HLTB, ProtonDB,
    Deck), EnrichAllProgressDialog (5 Zeilen mit unabhaengigen Fortschrittsbalken),
    neuer Menuepunkt "ALLE Daten NEU einlesen", i18n komplett (EN+DE), 27 Tests.
  ────────────────────────────────────────
  Sub-Phase: 6.5 External Games (Epic/GOG/Amazon/Lutris/itch.io/Bottles/Flatpak)
  Fortschritt: ████████████████████ 100%
  Details: Binary VDF Parser (byte-for-byte roundtrip), ShortcutsManager (CRC32 App-ID,
    CRUD, Backup), 8 Platform Parsers (HeroicEpic/GOG/Amazon, Lutris, Bottles, itch.io,
    Flatpak, ShortcutsVDF), ExternalGamesService Orchestrator (batch-add, progress),
    ExternalGamesDialog (BaseDialog, scan/filter/select/add, per-platform tags),
    DB Schema v7 (external_games Tabelle), Menu-Integration (Ctrl+Shift+E),
    i18n komplett (EN+DE, 23 Keys), 107 neue Tests.
  ────────────────────────────────────────
  Sub-Phase: 6.6 Library Health Check
  Fortschritt: ████████████████████ 100%
  Details: 2-Stufen Store-Verfuegbarkeitscheck (Batch GetItems API + HTTP Detail),
    Gesundheitsbericht-Dialog (BaseDialog, 3 Tabs: Store/Data/Cache),
    DB-Queries (missing_artwork, stale HLTB/ProtonDB), LibraryHealthThread (QThread),
    StoreCheckResult + HealthReport dataclasses, i18n komplett (EN+DE), 17 Tests.
  ────────────────────────────────────────
  Sub-Phase: 6.5.2 ROM Scanner & Emulator Integration
  Fortschritt: ████████████████████ 100%
  Details: RomParser (BaseExternalParser), 16 EmulatorDef-Eintraege (Eden, Citron,
    Ryujinx, Yuzu, Cemu, Azahar, melonDS, Dolphin GC/Wii, RetroArch N64/SNES/NES/GBA/GB,
    PPSSPP, DOSBox), 4-Stufen Emulator-Erkennung (EmuDeck→Flatpak→PATH→AppImage-Glob),
    ROM-Name-Cleanup (Regex: Title-IDs, Versions, Regions), Flatpak-Sentinel-Pfade,
    Emulator-spezifische Launch-Templates (--exec=, -L core, -g),
    Collection-Emoji-System (21 neue Emoji-Keys, get_collection_emoji() lazy lookup),
    Plattform-Emojis im Category-Tree (folgt Smart-Collection-Pattern),
    Saubere Kollektionsnamen ("Nintendo Switch" statt "Emulation (Nintendo Switch)"),
    i18n komplett (EN+DE, 7+21 Keys), 38 neue Tests.
  ────────────────────────────────────────
  Sub-Phase: 6.7 DB Refactoring v8
  Fortschritt: ████████████████████ 100%
  Details: Schema v8 Migration (6 neue Spalten in games: pegi_rating, esrb_rating,
    metacritic_score, steam_deck_status, short_description, content_descriptors;
    8 neue Tabellen: user_game_status, age_ratings, purchase_history, user_tags,
    user_game_tags, user_lists, user_list_items, playtime_snapshots).
    DRY Prep: age_ratings.py zentralisiert (3 Duplikate eliminiert), widget_factory.py
    geloescht (UIHelper.create_progress_dialog ersetzt 5 manuelle Konstruktionen),
    BaseDialog Basisklasse, Theme.STYLE_* Konstanten.
    Database Split: 1876-Zeilen database.py → 10 Module in src/core/db/ (Mixin-Pattern,
    alle <500 Zeilen, 16-Zeilen Facade fuer Backward-Compat).
    ProtonDB batch-load Bugfix (batch_get_protondb existierte, wurde nie aufgerufen).

  ---
  Phase 7 — Polish & Release ████████████████████ 99%

  Sub-Phase: 7.1 UI/UX Polish
  Fortschritt: ████████████████████ 100%
  Details: Inter-Font, FontHelper, Context-Menus, Detail-Panel Refactoring
    (4 Module, alle <500 Zeilen), ImageBrowser Pagination (SteamGridDB
    seitenweise laden, PagedSearchThread, Lazy Loading),
    Detail-Panel erweitert (Description, DLC-Section, Private Badge),
    ImageBrowser Throttling (max 3 animierte Bilder gleichzeitig, 150ms Delay,
    load_finished Signal an 7 Stellen, Queue-System, 7 Tests),
    QR Code Styling (RoundedModuleDrawer, Custom PNG-Logo Overlay mit
    Alpha-Channel, Fallbacks fuer fehlende Datei/Imports, i18n Error-Texte),
    Drag&Drop (Games zwischen Kategorien ziehen, Multi-Select, Signal-Chain,
    persistente Speicherung via CategoryChangeHandler),
    Review-Percentage Bugfix (review_score Kategorie 1-9 wurde als Prozent
    angezeigt → neue DB-Spalte review_percentage, Schema v6 Migration,
    tag_import_service/game_manager/database.py/8 Dateien gefixt),
    Settings-Crash Bugfix (STEAM_PATH str→Path, Sprach-Revert bei Cancel),
    Keyboard-Shortcuts (Ctrl+F/R/S/Q/P, F1/F5/F12, Konami-Code Easter Egg,
    Layered ESC, Del/F2/Space Hotkeys, Switchbros Easter Egg),
    About Dialog (Professionell, QR-Code, Version/Build/System Info),
    Bulk Metadata: Revert-to-Original + Live Name Preview (QListWidget,
    click-to-inspect, orange Modified-Indicator, sort_as Bugfix),
    Smart Collection Builder: i18n Titel (Create/Edit differenziert, DE+EN)
  ────────────────────────────────────────
  Sub-Phase: 7.2 Documentation
  Fortschritt: ████████████████████ 100%
  Details: README dual-language (EN + DE mit Sprachwechsler), CLAUDE.md,
    User Manual (EN+DE, 460+ Zeilen), FAQ (EN+DE, 219 Zeilen),
    Keyboard Shortcuts (EN+DE), Tips & Tricks (EN+DE),
    Help-Menü-Integration (F1 → User Manual, FAQ als 4. Eintrag),
    Screenshots PNG→WebP Migration (34 WebP: 17 EN + 17 DE),
    README-Grafiken dark/light Theme (header/footer/divider),
    Ko-fi + PayPal Donation-Buttons (EN+DE),
    SLM-Fortschritt.md aktuell gehalten.
  ────────────────────────────────────────
  Sub-Phase: 7.3 Packaging
  Fortschritt: ███████████████████░ 95%
  Details: AppImage (build-appimage.sh + CI/CD), AUR (PKGBUILD, live via yay),
    Flatpak (Manifest + Dependencies, lokal getestet mit KDE 6.9, Flathub PR pending),
    GitHub Release (v1.1.1 live mit AppImage + SHA256SUMS),
    Desktop-Integration (auto-register bei AppImage-Start, --uninstall CLI),
    App-ID: io.github.switch_bros.SteamLibraryManager
  ────────────────────────────────────────
  Sub-Phase: 7.4 Testing & Hardening
  Fortschritt: ████████████████████ 100%
  Details: 1589 Tests, 0 Failures, Schema v9, DB Split (10 Module),
    Coverage-Audit (46% gesamt, >70% Core), Mega Refactoring MRP-2 KOMPLETT (T01-T14:
    19 Dateien kondensiert/gesplittet, 9 neue Module, __all__ auf allen Modulen,
    processEvents eliminiert, DRY-Deduplizierung in 8 Modulen).
    Pre-Commit: black + flake8 + mypy enforced.
    Codex Audit Cleanup: 6 fehlende i18n-Keys, pytest-Konfig konsolidiert,
    __all__ in 24 UI-Modulen, BaseDialog konsolidiert, Import-Zyklus verifiziert,
    MagicMock Root Cause gefixt (28 Test-Sites).

  ---
  Phase 8 — Curator Enhancement ████████████████████ 100%

  Sub-Phase: 8.A Foundation (DB + Enrichment)
  Fortschritt: ████████████████████ 100%
  Details: Schema v9 Migration (curators + curator_recommendations Tabellen),
    CuratorMixin (11 Methoden), CuratorPresets (18 verifizierte Popular Curators),
    CuratorEnrichmentThread (BaseEnrichmentThread), EnrichAll Track G, 31 Tests.
  ────────────────────────────────────────
  Sub-Phase: 8.B UI (Management + AutoCat + Filter)
  Fortschritt: ████████████████████ 100%
  Details: CuratorManagementDialog (BaseDialog), AutoCat auf DB-backed umgestellt,
    FilterService Curator-Cache + Filter, dynamisches Curator-Submenu im View-Menu,
    Tools-Menu "Kuratoren verwalten...", 14 neue + 6 rewritten Tests.
  ────────────────────────────────────────
  Sub-Phase: 8.C Polish (Overlap + Export/Import + Discovery)
  Fortschritt: ████████████████████ 100%
  Details: Overlap Score (curator_overlap Feld, Detail-Panel), JSON Export/Import
    (Merge-Logik), Auto-Discovery (Top Curators API, Subscribed Curators),
    16 neue Tests.

  ---
  Zahlen auf einen Blick

  ┌─────────────────────┬───────────────────────────────────────────┐
  │       Metrik        │                   Wert                    │
  ├─────────────────────┼───────────────────────────────────────────┤
  │ Python-Quelldateien │ 186                                       │
  ├─────────────────────┼───────────────────────────────────────────┤
  │ Testdateien         │ 104                                       │
  ├─────────────────────┼───────────────────────────────────────────┤
  │ Tests (passed)      │ 1589                                      │
  ├─────────────────────┼───────────────────────────────────────────┤
  │ DB-Schema           │ v9 (curators + curator_recommendations,   │
  │                     │   11 Module in src/core/db/)              │
  ├─────────────────────┼───────────────────────────────────────────┤
  │ i18n-Sprachen       │ 2 (EN/DE)                                 │
  ├─────────────────────┼───────────────────────────────────────────┤
  │ AutoCat-Typen       │ 17/17                                     │
  ├─────────────────────┼───────────────────────────────────────────┤
  │ API-Integrationen   │ 7+8 (Steam, HLTB, SteamGridDB, Steam Store,│
  │                     │   Steam Curator, ISteamUserStats, ProtonDB │
  │                     │   + Heroic/Lutris/Bottles/itch.io/Flatpak/ │
  │                     │   ROM-Emulation)                           │
  ├─────────────────────┼───────────────────────────────────────────┤
  │ SteamKit2-Endpoints │ 10 (GetItems+, GetTagList, GetLocalized   │
  │                     │   NameForTags, GetAchievementsProgress,   │
  │                     │   GetDLCForApps, GetMostPopularTags,      │
  │                     │   PrivateApps, ClientComm, Wishlist)      │
  ├─────────────────────┼───────────────────────────────────────────┤
  │ Export-Formate      │ 5 (VDF, CSV Simple, CSV Full, JSON,       │
  │                     │   Smart Collections JSON)                 │
  ├─────────────────────┼───────────────────────────────────────────┤
  │ Import-Formate      │ 3 (VDF, DB Backup, Smart Collections JSON)│
  └─────────────────────┴───────────────────────────────────────────┘
