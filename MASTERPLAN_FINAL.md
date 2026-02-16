# 🚀 MASTERPLAN: SteamLibraryManager - Der Beste Steam Library Manager Aller Zeiten

**Status:** Phase 0-4 komplett, Phase 5+ offen
**Ziel:** Depressurizer in ALLEN Bereichen übertreffen + Einzigartige Features
**Platform:** Linux-First, Cross-Platform-Ready
**Letzte Aktualisierung:** 2026-02-16

- Depressurizer v9.3.0.0 (175 C# Files) ✅ Analyzed
- Steam Metadata Editor (Python/Tkinter) ✅ Analyzed
- Stelicas (JavaScript/Electron) ✅ **NEW! Analyzed**
- Database System ✅ **IMPLEMENTED!**
- Menu Redesign ✅ **DESIGNED!**

---

## 📊 AKTUELLER STATUS (2026-02-16)

### ✅ Was funktioniert:

- [x] Favoriten (Steam-kompatibel mit `user-collections.favorite`)
- [x] Versteckt (Steam-kompatibel mit `user-collections.hidden`)
- [x] User-Kollektionen (cloud-storage-namespace-1.json)
- [x] SteamGridDB Integration (Cover, Logos, Icons)
- [x] PyQt6 Modern UI
- [x] Internationalisierung (Deutsch/English via JSON)
- [x] Auto-Kategorisierung (13/15 Typen!)
- [x] UNCATEGORIZED LOGIC FIXED! (Depressurizer-kompatibel!)
- [x] appinfo.vdf WRITER! (dank Pro Chat!)
- [x] **DATABASE SYSTEM IMPLEMENTED!** (40+ tables, <7s startup!)
- [x] **FLATPAK STEAM SUPPORT!** (Auto-detection!)
- [x] **ARTWORK METADATA TRACKING!** (Multi-device ready!)
- [x] **Bootstrap Service** (Phase 3.2 - UI instant, progressive loading!)
- [x] **Menu Redesign** (Steam-like filters, Sort, Statistics!)
- [x] **Batch Steam API** (IStoreBrowseService, 50er-Batches!)
- [x] **Type/Platform/Status/Language Filters** (Full FilterService!)
- [x] **Sortierung** (Name/Playtime/LastPlayed/ReleaseDate!)
- [x] **Statistics Dialog** (4 Tabs: Overview, Genre, Platform, Top 10!)
- [x] **CSV Export** (Simple + Full mit 22 Spalten!)
- [x] **JSON Export** (Strukturiert mit allen Metadaten!)
- [x] **VDF Import** (Collections laden!)
- [x] **DB Backup** (Export + Import im Menu!)
- [x] **Regex-Suche** (Prefix / im Suchfeld!)
- [x] **Backup/Restore** (Timestamped, Auto-Rotation, Safety-Backup!)
- [x] **Profile System** (CRUD, Import/Export, UI-Dialog!)
- [x] **HLTB Integration** (75.4% Match-Rate, 60 Tests!)

### 🎯 Next Up (High Priority):

- [ ] **AutoCat Curator + Group** (2 verbleibende Typen)
- [ ] **shortcuts.vdf Manager** (Non-Steam game icons - Phase 6!)
- [ ] **Artwork Package Export/Import** (Phase 6/7)

### ⌛ Fehlt noch (vs Depressurizer):

- [ ] **2 weitere AutoCat-Typen** (Curator + Group)
- [ ] Random Game Selector
- [ ] Automatic Mode (Hintergrund-Sync)

---

## 🎉 PHASE 1: KRITISCHE FIXES - ✅ COMPLETED!

### 1.1 OHNE KATEGORIE Fix ✅ DONE!

**Status:** ✅ **GEFIXT!** Logic matches Depressurizer exactly!

### 1.2 Game Type Field ✅ DONE!

**Status:** ✅ **IMPLEMENTED!** Type field in Game dataclass.

### 1.3 Performance: Lokale Datenbank ✅ IMPLEMENTED! 🎉

**BEFORE:**

- ❌ **App-Start: 30+ Sekunden** (appinfo.vdf parsing!)
- ❌ **UI freeze mit "(Reagiert nicht)"**
- ❌ **11MB Binary File** jedes Mal komplett parsen!

**AFTER (2026-02-14):**

- ✅ **App-Start: 7 Sekunden** (4.3x faster!)
- ✅ **UI bleibt responsive** (keine Freezes!)
- ✅ **Database mit 40+ Tabellen**
- ✅ **Artwork Metadata Tracking**
- ✅ **Multi-Device Sync Ready**

**Implemented Features:**

```
✅ database_schema.sql (40+ tables!)
   ├── Core: games, game_genres, game_tags
   ├── Artwork: custom_artwork, artwork_naming_rules
   ├── HLTB: hltb_data
   ├── Personal: game_notes, game_custom_meta
   ├── Collections: user_collections, collection_games
   ├── Performance: device_performance
   ├── Mods: installed_mods
   ├── Achievements: achievements, achievement_stats
   ├── Play Tracking: play_sessions, playtime
   └── Advanced: controller_configs, screenshots, wishlist

✅ database.py - Database class with migrations
✅ database_importer.py - Import from appinfo.vdf
✅ steam_assets.py - Enhanced with DB integration
   ├── _save_artwork_metadata() - NEW!
   ├── export_artwork_package() - NEW!
   └── import_artwork_package() - NEW!

✅ config.py - Enhanced with Flatpak support
   ├── installation_type property - NEW!
   ├── grid_folder property - NEW!
   └── Flatpak auto-detection - NEW!
```

**Stats:**

- Database Size: ~18 MB for 3000 games
- Import Time: ~30 seconds (one-time!)
- Startup Time: < 7 seconds (was 30+!)
- UI Responsive: YES! (was frozen!)

**Files:**

- ✅ `src/core/database_schema.sql`
- ✅ `src/core/database.py`
- ✅ `src/core/database_importer.py`
- ✅ `src/core/steam_assets.py` (enhanced!)
- ✅ `src/config.py` (enhanced!)

**Assignee:** Claude Code ✅ DONE!

---

## 🚀 PHASE 2: CLOUD SYNC & AUTH - Existing

(Content unchanged - already implemented)

---

## 🏗️ PHASE 3: ARCHITECTURE & UX

### 3.1 Split Large Classes ⏳ IN PROGRESS

**Status:** Ongoing refactoring by Claude Code

### 3.2 Bootstrap Service ⏳ IN PROGRESS (Claude Code)

**Goal:** UI visible < 1s, data loads progressively

**Current Status:**

- UI appears immediately ✅
- Tree view loads in 7s
- No UI freeze ✅

**With Bootstrap:**

```
0.0s: Window appears ✨
0.5s: Empty tree visible
1.0s: First 100 games appear!
2.0s: Progressive loading...
7.0s: All games loaded
```

**Implementation:**

```python
# src/services/bootstrap_service.py
class BootstrapService:
    async def initialize(self):
        # Step 1: Config (0.1s)
        components["config"] = config
        
        # Step 2: Database (0.2s)
        components["db"] = Database(db_path)
        
        # Step 3: Game Manager (0.5s)
        components["game_manager"] = GameManager(...)
        
        # Step 4: Load Games (progressive!)
        await self._load_games_async(...)
```

**Estimated:** 1-2 days
**Assignee:** Claude Code

---

## 🎨 PHASE 3.5: MENU REDESIGN - 🆕 NEW!

### 3.5.1 Complete Menu Restructure

**Goal:** Steam-inspired menu with better structure and accessibility

**Key Improvements:**

1. **Type Filters** (like Steam!) - Spiele, Soundtracks, Software, etc.
2. **Platform Filters** (Linux-First!) - Linux, Windows, Steam Deck
3. **Status Filters** - Installiert, Versteckt, Mit Spielzeit
4. **Sort Options** - Name, Spielzeit, Zuletzt gespielt, Release-Datum
5. **View Modes** - Liste, Details, Raster
6. **Better Grouping** - Related items in submenus

**New Menu Structure:**

#### **📁 DATEI**

```
Datei
├─ 🔄 Bibliothek aktualisieren       [Strg+R]
├─ 💾 Speichern                      [Strg+S]
├─ ────────────────────────────────
├─ 📤 Exportieren                    →
│  ├─ Kategorien & Kollektionen      🆕 cloudstorage-namespace-1.json!
│  ├─ Spieleliste als CSV (Simple)
│  ├─ Spieleliste als CSV (Full)     🆕 Stelicas-inspired!
│  ├─ Spieleliste als JSON
│  ├─ App-Metadaten (JSON)           🆕 appinfo.vdf → JSON!
│  ├─ Non-Steam Shortcuts            🆕 shortcuts.vdf!
│  └─ Datenbank-Backup               🆕
├─ 📥 Importieren                    →
│  ├─ Kategorien & Kollektionen      🆕 Merge/Overwrite!
│  ├─ Non-Steam Shortcuts            🆕 shortcuts.vdf!
│  ├─ Datenbank-Backup               🆕
│  └─ Artwork-Paket (Multi-Device!)  🆕
├─ ────────────────────────────────
└─ ❌ Beenden                        [Strg+Q]
```

**Changes:**

- ✅ Export/Import as submenus (cleaner!)
- ✅ Database backup export/import
- ✅ Artwork package multi-device sync
- ❌ Removed "Steam-Pfad neu erkennen" (→ Settings)
- ❌ Removed "Benutzer wechseln" (unnecessary)

#### **✏️ BEARBEITEN**

```
Bearbeiten
├─ ✏️ Metadaten bearbeiten           [Strg+M]
│  ├─ Einzelnes Spiel
│  └─ Mehrere Spiele (Bulk Edit)
├─ 🤖 Auto-Kategorisierung           [Strg+K]
├─ ────────────────────────────────
├─ 🏷️ Kollektionen                   →
│  ├─ Neue Kollektion erstellen
│  ├─ Kollektion umbenennen
│  ├─ Kollektionen zusammenführen
│  ├─ Leere Kollektionen löschen
│  └─ Alle auf-/zuklappen            🆕 From Steam!
├─ ────────────────────────────────
├─ 🔍 Spiele mit fehlenden Metadaten
├─ 🔄 Metadaten zurücksetzen
└─ 🗑️ Duplikate entfernen
```

**Changes:**

- ✅ Metadaten-Edit split (Single vs Bulk)
- ✅ Kollektionen submenu (like Steam!)
- ✅ Alle auf-/zuklappen (from Steam context menu!)
- ❌ Removed "Favoriten" (is a collection!)
- ❌ Removed "Cache leeren" (→ Settings)

#### **👁️ ANSICHT** - 🆕 STEAM-INSPIRED!

```
Ansicht
├─ 📊 Ansichtsmodus                  →
│  ├─ ○ Liste (Kompakt)
│  ├─ ● Details (Normal)
│  └─ ○ Raster (Grid)
├─ 🔍 Sortieren nach                 →
│  ├─ ● Name (A-Z)
│  ├─ ○ Spielzeit
│  ├─ ○ Zuletzt gespielt             🆕 From Steam!
│  ├─ ○ Hinzugefügt am
│  └─ ○ Release-Datum
├─ ────────────────────────────────
├─ 🎮 Typ anzeigen                   → 🆕 LIKE STEAM!
│  ├─ ✓ Spiele (3032)                
│  ├─ ✓ Soundtracks (47)
│  ├─ ✓ Software (19)
│  ├─ ✓ Videos (1)
│  ├─ ✓ DLCs (152)
│  └─ ✓ Tools (192)
├─ 💻 Plattform                      → 🆕 LINUX-FIRST!
│  ├─ ✓ Linux
│  ├─ ✓ Windows
│  ├─ ✓ macOS
│  └─ ✓ Steam Deck
├─ 📦 Status                         → 🆕 LIKE STEAM!
│  ├─ ✓ Installiert
│  ├─ ✓ Nicht installiert
│  ├─ ✓ Versteckt
│  ├─ ✓ Mit Spielzeit
│  └─ ✓ Favoriten
├─ ────────────────────────────────
├─ 📊 Statistiken anzeigen           →
│  ├─ Gesamtübersicht
│  ├─ Nach Genre
│  ├─ Nach Plattform                 🆕
│  └─ Top 10 meist gespielt
├─ ────────────────────────────────
└─ 🎨 Theme                          →
   ├─ ● System
   ├─ ○ Hell
   └─ ○ Dunkel
```

**KEY NEW FEATURES:**

- ✅ **Typ anzeigen** - Exactly like Steam! (with counts!)
- ✅ **Plattform** - Linux/Windows/macOS/Deck filters
- ✅ **Status** - Installiert, Versteckt, Mit Spielzeit
- ✅ **Sortieren nach** - Multiple sort options
- ✅ **Nach Plattform** stats

#### **🛠️ WERKZEUGE**

```
Werkzeuge
├─ 🎨 Artwork                        → 🆕 ENHANCED!
│  ├─ Cover herunterladen (Alle)
│  ├─ Logos herunterladen (Alle)
│  ├─ Heroes herunterladen (Alle)
│  ├─ ────
│  ├─ Benutzerdefinierte Bilder
│  ├─ ────
│  ├─ Artwork-Paket exportieren      🆕 Multi-Device!
│  └─ Artwork-Paket importieren      🆕 Multi-Device!
├─ ────────────────────────────────
├─ 🔍 Erweiterte Suche               →
│  ├─ Nach Publisher
│  ├─ Nach Developer
│  ├─ Nach Genre
│  ├─ Nach Tags
│  └─ Nach Release-Jahr
├─ ────────────────────────────────
├─ 📦 Batch-Operationen              →
│  ├─ Metadaten aktualisieren (Alle) 🆕 Batch API!
│  ├─ ProtonDB Ratings aktualisieren
│  ├─ Store-Seiten prüfen
│  └─ Achievements aktualisieren
├─ ────────────────────────────────
├─ 🗄️ Datenbank                     → 🆕 NEW!
│  ├─ Datenbank optimieren
│  ├─ Datenbank neu erstellen
│  ├─ Import von appinfo.vdf
│  └─ Backup erstellen
├─ ────────────────────────────────
└─ ⚙️ Einstellungen                 [Strg+P]
```

**Changes:**

- ✅ Artwork submenu (multi-device export/import!)
- ✅ Database Tools (NEW section!)
- ✅ Batch Operations (with Batch API!)
- ✅ Settings shortcut: Strg+P (like VS Code!)
- ❌ Removed "Steam starten" etc. (Steam must be closed!)

#### **❓ HILFE**

```
Hilfe
├─ 📖 Dokumentation                  [F1]
│  ├─ Benutzerhandbuch
│  ├─ Tipps & Tricks
│  └─ Keyboard Shortcuts
├─ ────────────────────────────────
├─ 🌐 Online                         →
│  ├─ GitHub Repository
│  ├─ Issues melden
│  ├─ Discussions
│  └─ Wiki
├─ ────────────────────────────────
├─ 🔄 Updates                        →
│  ├─ Auf Updates prüfen
│  └─ Changelog anzeigen
├─ ────────────────────────────────
├─ 💰 Unterstützen                   →
│  ├─ PayPal
│  ├─ GitHub Sponsors
│  └─ Ko-fi
├─ ────────────────────────────────
└─ ℹ️ Über SLM                       [F12]
   ├─ Version & Build
   ├─ Credits (inkl. SwitchBros!)   🆕
   └─ Lizenzen
```

**Implementation:**

```
Files:
- src/ui/builders/menu_builder.py (replace!)
- src/ui/handlers/filter_handler.py (NEW!)
- src/ui/handlers/sort_handler.py (NEW!)
- src/ui/dialogs/statistics_dialog.py (NEW!)
- src/config.py (add filter/sort state)

i18n Keys:
- resources/i18n/en/main.json
- resources/i18n/de/main.json
- resources/i18n/logs.json

Estimated: 3-4 days
Priority: HIGH
```

---

## 📤 PHASE 3.6: ENHANCED EXPORT - 🆕 STELICAS-INSPIRED!

### 3.6.1 Batch Steam API Integration

**Inspiration:** Stelicas (JavaScript/Electron app) shows the way!

**Current Problem:**

```python
# Slow approach (if we fetch metadata):
for game in games:  # 3000 iterations!
    data = fetch_single_game(game.app_id)  # 1 API call each
    # Total: 3000 API calls = HOURS! 😱
```

**Stelicas Solution:**

```javascript
// Batch approach:
const BATCH_SIZE = 200;
const url = 'IStoreBrowseService/GetItems/v1';

// 200 games in ONE request!
for batch in chunks(games, 200):  # 15 iterations!
    data = fetch_batch(batch.app_ids)  # 1 API call per 200 games
    # Total: 15 API calls = MINUTES! 🚀

// 200x FASTER!
```

**Implementation:**

```python
# src/services/steam_api_batch.py (NEW!)

class SteamApiBatch:
    """Batch Steam API requests using GetItems endpoint.
    
    Inspired by Stelicas - fetches 200 games per request!
    """
    
    BATCH_SIZE = 200
    CONCURRENT_REQUESTS = 10
    DELAY_BETWEEN_BATCHES = 1.0  # Rate limiting
    
    async def fetch_games_batch(
        self,
        app_ids: list[int],
        language: str = "german",
        country_code: str = "DE"
    ) -> list[dict]:
        """
        Fetch comprehensive game details for up to 200 games.
        
        Uses: IStoreBrowseService/GetItems/v1
        
        Returns metadata including:
        - Basic info (name, type, release_date)
        - Reviews (percentage, count)
        - Tags
        - Publishers, Developers
        - Franchises (!)
        - is_free, is_early_access (!)
        - Supported languages
        - Platforms
        - And more!
        
        Args:
            app_ids: List of up to 200 Steam app IDs
            language: Language code (german, english, etc.)
            country_code: Country code (DE, US, etc.)
            
        Returns:
            List of game detail dicts
        """
        url = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1"
        
        request_data = {
            "ids": [{"appid": app_id} for app_id in app_ids],
            "context": {
                "language": language,
                "country_code": country_code,
                "steam_realm": 1
            },
            "data_request": {
                "include_assets": True,
                "include_release": True,
                "include_platforms": True,
                "include_all_purchase_options": True,
                "include_screenshots": True,
                "include_trailers": True,
                "include_ratings": True,
                "include_tag_count": True,
                "include_reviews": True,
                "include_basic_info": True,
                "include_supported_languages": True,
                "include_full_description": True,
                "include_included_items": True,
            }
        }
        
        response = await self._make_request(url, request_data)
        return response.get("store_items", [])
    
    async def fetch_all_games(
        self,
        app_ids: list[int],
        progress_callback: Callable[[int, int, str], None] | None = None
    ) -> list[dict]:
        """
        Fetch all games in batches with progress tracking.
        
        Args:
            app_ids: All app IDs to fetch
            progress_callback: Function(current, total, message)
            
        Returns:
            Complete list of game details
        """
        all_data = []
        chunks = [app_ids[i:i+self.BATCH_SIZE] 
                  for i in range(0, len(app_ids), self.BATCH_SIZE)]
        
        total_batches = len(chunks)
        
        for i, chunk in enumerate(chunks):
            # Fetch batch
            batch_data = await self.fetch_games_batch(chunk)
            all_data.extend(batch_data)
            
            # Progress callback
            if progress_callback:
                progress_callback(
                    i + 1,
                    total_batches,
                    f"Fetching metadata ({i+1}/{total_batches} batches)..."
                )
            
            # Rate limiting
            if i + 1 < total_batches:
                await asyncio.sleep(self.DELAY_BETWEEN_BATCHES)
        
        return all_data
```

**Impact:**

- ✅ **200x faster!** (15 requests vs 3000!)
- ✅ **Rich metadata!** (franchises, is_free, reviews!)
- ✅ **Better database!** (fill all fields!)
- ✅ **Better export!** (17+ CSV columns!)

**Estimated:** 2-3 days
**Priority:** HIGH

---

### 3.6.2 Enhanced CSV Export (Stelicas-Style!)

**Current Export:** None (only VDF save)

**Stelicas Export:** 2 CSV files with 17+ columns!

**Implementation:**

```python
# src/services/export_service.py (NEW!)

class ExportService:
    """Export games with rich metadata (Stelicas-inspired)."""
    
    def __init__(self, db: Database, steam_api: SteamApiBatch):
        self.db = db
        self.steam_api = steam_api
    
    async def export_csv_full(
        self,
        games: list[Game],
        output_path: Path,
        progress_callback: Callable | None = None
    ) -> None:
        """
        Export games to CSV with rich metadata (17+ columns).
        
        Columns (Stelicas-inspired):
        - game_id, name, categories
        - type, tags, release_date
        - review_percentage, review_count
        - is_free, is_early_access
        - publishers, developers, franchises
        - short_description
        - supported_languages
        - steam_link, header_image
        - playtime, last_played (from DB!)
        
        Args:
            games: Games to export
            output_path: Output CSV file path
            progress_callback: Progress updates
        """
        # Phase 1: Fetch metadata via Batch API
        app_ids = [int(g.app_id) for g in games]
        metadata = await self.steam_api.fetch_all_games(
            app_ids,
            progress_callback=self._batch_progress_wrapper(progress_callback)
        )
        
        # Phase 2: Merge with database data
        enriched_data = self._merge_data(games, metadata)
        
        # Phase 3: Write CSV
        self._write_csv(enriched_data, output_path)
    
    def export_csv_simple(
        self,
        games: list[Game],
        output_path: Path
    ) -> None:
        """
        Export simple CSV (3 columns).
        
        Columns:
        - game_id, name, categories
        """
        data = [
            {
                "game_id": g.app_id,
                "name": g.name,
                "categories": ";".join(g.categories)
            }
            for g in games
        ]
        
        self._write_csv(data, output_path)
    
    def export_json(
        self,
        games: list[Game],
        output_path: Path
    ) -> None:
        """Export as structured JSON."""
        data = [g.to_dict() for g in games]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
```

**Export Dialog UI:**

```python
# src/ui/dialogs/export_dialog.py (NEW!)

class ExportDialog(QDialog):
    """Export dialog with format selection and progress."""
    
    def __init__(self, game_manager, db, parent=None):
        super().__init__(parent)
        self.game_manager = game_manager
        self.db = db
        
        # Checkboxes
        self.csv_simple_cb = QCheckBox(t("ui.export.csv_simple"))
        self.csv_full_cb = QCheckBox(t("ui.export.csv_full"))
        self.json_cb = QCheckBox(t("ui.export.json"))
        self.db_backup_cb = QCheckBox(t("ui.export.db_backup"))
        self.artwork_cb = QCheckBox(t("ui.export.artwork"))
        
        # Options
        self.include_hidden_cb = QCheckBox(t("ui.export.include_hidden"))
        self.include_dlc_cb = QCheckBox(t("ui.export.include_dlc"))
        self.fetch_metadata_cb = QCheckBox(t("ui.export.fetch_metadata"))
        
        # Progress
        self.progress_bar = QProgressBar()
        self.status_label = QLabel("")
        
        # Buttons
        self.export_btn = QPushButton(t("ui.export.start"))
        self.export_btn.clicked.connect(self.start_export)
    
    async def start_export(self):
        """Start export with progress tracking."""
        output_dir = self.select_output_folder()
        if not output_dir:
            return
        
        # Get games
        games = self.game_manager.get_all_games()
        
        # Export selected formats
        if self.csv_simple_cb.isChecked():
            self.update_progress(10, "Exporting simple CSV...")
            await self.export_service.export_csv_simple(
                games,
                output_dir / "games_simple.csv"
            )
        
        if self.csv_full_cb.isChecked():
            self.update_progress(30, "Fetching metadata...")
            await self.export_service.export_csv_full(
                games,
                output_dir / "games_full.csv",
                progress_callback=self.update_progress
            )
        
        if self.json_cb.isChecked():
            self.update_progress(80, "Exporting JSON...")
            await self.export_service.export_json(
                games,
                output_dir / "games.json"
            )
        
        if self.db_backup_cb.isChecked():
            self.update_progress(90, "Creating database backup...")
            shutil.copy(self.db.db_path, output_dir / "metadata_backup.db")
        
        if self.artwork_cb.isChecked():
            self.update_progress(95, "Exporting artwork...")
            from src.core.steam_assets import SteamAssets
            SteamAssets.export_artwork_package(self.db, output_dir)
        
        self.update_progress(100, "Export complete!")
        QMessageBox.information(
            self,
            t("ui.export.complete"),
            t("ui.export.complete_message", path=output_dir)
        )
```

**CSV Format Comparison:**

**Simple CSV:**

```csv
game_id,name,categories
620,Portal 2,"Puzzle;FPS"
440,Team Fortress 2,"Shooter;Multiplayer"
```

**Full CSV (Stelicas-style!):**

```csv
game_id,name,categories,type,tags,release_date,review_percentage,review_count,is_free,is_early_access,publishers,developers,franchises,short_description,supported_languages,steam_link,header_image,playtime,last_played
620,Portal 2,"Puzzle;FPS",game,"Puzzle,First-Person,Comedy",2011-04-18,95,125000,false,false,Valve,Valve,Portal,"Portal 2 draws from...",german,https://steamcommunity.com/app/620,https://.../header.jpg,245,2026-02-10
440,Team Fortress 2,"Shooter;Multiplayer",game,"Shooter,Multiplayer,Free",2007-10-10,92,500000,true,false,Valve,Valve,Team Fortress,"Team Fortress 2...",german,https://steamcommunity.com/app/440,https://.../header.jpg,1523,2026-02-13
```

**Files:**

- `src/services/steam_api_batch.py` (NEW!)
- `src/services/export_service.py` (NEW!)
- `src/ui/dialogs/export_dialog.py` (NEW!)
- i18n keys in `resources/i18n/`

**Estimated:** 3-4 days
**Priority:** HIGH
**Dependencies:** Batch Steam API

---

### 3.6.3 Smart Import/Export Hub - 🆕 REDESIGNED!

**Status:** 🔥 **REDESIGNED!** (2026-02-16)

**Alter Plan:** Generischer "Text VDF Export" als Debug-Tool (~50 Zeilen).
**Neuer Plan:** Fokussierter Import/Export der drei wichtigsten Steam-Dateien!

**Erkenntnis:** Ein generischer VDF-Text-Dump ist ein nettes Debug-Tool, aber kein echtes Feature das Nutzer brauchen.
Die WIRKLICH wichtigen Dateien sind:

| Datei                           | Richtung               | Priorität | Nutzen                                                    |
|---------------------------------|------------------------|-----------|-----------------------------------------------------------|
| `cloudstorage-namespace-1.json` | Export + Import        | **HOCH**  | Kategorien/Kollektionen sichern, teilen, wiederherstellen |
| `appinfo.vdf`                   | Nur Export (Read-only) | MITTEL    | Steam-Metadaten als JSON für Debugging/Analyse            |
| `shortcuts.vdf`                 | Export + Import        | **HOCH**  | Non-Steam Games zwischen Rechnern übertragen              |

---

#### **1. cloudstorage-namespace-1.json (Kategorien/Kollektionen)**

**Das Kernfeature!** Diese Datei ist die Source-of-Truth für alle Steam-Kategorien und Kollektionen. Export/Import
ermöglicht:

- **Backup:** Kategorien vor riskanten Operationen sichern
- **Teilen:** Setups mit anderen Nutzern teilen (z.B. "Mein perfektes Genre-Setup")
- **Wiederherstellen:** Nach Steam-Reset alles zurückholen
- **Profil-Ergänzung:** Das bestehende Profil-System speichert Filter-States — der Cloud-Export sichert die Kategorien
  selbst

**Implementation:**

```python
# src/utils/collection_exporter.py

class CollectionExporter:
    """Export/Import Steam collections from cloudstorage-namespace-1.json."""

    def export_collections(self, cloud_storage_path: Path, output_path: Path) -> None:
        """Export collections as human-readable JSON.

        Args:
            cloud_storage_path: Path to cloudstorage-namespace-1.json.
            output_path: Destination path for export file.
        """
        # Read + parse + export as clean, formatted JSON
        # Include: collection names, game IDs, dynamic collection rules

    def import_collections(
        self,
        import_path: Path,
        cloud_storage_path: Path,
        mode: str = "merge"  # "merge" or "overwrite"
    ) -> ImportResult:
        """Import collections back into cloud storage.

        Args:
            import_path: Path to exported JSON file.
            cloud_storage_path: Path to cloudstorage-namespace-1.json.
            mode: "merge" (add new, keep existing) or "overwrite" (replace all).

        Returns:
            ImportResult with counts of added/updated/skipped collections.
        """
```

**Import-Modi:**

```
Merge (Default):
├─ Neue Kollektionen → hinzufügen
├─ Existierende → beibehalten (kein Überschreiben)
└─ Konflikte → User fragen (Dialog)

Overwrite:
├─ Backup erstellen (automatisch!)
├─ Alle Kollektionen ersetzen
└─ Warnung vorher anzeigen
```

---

#### **2. appinfo.vdf (Steam-Metadaten)**

**Read-only Export!** Steam verwaltet diese Datei — wir lesen nur. Export als JSON für:

- **Debugging:** Was weiß Steam über ein bestimmtes Spiel?
- **Analyse:** Alle Spiel-Metadaten auf einen Blick
- **Vergleich:** Vor/nach DB-Import prüfen

**Implementation:**

```python
# In src/ui/actions/file_actions.py

def export_appinfo_json(self) -> None:
    """Export appinfo.vdf data as human-readable JSON."""
    # QFileDialog → Ziel wählen
    # appinfo_manager.parse() → JSON dump
    # Alle Felder: name, type, developer, publisher, tags, genres, etc.
```

**Kein Import nötig!** Steam pflegt appinfo.vdf selbst. Wir überschreiben sie nicht.

---

#### **3. shortcuts.vdf (Non-Steam Games)**

**Killer-Feature!** Export + Import von Non-Steam Games:

- **Multi-PC:** Gleiche Non-Steam Games auf mehreren Rechnern
- **Backup:** Vor Steam-Neuinstallation sichern
- **Teilen:** "Mein Emulator-Setup" mit Freunden teilen
- **Depressurizer hat das NICHT!**

**Implementation:**

```python
# In src/core/shortcuts_manager.py (erweitert Phase 3.7)

def export_shortcuts(self, output_path: Path) -> int:
    """Export all Non-Steam shortcuts as JSON.

    Args:
        output_path: Destination path for export file.

    Returns:
        Number of exported shortcuts.
    """
    # shortcuts.vdf → parse → JSON mit:
    # name, exe, start_dir, icon, launch_options, tags

def import_shortcuts(self, import_path: Path, mode: str = "merge") -> ImportResult:
    """Import Non-Steam shortcuts from JSON.

    Args:
        import_path: Path to exported JSON file.
        mode: "merge" (add new) or "overwrite" (replace all).

    Returns:
        ImportResult with counts of added/skipped shortcuts.
    """
    # JSON → parse → shortcuts.vdf write
    # Duplikat-Erkennung via app_name + exe
```

---

#### **UI: Import/Export Dialog**

```python
# src/ui/dialogs/import_export_dialog.py

class ImportExportDialog(QDialog):
    """Smart Import/Export Hub with tabbed interface."""

    # Tab 1: Kategorien (cloudstorage-namespace-1.json)
    #   Export: [Exportieren] → QFileDialog
    #   Import: [Importieren] → Merge/Overwrite Radio + QFileDialog
    #   Preview: Zeige Kollektionen im Export/Import

    # Tab 2: Non-Steam Shortcuts (shortcuts.vdf)
    #   Export: [Exportieren] → QFileDialog
    #   Import: [Importieren] → Merge/Overwrite + Preview

    # Tab 3: Metadaten (appinfo.vdf)
    #   Export only: [Als JSON exportieren] → QFileDialog

    # Tab 4: Datenbank
    #   Export: DB-Backup erstellen
    #   Import: DB-Backup wiederherstellen
```

---

#### **i18n-Keys**

```json
"import_export": {
  "dialog_title": "Import / Export",
  "tab_collections": "Categories & Collections",
  "tab_shortcuts": "Non-Steam Shortcuts",
  "tab_metadata": "App Metadata",
  "tab_database": "Database",
  "export_btn": "Export",
  "import_btn": "Import",
  "mode_merge": "Merge (keep existing)",
  "mode_overwrite": "Overwrite (replace all)",
  "overwrite_warning": "This will replace all existing data. A backup will be created automatically.",
  "export_success": "{count} items exported to {path}.",
  "import_success": "{added} added, {skipped} skipped, {updated} updated.",
  "import_conflict": "Collection '{name}' already exists. Overwrite?",
  "no_data": "No data found to export.",
  "backup_created": "Automatic backup created: {path}"
}
```

---

#### **Dateien:**

```
Neue Dateien:
├─ src/utils/collection_exporter.py          (Cloud-Storage Export/Import)
├─ src/ui/dialogs/import_export_dialog.py    (Smart Import/Export Hub UI)
├─ tests/unit/test_utils/test_collection_exporter.py

Geänderte Dateien:
├─ src/core/shortcuts_manager.py             (+export/import Methoden)
├─ src/ui/actions/file_actions.py            (+export_appinfo_json)
├─ src/ui/builders/menu_builder.py           (Menu-Connects)
├─ resources/i18n/en/main.json               (+import_export Block)
├─ resources/i18n/de/main.json               (+import_export Block)
```

#### **Tests:**

- `test_export_collections_creates_valid_json`
- `test_import_collections_merge_mode`
- `test_import_collections_overwrite_creates_backup`
- `test_export_shortcuts_round_trip`
- `test_import_shortcuts_detects_duplicates`
- `test_export_appinfo_as_json`

**Estimated:** 3-4 days
**Priority:** HIGH
**Dependencies:** Phase 3.7 (shortcuts.vdf Manager), Cloud-Storage Parser (Phase 2)

---

## 🎮 PHASE 3.7: NON-STEAM GAMES - 🆕 SHORTCUTS.VDF MANAGER

**Goal:** Automatically set icons for Non-Steam games from Database

**Problem NOW:**

```
User adds custom game → Steam creates entry in shortcuts.vdf
User downloads icon via SteamGridDB → Icon in grid folder ✅
BUT: Icon path not set in shortcuts.vdf! ❌
User must manually set in Steam UI! 😡
```

**Solution:**

```
SLM reads shortcuts.vdf
SLM updates icon path for Non-Steam games
SLM writes shortcuts.vdf back
Steam shows icons automatically! ✅
```

**Implementation:**

```python
# src/core/shortcuts_manager.py (NEW!)

from pathlib import Path
from dataclasses import dataclass

@dataclass
class Shortcut:
    """Non-Steam game shortcut."""
    app_id: int           # Calculated (>= 2147483648)
    app_name: str
    exe: str
    start_dir: str = ""
    icon: str = ""        # ← This we update!
    shortcut_path: str = ""
    launch_options: str = ""
    is_hidden: bool = False
    allow_desktop_config: bool = True
    allow_overlay: bool = True
    tags: list[str] = field(default_factory=list)

class ShortcutsManager:
    """Manages Steam shortcuts (Non-Steam Games)."""
    
    def __init__(self, steam_path: Path, steam_user_id: str):
        self.steam_path = steam_path
        self.user_id = steam_user_id
        self.shortcuts_path = (
            steam_path / "userdata" / user_id / "config" / "shortcuts.vdf"
        )
    
    def read_shortcuts(self) -> list[Shortcut]:
        """Read shortcuts from shortcuts.vdf."""
        # Binary VDF parsing (similar to appinfo.py)
        with open(self.shortcuts_path, "rb") as f:
            data = self._parse_binary_vdf(f)
        
        shortcuts = []
        for key, value in data.get("shortcuts", {}).items():
            shortcuts.append(Shortcut(
                app_id=self._calculate_app_id(value),
                app_name=value.get("appname", ""),
                exe=value.get("exe", ""),
                icon=value.get("icon", ""),
                # ... parse all fields
            ))
        
        return shortcuts
    
    def write_shortcuts(self, shortcuts: list[Shortcut]) -> None:
        """Write shortcuts back to shortcuts.vdf."""
        # Binary VDF writing
        data = {"shortcuts": {}}
        for i, shortcut in enumerate(shortcuts):
            data["shortcuts"][str(i)] = {
                "appid": shortcut.app_id,
                "appname": shortcut.app_name,
                "exe": shortcut.exe,
                "icon": shortcut.icon,  # ← Updated!
                # ... all fields
            }
        
        with open(self.shortcuts_path, "wb") as f:
            self._write_binary_vdf(f, data)
    
    def update_icon_from_grid(self, app_id: int) -> bool:
        """
        Update shortcut icon path from grid folder.
        
        Args:
            app_id: Non-Steam game app ID
            
        Returns:
            True if icon was found and updated
        """
        # Read shortcuts
        shortcuts = self.read_shortcuts()
        
        # Find shortcut
        shortcut = next((s for s in shortcuts if s.app_id == app_id), None)
        if not shortcut:
            return False
        
        # Check if icon exists in grid folder
        grid_folder = SteamAssets.get_steam_grid_path()
        icon_path = grid_folder / f"{app_id}_icon.png"
        
        if not icon_path.exists():
            return False
        
        # Update icon path
        shortcut.icon = str(icon_path)
        
        # Write back
        self.write_shortcuts(shortcuts)
        
        return True
    
    def batch_update_icons(self) -> int:
        """
        Update all Non-Steam game icons from grid folder.
        
        Returns:
            Number of icons updated
        """
        shortcuts = self.read_shortcuts()
        grid_folder = SteamAssets.get_steam_grid_path()
        updated = 0
        
        for shortcut in shortcuts:
            icon_path = grid_folder / f"{shortcut.app_id}_icon.png"
            if icon_path.exists() and shortcut.icon != str(icon_path):
                shortcut.icon = str(icon_path)
                updated += 1
        
        if updated > 0:
            self.write_shortcuts(shortcuts)
        
        return updated
```

**Integration with Menu:**

```
Werkzeuge → Artwork
├─ ...
├─ ────
├─ Non-Steam Games Icons          🆕
│  ├─ Icons automatisch setzen    🆕
│  └─ Icon für ausgewähltes Spiel 🆕
```

**Concept Document:** See `/mnt/project/__shortcuts_manager_py_Konzept.md`

**Files:**

- `src/core/shortcuts_manager.py` (NEW!)
- Tests in `tests/test_shortcuts_manager.py`

**Estimated:** 2-3 days
**Priority:** MEDIUM (nice-to-have, not critical)
**Dependencies:** Binary VDF parser (can reuse from appinfo.py!)

---

## 🎯 PHASE 4: DEPRESSURIZER PARITY

(Content mostly unchanged, but updated priorities)

### 4.1 AutoCat Types - 12 ADDITIONAL TYPES

**Current:** 3 types (Genre, Tags, Year)
**Target:** 15 types (Depressurizer parity)

**Missing Types:**

1. Flags (achievements, trading cards, workshop, etc.)
2. UserScore (review percentage ranges)
3. HLTB (HowLongToBeat playtime brackets)
4. DevPub (Developer/Publisher)
5. Name (alphabetical grouping)
6. VR (VR support levels)
7. Language (supported languages)
8. Curator (Steam Curator recommendations)
9. Platform (Linux/Windows/macOS)
10. HoursPlayed (playtime brackets)
11. Manual (user-defined rules)
12. Group (combine multiple AutoCats)

**NEW PRIORITY:** After Batch API + Enhanced Export!

**Why:** Batch API gives us all the metadata we need for these!

**Files:**

- `src/services/autocategorize/autocat_flags.py`
- `src/services/autocategorize/autocat_userscore.py`
- `src/services/autocategorize/autocat_hltb.py`
- ... (one file per type)

**Estimated:** 8-10 days (all 12 types)
**Priority:** HIGH (Depressurizer parity!)

---

### 4.2 Advanced Filter (Allow/Require/Exclude)

**Depressurizer has:**

```
Filter Builder:
├─ Allow: Tags that are OK
├─ Require: Tags that MUST be present
├─ Exclude: Tags that MUST NOT be present
└─ Presets: Save filter combinations
```

**Implementation:**

```python
# src/services/filter_service.py

class AdvancedFilter:
    allow_tags: set[str] = set()
    require_tags: set[str] = set()
    exclude_tags: set[str] = set()
    
    def matches(self, game: Game) -> bool:
        # Exclude check (highest priority)
        if any(tag in game.tags for tag in self.exclude_tags):
            return False
        
        # Require check
        if self.require_tags and not all(
            tag in game.tags for tag in self.require_tags
        ):
            return False
        
        # Allow check (if no require tags)
        if not self.require_tags and self.allow_tags:
            if not any(tag in game.tags for tag in self.allow_tags):
                return False
        
        return True
```

**Files:**

- `src/services/filter_service.py`
- `src/ui/dialogs/advanced_filter_dialog.py`

**Estimated:** 3-4 days
**Priority:** MEDIUM

---

### 4.3 Backup & Restore with Auto-Rotate

**Depressurizer:** Automatic backups before every write, max 10 backups

**Implementation:**

```python
# src/core/backup_manager.py

class BackupManager:
    def create_backup(self, reason: str = "manual") -> Path:
        """Create timestamped backup."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"backup_{timestamp}_{reason}.zip"
        
        # Backup files:
        # - cloud-storage-namespace-1.json
        # - localconfig.vdf (categories)
        # - metadata.db (our database!)
        # - Custom artwork (optional)
        
        with zipfile.ZipFile(backup_path, "w") as zf:
            zf.write(cloud_storage_file, "cloud-storage.json")
            zf.write(localconfig_file, "localconfig.vdf")
            zf.write(db_file, "metadata.db")
        
        # Rotate old backups
        self.rotate_backups()
        
        return backup_path
    
    def rotate_backups(self, max_backups: int = 10) -> None:
        """Delete oldest backups if > max_backups."""
        backups = sorted(self.backup_dir.glob("backup_*.zip"))
        while len(backups) > max_backups:
            oldest = backups.pop(0)
            oldest.unlink()
```

**Files:**

- `src/core/backup_manager.py`
- `src/ui/dialogs/backup_dialog.py`

**Estimated:** 2 days
**Priority:** MEDIUM

---

### 4.4 Profile System

**Depressurizer:** Save/load different categorization profiles

**Use Case:**

```
Profile "Main": My personal categories
Profile "Family": Kid-friendly categories
Profile "Streaming": Viewer-requested categories
```

**Implementation:**

```python
# src/core/profile_manager.py

@dataclass
class Profile:
    name: str
    description: str
    created_at: datetime
    categories: dict[str, list[str]]  # game_id -> categories
    autocat_rules: list[dict]
    filters: dict

class ProfileManager:
    def save_profile(self, name: str) -> None:
        """Save current state as profile."""
        
    def load_profile(self, name: str) -> None:
        """Load profile and apply categories."""
        
    def export_profile(self, name: str, path: Path) -> None:
        """Export profile as JSON."""
        
    def import_profile(self, path: Path) -> None:
        """Import profile from JSON."""
```

**Files:**

- `src/core/profile_manager.py`
- `src/ui/dialogs/profile_dialog.py`

**Estimated:** 3 days
**Priority:** MEDIUM

---

## 🌟 PHASE 5: UNIQUE FEATURES (BETTER THAN DEPRESSURIZER!)

### 5.1 Steam Deck Optimizer 🎮

**Goal:** Optimize library for Steam Deck

**Features:**

- Filter by Deck Verified / Playable / Unsupported
- ProtonDB ratings integration
- Controller support detection
- Resolution/Performance recommendations
- Create "Deck-Ready" collection

**Implementation:**

```python
# src/services/steamdeck_optimizer.py

class SteamDeckOptimizer:
    def get_deck_status(self, app_id: int) -> str:
        """
        Get Deck compatibility status.
        
        Returns: "verified", "playable", "unsupported", "unknown"
        """
        # Fetch from Steam API or cache
        
    def create_deck_collection(self) -> None:
        """Create 'Deck Verified' collection."""
        verified_games = [
            g for g in self.games
            if self.get_deck_status(g.app_id) == "verified"
        ]
        self.create_collection("Deck Verified", verified_games)
```

**Files:**

- `src/services/steamdeck_optimizer.py`
- `src/ui/dialogs/deck_optimizer_dialog.py`

**Estimated:** 4-5 days
**Priority:** HIGH (unique selling point!)

---

### 5.2 Achievement Hunter Mode 🏆

**Goal:** Track achievement progress, highlight 75-99% completion games

**Features:**

- Show achievement completion percentage
- "Almost Perfect" filter (75-99%)
- Achievement difficulty ratings
- Time to platinum estimates

**Database Support:** ✅ Already implemented!

```sql
CREATE TABLE achievements (
    app_id INTEGER,
    achievement_id TEXT,
    name TEXT,
    description TEXT,
    unlocked BOOLEAN,
    unlock_time INTEGER,
    rarity REAL,
    PRIMARY KEY (app_id, achievement_id)
);

CREATE VIEW v_achievement_hunting AS
SELECT * FROM games 
WHERE achievement_completion BETWEEN 75 AND 99;
```

**Files:**

- `src/services/achievement_service.py`
- `src/ui/dialogs/achievement_dialog.py`

**Estimated:** 3-4 days
**Priority:** MEDIUM

---

### 5.3 Smart Collections System 🧠 - COMPLETE REDESIGN!

**Status:** 🔥 **CRITICAL FEATURE - HIGH PRIORITY!**

**Problem:** Valve's dynamic collections only support AND logic, not OR!  
**Solution:** App-internal "Smart Collections" with full boolean logic + REGEX  
**User Benefit:** Create collections like "LEGO OR Kampf" instead of just "LEGO AND Kampf"

**Complete Design:** See `SMART_COLLECTIONS_COMPLETE_DESIGN.md` (100+ pages!)

---

#### **Current Problem with Valve's System:**

```
Valve Dynamic Collections:
├─ User selects: Tag "LEGO" + Tag "Kampf"
├─ Logic: LEGO AND Kampf (hardcoded!)
├─ Result: Only games with BOTH tags ❌
└─ User gets 1 game instead of 27! 😡

SLM Current Behavior:
├─ Reads dynamic collection from Steam
├─ Shows ⚡ emoji: "LEGO ⚡ (27)"
├─ But only displays FIRST game! ❌
└─ filterSpec rules NOT evaluated!

User Complaint (Steam Forums):
"WHY IS THERE NO OR LOGIC?!"
→ Valve won't fix it
→ WE WILL! 💪
```

---

#### **Smart Collections Solution:**

**Features:**

```
✅ Full Boolean Logic (AND, OR, NOT)
✅ REGEX Support for text fields
✅ 25+ Filter Types (tags, genre, publisher, year, HLTB, ProtonDB, etc.)
✅ Grouping: (A AND B) OR (C AND D)
✅ Auto-Update (new games → automatically added!)
✅ Sync to Steam (as static collection - works everywhere!)
✅ Visual Builder (no coding required!)
✅ Preview (see results before saving!)
✅ Templates (predefined rule sets!)
✅ Import/Export (share Smart Collections!)
```

**Database Schema:**

```sql
-- Smart Collections metadata
CREATE TABLE smart_collections (
    collection_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    icon TEXT,
    is_active BOOLEAN DEFAULT 1,
    auto_sync BOOLEAN DEFAULT 1,
    last_evaluated INTEGER,
    created_at INTEGER,
    updated_at INTEGER
);

-- Filter rules
CREATE TABLE smart_collection_rules (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    collection_id INTEGER NOT NULL,
    rule_order INTEGER NOT NULL,
    
    filter_type TEXT NOT NULL,  -- tag, genre, publisher, year, etc.
    operator TEXT NOT NULL,      -- equals, contains, regex, gt, lt
    value TEXT,
    value_min INTEGER,
    value_max INTEGER,
    
    logic_operator TEXT DEFAULT 'AND',  -- AND, OR, NOT
    group_id INTEGER,                   -- For grouping
    is_negated BOOLEAN DEFAULT 0,
    case_sensitive BOOLEAN DEFAULT 0,
    
    FOREIGN KEY (collection_id) REFERENCES smart_collections(collection_id)
);

-- Cached results (performance!)
CREATE TABLE smart_collection_cache (
    collection_id INTEGER,
    app_id INTEGER,
    match_score REAL,
    added_at INTEGER,
    PRIMARY KEY (collection_id, app_id)
);

-- Sync state
CREATE TABLE smart_collection_sync (
    collection_id INTEGER PRIMARY KEY,
    steam_collection_name TEXT,
    last_synced INTEGER,
    needs_sync BOOLEAN DEFAULT 1,
    sync_errors TEXT
);
```

---

#### **Filter Types (25+):**

```python
# Text Filters:
TAG, GENRE, PUBLISHER, DEVELOPER, NAME, FRANCHISE

# Numeric Filters:
RELEASE_YEAR, PLAYTIME, PRICE, REVIEW_SCORE, METACRITIC

# Boolean Filters:
IS_FREE, IS_EARLY_ACCESS, HAS_ACHIEVEMENTS, HAS_TRADING_CARDS,
HAS_WORKSHOP, CLOUD_SAVES

# Platform Filters:
PLATFORM, STEAM_DECK, VR_SUPPORT

# Advanced Filters:
HLTB_TIME, PROTONDB_TIER, ACHIEVEMENT_COMPLETION, LAST_PLAYED
```

---

#### **Operators:**

```python
# Text:
EQUALS, CONTAINS, STARTS_WITH, ENDS_WITH, REGEX

# Numeric:
GREATER_THAN, LESS_THAN, GREATER_EQUAL, LESS_EQUAL, BETWEEN

# Boolean:
IS_TRUE, IS_FALSE
```

---

#### **Example Use Cases:**

**1. "LEGO OR Kampf" (User's Request!):**

```
Rule 1: Tag contains "LEGO"
OR
Rule 2: Tag contains "Kampf"

Result: 27 games! ✅
```

**2. "Linux Perfect Games":**

```
Rule 1: Platform equals "Linux"
AND
Rule 2: ProtonDB tier equals "Platinum"
AND
Rule 3: Achievement completion equals 100

Result: Perfect Linux games you've 100%ed!
```

**3. "Quick Games for Deck":**

```
Rule 1: Steam Deck verified equals "verified"
AND
Rule 2: HLTB time less than 120 (< 2 hours)
AND
Rule 3: NOT Is Free (no F2P shovelware)

Result: Short, paid, Deck-verified games!
```

**4. "Hidden Gems":**

```
Rule 1: Review percentage greater than 90
AND
Rule 2: Review count less than 1000
AND
Rule 3: NOT Tag contains "AAA"

Result: Highly rated unknown indie games!
```

**5. "Backlog":**

```
Rule 1: Playtime equals 0
AND
Rule 2: NOT Is Free
AND
Rule 3: Release year greater than 2020

Result: Unplayed paid games from recent years!
```

---

#### **REGEX Power User Examples:**

```
1. Souls-like games:
   Tag REGEX: .*(souls|borne|sekiro).*

2. Japanese developers:
   Developer REGEX: (Nintendo|Sony|Capcom|Square|Konami)

3. Episode games:
   Name REGEX: Episode \d+|Part \d+

4. Year in name:
   Name REGEX: ^\d{4}
```

---

#### **Workflow:**

```
1. USER CREATES:
   ├─ Opens: Werkzeuge → Smart Collection erstellen
   ├─ Name: "LEGO Games"
   ├─ Rule: Tag contains "LEGO"
   ├─ Clicks "Preview" → sees 27 games!
   └─ Clicks "Save & Sync"

2. SLM EVALUATES:
   ├─ Checks all games against rules
   ├─ Finds 27 matching games
   └─ Caches results in database

3. SLM SYNCS TO STEAM:
   ├─ Creates static collection in cloud storage
   ├─ Adds all 27 game IDs
   ├─ Saves cloud-storage-namespace-1.json
   └─ User sees collection in Steam! ✅

4. AUTO-UPDATE:
   ├─ User buys new LEGO game
   ├─ SLM detects new game
   ├─ Evaluates Smart Collections
   ├─ Matches "LEGO Games"!
   ├─ Auto-adds to cache
   ├─ Marks for sync
   └─ Next sync: Steam updated! ✅

5. EDIT RULES:
   ├─ User changes: LEGO OR Duplo
   ├─ SLM re-evaluates
   ├─ Now 35 games match!
   └─ Syncs to Steam → 35 games! ✅
```

---

#### **UI Design:**

**Smart Collection Builder Dialog:**

```
┌────────────────────────────────────────────────────────┐
│  Smart Collection Builder                              │
├────────────────────────────────────────────────────────┤
│                                                        │
│  Collection Info:                                      │
│  Name:        [LEGO oder Kampf Spiele              ]  │
│  Description: [Alle LEGO und Kampf-Spiele          ]  │
│                                                        │
│  ─────────────────────────────────────────────────────│
│                                                        │
│  Rules:                                                │
│  ┌──────────────────────────────────────────────────┐ │
│  │ [ ] NOT  Tag      [contains] [lego        ] [🗑️] │ │
│  │ [OR]  [ ] NOT  Tag   [contains] [kampf    ] [🗑️] │ │
│  │ [AND] [ ] NOT  Platform [equals] [Linux    ] [🗑️] │ │
│  └──────────────────────────────────────────────────┘ │
│  [+ Add Rule]                                          │
│                                                        │
│  ─────────────────────────────────────────────────────│
│                                                        │
│  Preview: 27 games                                     │
│  ┌──────────────────────────────────────────────────┐ │
│  │ LEGO Star Wars: The Complete Saga                │ │
│  │ LEGO Batman                                       │ │
│  │ Mortal Kombat 11                                  │ │
│  │ Street Fighter V                                  │ │
│  │ ...                                               │ │
│  └──────────────────────────────────────────────────┘ │
│                                                        │
│  [Preview]                   [Cancel]  [Save & Sync]  │
└────────────────────────────────────────────────────────┘
```

**Logic Example:**

```
(Tag:LEGO OR Tag:Kampf) AND Platform:Linux

Result: All games with LEGO or Kampf tags that run on Linux!
```

---

#### **Recognition in SLM:**

**How SLM knows a collection is "Smart":**

**Option 1: Emoji Marker** 🧠

```
Smart Collections display with emoji:
🧠 LEGO Games (27)
```

**Option 2: Database Mapping** ✅ **RECOMMENDED!**

```sql
CREATE TABLE smart_collection_mapping (
    steam_name TEXT PRIMARY KEY,
    collection_id INTEGER,
    FOREIGN KEY (collection_id) REFERENCES smart_collections(collection_id)
);
```

**Option 3: Hidden Marker**

```
Description: "All LEGO games [SMART:12345]"
```

---

#### **Implementation:**

**Files:**

```
src/services/smart_collections/
├─ __init__.py
├─ filter_types.py        (FilterType, Operator, LogicOperator enums)
├─ evaluator.py           (SmartCollectionEvaluator class)
├─ manager.py             (SmartCollectionManager class)
└─ models.py              (FilterRule dataclass)

src/ui/dialogs/
├─ smart_collection_builder.py  (Main dialog)
├─ rules_builder_widget.py      (Rules UI)
└─ rule_row_widget.py           (Single rule row)

src/ui/widgets/
└─ smart_collection_tree_item.py (Tree item with 🧠 icon)
```

**Integration Points:**

```python
# In game_manager.py:
def add_game(self, game: Game):
    self.games[game.app_id] = game
    # NEW: Auto-update Smart Collections!
    self.smart_collections.update_on_new_game(game)

# In cloud_storage_parser.py:
def load_collections(self):
    collections = self._parse_cloud_storage()
    # NEW: Check if Smart Collection
    for name in collections:
        if is_smart_collection(name):
            # Load rules for editing
            pass

# In main_window.py:
def populate_tree(self):
    for collection in self.collections:
        if is_smart_collection(collection):
            icon = "🧠"
            label = f"{icon} {collection.name} ({count})"
```

---

#### **Implementation Phases:**

**Phase 1: Foundation (3-4 days)**

```
✅ Database schema
✅ FilterRule dataclass
✅ FilterType & Operator enums
✅ Basic evaluator engine
✅ Unit tests
```

**Phase 2: Manager & Sync (3-4 days)**

```
✅ SmartCollectionManager class
✅ Create/Read/Update/Delete operations
✅ Sync to Steam cloud storage
✅ Auto-sync on new games
✅ Integration with existing code
```

**Phase 3: UI (4-5 days)**

```
✅ Smart Collection Builder Dialog
✅ RulesBuilderWidget
✅ RuleRowWidget with dynamic controls
✅ Preview functionality
✅ Edit existing Smart Collections
```

**Phase 4: Advanced Features (2-3 days)**

```
✅ REGEX support
✅ Complex boolean logic (grouping)
✅ Import/Export rules
✅ Templates (predefined rule sets)
```

**Phase 5: Polish (2-3 days)**

```
✅ Error handling
✅ Performance optimization
✅ i18n keys
✅ Documentation
✅ User guide
```

**Total Estimate:** 14-19 days  
**Priority:** **HIGH** (CRITICAL USER REQUEST!)  
**Dependencies:** Database System (Phase 1 ✅ DONE!)

---

#### **Why This is MEGA:**

```
✅ Solves Valve's Limitation (AND → OR/AND/NOT!)
✅ NO OTHER TOOL HAS THIS!
✅ Works everywhere (syncs to Steam!)
✅ Auto-updates (new games → auto-added!)
✅ Power user features (REGEX!)
✅ Better than Steam itself! 🏆
```

**Complete Documentation:** `SMART_COLLECTIONS_COMPLETE_DESIGN.md`  
**Lines of Code:** ~1500+ (complete implementation ready!)  
**User Impact:** 🔥🔥🔥 **GAME CHANGER!**

---

### 5.4 Hybrid AutoCat (AND/OR Logic) 🔧

**Concept:** See `/mnt/project/__Dynamische_Kollektionen_mit_AND_OR-Logik_-_Feat.md`

**Goal:** Combine multiple AutoCat rules with AND/OR logic

**Example:**

```
Collection: "Couch Co-op Indie"
Rules:
  Genre = Indie AND
  (Tags CONTAINS "Local Co-op" OR Tags CONTAINS "Local Multiplayer") AND
  NOT Tags CONTAINS "Online-Only"
```

**Files:**

- `src/services/autocategorize/hybrid_autocat.py`
- `src/ui/dialogs/hybrid_autocat_dialog.py`

**Estimated:** 4-5 days
**Priority:** MEDIUM

---

## 📊 PHASE 6: DATA & PERFORMANCE

### 6.1 HowLongToBeat Integration ⏳ IN PROGRESS!

**Status:** ✅ **CORE IMPLEMENTED!** (2026-02-16) — 75,4% Match-Rate!

**Ergebnis Batch-Test (2419 Spiele):**

```
✅ 1825 Spiele aktualisiert (75,4%)
❌  594 fehlgeschlagen (24,6%)
   ├─ Games mit 0h Zeiten (DLCs, Online-Only, Tools) → als "checked" gespeichert
   ├─ Leere Namen (AppIDs ohne Name in DB)
   └─ Spiele die HLTB nicht kennt (sehr obskure/alte Titel)
```

**Was bereits funktioniert:**

- ✅ `src/integrations/hltb_api.py` — HLTBClient mit:
    - Reverse-Engineered HLTB API (`/api/finder` + dynamic endpoint discovery)
    - Token-Management (`/api/finder/init`, 5 Min TTL)
    - Levenshtein-Distance Matching mit Popularity-Tiebreaker
    - Two-Pass Search (full name → simplified fallback)
    - 30+ Name-Normalisierungspatterns (inspiriert vom Millennium HLTB Plugin)
    - Unicode-Handling (Superscripts, Dashes, Symbols)
    - Request-Caching (5 Min TTL)
- ✅ `src/services/enrichment_service.py` — EnrichmentThread (QThread):
    - HLTB + Steam API Batch-Enrichment
    - Progress-Signale, Cancel-Support
    - 0h-Matches werden als "checked" in DB gespeichert
- ✅ `src/ui/dialogs/enrichment_dialog.py` — Progress-Dialog
- ✅ `src/ui/actions/enrichment_actions.py` — Menu-Integration
- ✅ AutoCat HLTB (`src/services/autocategorize/autocat_hltb.py`)
- ✅ 60 Unit Tests für HLTB Client
- ✅ DB-Tabelle `hltb_data` mit Batch-Load

**AutoCat Integration (bereits fertig!):**

```python
# Kategorien basierend auf HLTB-Daten:
"Quick Games"  → main_story < 2h
"Short Games"  → main_story < 6h
"Medium Games" → main_story 6-20h
"Long Games"   → main_story > 20h
```

---

#### **6.1.1 ZUKÜNFTIGE VERBESSERUNG: HLTB Steam Import API**

**Ziel:** Die restlichen ~25% Fehlschläge durch Bulk-AppID-Mapping eliminieren!

**Hintergrund:** Das Millennium HLTB Plugin (Jan 2026) nutzt einen undokumentierten
HLTB-Endpoint der direkt Steam-AppIDs auf HLTB-IDs mappt — ohne Namens-Matching!

**Endpoint:** `https://howlongtobeat.com/api/steam/getSteamImportData`

```
Request:
POST /api/steam/getSteamImportData
Headers: x-auth-token: <token>
Body: { "steam_app_ids": [440, 570, 730, ...] }

Response:
{
  "games": [
    { "steam_app_id": 440, "hltb_id": 12345, "game_name": "Team Fortress 2" },
    { "steam_app_id": 570, "hltb_id": 67890, "game_name": "Dota 2" },
    ...
  ]
}
```

**Vorteile:**

- **Kein Namens-Matching nötig!** Direkte AppID → HLTB-ID Zuordnung
- **Bulk-fähig:** Hunderte AppIDs pro Request
- **Höhere Match-Rate:** Auch obskure Spiele die per Name nicht gefunden werden
- **Schneller:** Kein Two-Pass-Search pro Spiel nötig

**Implementation (geplant):**

```python
# In src/integrations/hltb_api.py erweitern:

def bulk_resolve_steam_ids(self, app_ids: list[int]) -> dict[int, int]:
    """Resolve Steam AppIDs to HLTB game IDs via Steam Import API.

    Args:
        app_ids: List of Steam AppIDs to resolve.

    Returns:
        Dict mapping Steam AppID → HLTB game ID.
    """
    # POST /api/steam/getSteamImportData
    # Bulk-Batches von ~200 AppIDs
    # Ergebnis cachen in DB (neue Spalte hltb_id in hltb_data)

def search_game_by_id(self, hltb_id: int) -> HLTBResult | None:
    """Fetch HLTB times directly by HLTB game ID (no name search needed)."""
```

**Strategie: Hybrid-Ansatz:**

```
1. Bulk-Resolve: Alle AppIDs → HLTB-IDs via Steam Import API
2. Direkt-Fetch: Für gemappte Spiele → Zeiten per HLTB-ID holen
3. Fallback: Für nicht-gemappte Spiele → Name-Search (aktueller Code)
```

**Dateien:**

- `src/integrations/hltb_api.py` (erweitern)
- DB-Migration: `hltb_data` + `hltb_id` Spalte

**Estimated:** 1-2 Tage
**Priority:** MEDIUM (aktuelle 75% sind bereits gut!)
**Dependencies:** Reverse-Engineering des Steam Import Endpoints bestätigen

---

### 6.2 ProtonDB Integration (Linux-First!) 🐧

**Goal:** Show Linux/Proton compatibility ratings

**Features:**

- Fetch ProtonDB ratings (Platinum, Gold, Silver, Bronze, Borked)
- Cache in database
- Filter by compatibility
- Create "Linux Perfect" collection

**Database Support:** Add table

```sql
CREATE TABLE protondb_ratings (
    app_id INTEGER PRIMARY KEY,
    tier TEXT,  -- platinum, gold, silver, bronze, borked
    confidence TEXT,  -- high, medium, low
    last_updated INTEGER
);
```

**Files:**

- `src/integrations/protondb_api.py`
- `src/services/autocategorize/autocat_proton.py`

**Estimated:** 2-3 days
**Priority:** HIGH (Linux-First!)

---

### 6.5 External Games Integration (Epic, GOG, etc.) 🎮

**Goal:** Show and manage games from other platforms in SLM

**Inspiration:** BoilR (but modern! BoilR is outdated - uses sharedconfig.vdf)

**Supported Platforms:**

- 🎮 Epic Games Store
- 🎮 GOG Galaxy
- 🎮 Itch.io
- 🎮 Heroic Games Launcher
- 🎮 Lutris
- 🎮 Legendary (Epic CLI)
- 🎮 Flatpak games
- 🎮 Other Non-Steam games

**IMPORTANT NOTE:**

```
⚠️ BoilR (2022) is OUTDATED!
   - Uses sharedconfig.vdf (deprecated!)
   - Doesn't know about cloud-storage-namespace-1.json
   - Collections don't work!

✅ Our Modern Approach (2026):
   - Uses cloud-storage-namespace-1.json ✅
   - Uses shortcuts.vdf (Phase 3.7!) ✅
   - Collections work perfectly! ✅
   - Better than BoilR! 🏆
```

**Implementation:**

#### **6.5.1 Platform Parsers (3-4 days)**

```python
# src/integrations/external_games/epic_parser.py

class EpicGamesParser:
    """Parse Epic Games installed games."""
    
    def read_manifests(self) -> list[ExternalGame]:
        """
        Read Epic Games manifests.
        
        Locations:
        - Linux: ~/.config/legendary/installed.json
        - Linux (Heroic): ~/.config/heroic/legendaryConfig/legendary/installed.json
        - Windows: %PROGRAMDATA%/Epic/EpicGamesLauncher/Data/Manifests/
        
        Returns:
            List of installed Epic games
        """
        manifest_paths = self._get_manifest_paths()
        games = []
        
        for manifest_path in manifest_paths:
            if not manifest_path.exists():
                continue
                
            with open(manifest_path) as f:
                data = json.load(f)
                
            for app_name, app_data in data.items():
                games.append(ExternalGame(
                    platform="Epic Games",
                    app_id=app_data.get("app_name"),
                    name=app_data.get("title"),
                    install_path=Path(app_data.get("install_path")),
                    executable=app_data.get("executable"),
                    launch_options=app_data.get("launch_parameters", "")
                ))
        
        return games

# src/integrations/external_games/gog_parser.py

class GOGParser:
    """Parse GOG games."""
    
    def read_games(self) -> list[ExternalGame]:
        """
        Read GOG installed games.
        
        Locations:
        - Linux (Heroic): ~/.config/heroic/gog_store/installed.json
        - Windows: Registry HKLM\Software\GOG.com\Games
        """
        
# src/integrations/external_games/heroic_parser.py

class HeroicParser:
    """Parse Heroic Games Launcher database."""
    
    def read_installed_games(self) -> list[ExternalGame]:
        """
        Read all games from Heroic (Epic + GOG + Amazon).
        
        Location: ~/.config/heroic/
        """

# src/integrations/external_games/lutris_parser.py

class LutrisParser:
    """Parse Lutris games database."""
    
    def read_games(self) -> list[ExternalGame]:
        """
        Read Lutris games.
        
        Location: ~/.local/share/lutris/pga.db (SQLite!)
        """

# src/integrations/external_games/flatpak_parser.py

class FlatpakGamesParser:
    """Detect Flatpak games."""
    
    def read_games(self) -> list[ExternalGame]:
        """
        Scan for installed Flatpak games.
        
        Command: flatpak list --app
        """
```

**Data Structure:**

```python
# src/integrations/external_games/models.py

@dataclass
class ExternalGame:
    """Game from external platform."""
    platform: str           # "Epic Games", "GOG", etc.
    app_id: str            # Platform-specific ID
    name: str
    install_path: Path
    executable: str | None = None
    launch_options: str = ""
    icon_path: Path | None = None
    
    # Calculated fields
    steam_app_id: int | None = None  # If added to Steam
    
    def get_launcher_command(self) -> str:
        """Get command to launch this game."""
        if self.platform == "Epic Games":
            return f"legendary launch {self.app_id}"
        elif self.platform == "GOG":
            return f"heroic launch {self.app_id} --gog"
        elif self.platform == "Flatpak":
            return f"flatpak run {self.app_id}"
        # ... etc
```

---

#### **6.5.2 Add to Steam Feature (2-3 days)**

```python
# src/services/external_games_service.py

class ExternalGamesService:
    """Manage external games integration with Steam."""
    
    def __init__(
        self,
        shortcuts_manager: ShortcutsManager,
        cloud_storage: CloudStorageParser,
        db: Database
    ):
        self.shortcuts_mgr = shortcuts_manager
        self.cloud_storage = cloud_storage
        self.db = db
        
        # Platform parsers
        self.parsers = {
            "Epic Games": EpicGamesParser(),
            "GOG": GOGParser(),
            "Heroic": HeroicParser(),
            "Lutris": LutrisParser(),
            "Flatpak": FlatpakGamesParser(),
        }
    
    def scan_all_platforms(self) -> dict[str, list[ExternalGame]]:
        """
        Scan all supported platforms for installed games.
        
        Returns:
            Dict mapping platform name to list of games
        """
        all_games = {}
        
        for platform, parser in self.parsers.items():
            try:
                games = parser.read_games()
                if games:
                    all_games[platform] = games
                    logger.info(f"Found {len(games)} {platform} games")
            except Exception as e:
                logger.warning(f"Could not scan {platform}: {e}")
        
        return all_games
    
    def add_to_steam(
        self,
        game: ExternalGame,
        download_artwork: bool = True,
        add_to_collection: bool = True
    ) -> bool:
        """
        Add external game to Steam as Non-Steam game.
        
        Modern approach using:
        - shortcuts.vdf (for the game entry)
        - cloud-storage-namespace-1.json (for collections!)
        
        Args:
            game: External game to add
            download_artwork: Download from SteamGridDB
            add_to_collection: Add to platform collection
            
        Returns:
            True if successful
        """
        # 1. Create shortcut entry
        shortcut = Shortcut(
            app_id=self._calculate_app_id(game),
            app_name=game.name,
            exe=game.get_launcher_command(),
            start_dir=str(game.install_path.parent) if game.install_path else "",
            icon=str(game.icon_path) if game.icon_path else "",
            tags=[f"Platform: {game.platform}"]
        )
        
        # 2. Add to shortcuts.vdf
        shortcuts = self.shortcuts_mgr.read_shortcuts()
        
        # Check if already exists
        existing = next(
            (s for s in shortcuts if s.app_name == game.name),
            None
        )
        if existing:
            logger.info(f"Game '{game.name}' already in Steam")
            return False
        
        shortcuts.append(shortcut)
        self.shortcuts_mgr.write_shortcuts(shortcuts)
        
        # 3. Download artwork (if requested)
        if download_artwork:
            self._download_artwork(game, shortcut.app_id)
        
        # 4. Add to collection (MODERN WAY!)
        if add_to_collection:
            collection_name = f"{game.platform} Games"
            self.cloud_storage.add_to_collection(
                collection_name,
                str(shortcut.app_id)
            )
            self.cloud_storage.save()
        
        # 5. Save to database
        self.db.conn.execute(
            """
            INSERT INTO external_games
            (steam_app_id, platform, platform_app_id, name, install_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                shortcut.app_id,
                game.platform,
                game.app_id,
                game.name,
                str(game.install_path) if game.install_path else None
            )
        )
        self.db.commit()
        
        logger.info(f"Added '{game.name}' to Steam (ID: {shortcut.app_id})")
        return True
    
    def batch_add_to_steam(
        self,
        games: list[ExternalGame],
        progress_callback: Callable | None = None
    ) -> dict[str, int]:
        """
        Add multiple external games to Steam.
        
        Returns:
            Stats dict with added/skipped counts
        """
        stats = {"added": 0, "skipped": 0, "errors": 0}
        
        for i, game in enumerate(games):
            try:
                if self.add_to_steam(game):
                    stats["added"] += 1
                else:
                    stats["skipped"] += 1
            except Exception as e:
                logger.error(f"Error adding {game.name}: {e}")
                stats["errors"] += 1
            
            if progress_callback:
                progress_callback(i + 1, len(games), game.name)
        
        return stats
    
    def _download_artwork(self, game: ExternalGame, steam_app_id: int) -> None:
        """Download artwork from SteamGridDB."""
        from src.integrations.steamgrid_api import SteamGridDB
        
        sgdb = SteamGridDB()
        
        # Search by game name
        results = sgdb.search_game(game.name)
        if not results:
            logger.warning(f"No artwork found for '{game.name}'")
            return
        
        sgdb_id = results[0]["id"]
        
        # Download grid, hero, logo, icon
        for asset_type in ["grids", "heroes", "logos", "icons"]:
            images = sgdb.get_images_by_type(sgdb_id, asset_type)
            if images:
                # Download first image
                url = images[0]["url"]
                SteamAssets.save_custom_image(
                    str(steam_app_id),
                    asset_type,
                    url,
                    db=self.db,
                    source="steamgriddb"
                )
```

**Database Support:**

```sql
-- Add to database_schema.sql

CREATE TABLE external_games (
    steam_app_id INTEGER PRIMARY KEY,  -- Calculated Non-Steam ID
    platform TEXT NOT NULL,             -- Epic, GOG, etc.
    platform_app_id TEXT,               -- Platform-specific ID
    name TEXT NOT NULL,
    install_path TEXT,
    added_at INTEGER DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY (steam_app_id) REFERENCES games(app_id)
);

CREATE INDEX idx_external_platform ON external_games(platform);
```

---

#### **6.5.3 External Games UI (2 days)**

```python
# src/ui/dialogs/external_games_dialog.py

class ExternalGamesDialog(QDialog):
    """Dialog to manage external platform games."""
    
    def __init__(self, external_service: ExternalGamesService, parent=None):
        super().__init__(parent)
        self.service = external_service
        
        # UI Elements
        self.platform_combo = QComboBox()  # Filter by platform
        self.games_table = QTableWidget()
        self.scan_btn = QPushButton(t("ui.external.scan"))
        self.add_selected_btn = QPushButton(t("ui.external.add_selected"))
        self.add_all_btn = QPushButton(t("ui.external.add_all"))
        
        # Progress
        self.progress_bar = QProgressBar()
        self.status_label = QLabel("")
        
        # Connect signals
        self.scan_btn.clicked.connect(self.scan_platforms)
        self.add_selected_btn.clicked.connect(self.add_selected_games)
        self.add_all_btn.clicked.connect(self.add_all_games)
    
    def scan_platforms(self):
        """Scan all platforms for games."""
        self.status_label.setText(t("ui.external.scanning"))
        
        all_games = self.service.scan_all_platforms()
        
        # Populate table
        self.games_table.setRowCount(0)
        for platform, games in all_games.items():
            for game in games:
                self._add_game_row(platform, game)
        
        total = sum(len(g) for g in all_games.values())
        self.status_label.setText(
            t("ui.external.found_games", count=total)
        )
    
    def add_selected_games(self):
        """Add selected games to Steam."""
        selected_rows = self.games_table.selectionModel().selectedRows()
        games_to_add = [
            self._get_game_from_row(row.row())
            for row in selected_rows
        ]
        
        if not games_to_add:
            QMessageBox.warning(
                self,
                t("ui.external.no_selection"),
                t("ui.external.select_games_first")
            )
            return
        
        self._add_games_with_progress(games_to_add)
    
    def add_all_games(self):
        """Add all scanned games to Steam."""
        games_to_add = []
        for row in range(self.games_table.rowCount()):
            game = self._get_game_from_row(row)
            games_to_add.append(game)
        
        if not games_to_add:
            return
        
        reply = QMessageBox.question(
            self,
            t("ui.external.confirm_add_all"),
            t("ui.external.add_all_message", count=len(games_to_add)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._add_games_with_progress(games_to_add)
    
    def _add_games_with_progress(self, games: list[ExternalGame]):
        """Add games with progress tracking."""
        self.progress_bar.setMaximum(len(games))
        
        def progress_callback(current, total, game_name):
            self.progress_bar.setValue(current)
            self.status_label.setText(
                t("ui.external.adding_game", name=game_name, current=current, total=total)
            )
            QApplication.processEvents()
        
        stats = self.service.batch_add_to_steam(games, progress_callback)
        
        QMessageBox.information(
            self,
            t("ui.external.complete"),
            t(
                "ui.external.complete_message",
                added=stats["added"],
                skipped=stats["skipped"],
                errors=stats["errors"]
            )
        )
```

**Menu Integration:**

```
Werkzeuge
├─ ...
├─ ────────────────────────────────
├─ 🎮 External Games                → 🆕
│  ├─ Scan Platforms
│  ├─ Manage External Games
│  └─ Platform Settings
```

---

**Files:**

- `src/integrations/external_games/epic_parser.py`
- `src/integrations/external_games/gog_parser.py`
- `src/integrations/external_games/heroic_parser.py`
- `src/integrations/external_games/lutris_parser.py`
- `src/integrations/external_games/flatpak_parser.py`
- `src/integrations/external_games/models.py`
- `src/services/external_games_service.py`
- `src/ui/dialogs/external_games_dialog.py`
- Database: Add `external_games` table

**Estimated:** 7-9 days total

- 6.5.1: Parsers (3-4 days)
- 6.5.2: Add to Steam (2-3 days)
- 6.5.3: UI (2 days)

**Priority:** LOW (nice-to-have, not critical)

**Dependencies:**

- ✅ Phase 3.7: shortcuts.vdf Manager (REQUIRED!)
- ✅ Database System (already done!)
- ✅ SteamGridDB Integration (already done!)

**Why Later?**

```
This is a BONUS feature:
- Not critical for Steam game management
- Requires shortcuts.vdf Manager first
- Can be skipped if time is limited
- But GREAT for users with multi-platform libraries!

IMPORTANT: Written down so we don't forget! ✅
```

---

## 🎨 PHASE 7: POLISH & RELEASE

### 7.1 UI/UX Polish

- Keyboard shortcuts (comprehensive!)
- Drag & drop for categories
- Context menus (like Steam!)
- Icons & visual polish
- Dark/Light theme support
- Responsive layout

**Estimated:** 3-4 days

---

### 7.2 Documentation

- User Manual (PDF + Online)
- Developer Documentation
- API Documentation
- Video Tutorials
- FAQ

**Estimated:** 3-4 days

---

### 7.3 Packaging

- Flatpak (PRIMARY!)
- AppImage
- DEB package
- RPM package
- Windows installer (future)

**Estimated:** 2-3 days

---

### 7.4 Testing & Hardening

- Unit test coverage > 70%
- Integration tests
- Performance benchmarks
- Bug hunting
- Beta testing

**Estimated:** 4-5 days

---

## 📅 UPDATED TIMELINE

### **Completed (2026-02-14):**

- ✅ Phase 1: Critical Fixes (Database, Performance, Flatpak!)

### **In Progress:**

- ⏳ Phase 3.2: Bootstrap Service (Claude Code)

### **Next Priority:**

- 🎯 Phase 3.5: Menu Redesign (3-4 days)
- 🎯 Phase 3.6.1: Batch Steam API (2-3 days)
- 🎯 Phase 3.6.2: Enhanced CSV Export (3-4 days)
- 🎯 Phase 3.6.3: Smart Import/Export Hub (3-4 days) 🆕
- 🎯 Phase 4.1: AutoCat Types (8-10 days)

### **Medium Priority:**

- Phase 3.7: shortcuts.vdf Manager (2-3 days)
- Phase 4.2: Advanced Filter (3-4 days)
- Phase 4.3: Backup System (2 days)
- Phase 5.1: Steam Deck Optimizer (4-5 days)
- Phase 6.2: ProtonDB Integration (2-3 days)

### **HIGH Priority (User Request!):** 🔥

- **Phase 5.3: Smart Collections (14-19 days)** - CRITICAL! Solves Valve's AND-only limitation!

### **Lower Priority:**

- Phase 4.4: Profile System (3 days) ✅ **DONE!**
- Phase 5.2: Achievement Hunter (3-4 days)
- Phase 5.4: Hybrid AutoCat (4-5 days)
- Phase 6.1: HLTB Integration (3-4 days) ⏳ **IN PROGRESS!**
- Phase 6.5: External Games (7-9 days) 🆕 **OPTIONAL!**

### **Final:**

- Phase 7: Polish & Release (12-15 days)

---

## 🏆 SUCCESS CRITERIA (UPDATED!)

### **Performance:**

- ✅ Startup < 7 seconds (was 30+!) ✅ ACHIEVED!
- ✅ UI responsive (no freezes!) ✅ ACHIEVED!
- ⏳ With Bootstrap: < 3 seconds perceived
- ⏳ CSV Export: < 2 minutes for 3000 games (with Batch API!)

### **Features:**

- ✅ All Depressurizer AutoCat types
- ✅ Better export than Depressurizer (17+ columns!)
- ✅ Multi-device artwork sync
- ✅ Steam Deck specific features
- ✅ Smart Collections
- ✅ Linux-First (ProtonDB, Deck support!)

### **Code Quality:**

- ✅ Test coverage > 70%
- ✅ No hardcoded strings (i18n everywhere!)
- ✅ Clean architecture (< 500 lines per file!)
- ✅ Type hints everywhere
- ✅ ruff/mypy pass

### **UX:**

- ✅ Steam-like filters (Type, Platform, Status!)
- ✅ Better menu structure
- ✅ Progress tracking everywhere
- ✅ Keyboard shortcuts
- ✅ Context menus like Steam
- ✅ Dark/Light theme

---

## 📚 REFERENCES

### **Analyzed Projects:**

1. **Depressurizer v9.3.0.0** (C#/.NET)
    - Source Code Analysis: 175 files, ~50,000 lines
    - AutoCat Types: 15 types
    - Filter System: Allow/Require/Exclude
    - Profile System: Save/Load categories

2. **Steam Metadata Editor** (Python/Tkinter)
    - appinfo.vdf writer (helped us!)
    - Metadata editing
    - Sort As field support

3. **Stelicas** (JavaScript/Electron) 🆕
    - Batch Steam API: IStoreBrowseService/GetItems/v1
    - Rich CSV Export: 17+ columns
    - Progress tracking
    - Two-file export system (simple + full)
    - **KEY LEARNINGS:** Batch API is 200x faster!

### **Documentation:**

- `/mnt/project/__shortcuts_manager_py_Konzept.md` - shortcuts.vdf spec
- `/mnt/project/__Dynamische_Kollektionen_mit_AND_OR-Logik_-_Feat.md` - Hybrid AutoCat
- `STELICAS_ANALYSIS.md` - Complete Stelicas analysis 🆕
- `MENU_REDESIGN_v2.md` - Complete menu structure 🆕
- `MENU_FINAL.md` - Final approved menu 🆕
- `DATABASE_TESTING_GUIDE.md` - Database integration tests 🆕
- `SMART_COLLECTIONS_COMPLETE_DESIGN.md` - Complete Smart Collections system 🆕🔥
    - 100+ pages complete design
    - Database schema (4 tables)
    - Evaluation engine (~500 lines)
    - Manager class (~400 lines)
    - Complete UI design
    - 8+ use case examples
    - REGEX support
    - Solves Valve's AND-only limitation!

---

## 🎉 CONCLUSION

**We are building the BEST Steam Library Manager!**

**Key Achievements (2026-02-14):**

- ✅ Database system (40+ tables, 4.3x faster startup!)
- ✅ Multi-device artwork sync
- ✅ Flatpak support (Linux-First!)
- ✅ No UI freezes anymore!

**Key Next Steps:**

1. Menu Redesign (Steam-like filters!)
2. Batch Steam API (200x faster metadata!)
3. Enhanced Export (17+ columns!)
4. AutoCat Types (Depressurizer parity!)

**Unique Selling Points:**

- 🐧 **Linux-First** (Flatpak, ProtonDB, Deck support!)
- 🎨 **Multi-Device Artwork Sync** (export/import!)
- 📊 **Rich CSV Export** (17+ columns, Stelicas-inspired!)
- 🚀 **Fast Startup** (< 7s, target < 3s!)
- 🧠 **Smart Collections** (OR/AND/NOT + REGEX - Solves Valve's limitation!) 🔥
- 🎮 **Steam Deck Optimizer** (unique!)
- 💾 **Modern Database** (SQLite, 40+ tables!)
- ⚡ **Auto-Updates** (Smart Collections auto-add new games!)

**WE WILL DOMINATE!** 🏆

---

**Last Updated:** 2026-02-16 by Sarah (Claude Opus)
**Total Phases:** 7
**Current Phase:** 5 (Performance Plus & Data Quality)
**Completion:** ~55% (Phase 1-4 done, Phase 5 in progress!)
**ETA to Beta:** ~6-8 weeks
**ETA to Release:** ~10-12 weeks

---

**LET'S GO! 🚀🔥💪**
