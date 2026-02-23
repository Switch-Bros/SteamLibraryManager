# 📖 Steam Library Manager — User Manual

**Version:** 1.0
**Platform:** Linux (CachyOS, Ubuntu, Fedora, Arch, SteamOS, etc.)

---

## Table of Contents

1. [What is Steam Library Manager?](#what-is-steam-library-manager)
2. [Installation](#installation)
3. [First Launch](#first-launch)
4. [Main Interface](#main-interface)
5. [Managing Collections](#managing-collections)
6. [Smart Collections](#smart-collections)
7. [Auto-Categorization](#auto-categorization)
8. [Data Enrichment](#data-enrichment)
9. [External Games](#external-games)
10. [Import & Export](#import--export)
11. [Profiles & Backup](#profiles--backup)
12. [View Filters & Sorting](#view-filters--sorting)
13. [Settings](#settings)
14. [Keyboard Shortcuts](#keyboard-shortcuts)
15. [Troubleshooting](#troubleshooting)

---

## What is Steam Library Manager?

Steam Library Manager (SLM) is a powerful tool for organizing large Steam game libraries on Linux. Think of it as a modern, Linux-native alternative to Depressurizer — with extras.

**Key Features:**
- Organize 3000+ games into collections that sync with Steam
- 15+ automatic categorization types (genre, tags, playtime, HLTB, and more)
- Smart Collections with AND/OR/NOT logic (something Steam can't do natively)
- Data enrichment from HLTB, ProtonDB, and Steam Deck compatibility
- Manage non-Steam games from Epic, GOG, Lutris, and 5 other platforms
- Full import/export support (CSV, VDF, JSON)

**What makes SLM different from Depressurizer?**
- Linux-first (Flatpak, AppImage)
- Smart Collections with OR logic (Depressurizer and Steam only support AND)
- ProtonDB and Steam Deck integration
- HLTB data directly in your library
- External games management (8 platform parsers)
- Modern SQLite database for fast performance

---

## Installation

### Flatpak (Recommended)

```bash
flatpak install flathub com.github.steamlibmgr.SteamLibraryManager
```

### AppImage

1. Download the latest `.AppImage` from the [GitHub Releases](https://github.com/HeikesFootSlave/SteamLibraryManager/releases) page
2. Make it executable: `chmod +x SteamLibraryManager-*.AppImage`
3. Run: `./SteamLibraryManager-*.AppImage`

### From Source

```bash
git clone https://github.com/HeikesFootSlave/SteamLibraryManager.git
cd SteamLibraryManager
pip install -r requirements.txt
python -m src.main
```

Requires Python 3.11+ and PyQt6.

---

## First Launch

On first launch, SLM will:

1. **Detect your Steam installation** — automatically finds your Steam path
2. **Ask for your Steam account** — select which Steam user's library to manage
3. **Build the local database** — this takes 10-30 seconds on first run as it indexes your library
4. **Load your collections** — reads your existing Steam categories from cloud storage

After the initial setup, subsequent launches take less than 3 seconds.

**Important:** Make sure Steam is not running when you first use SLM, or at least don't modify collections in Steam while SLM is open. SLM syncs with Steam's cloud storage, and simultaneous writes can cause conflicts.

---

## Main Interface

The main window has four areas:

```
┌─────────────────────────────────────────────────────────┐
│  Menu Bar  |  Toolbar                                   │
├──────────────┬──────────────────────────────────────────┤
│              │                                          │
│  Category    │  Game List / Details                     │
│  Tree        │                                          │
│  (Sidebar)   │                                          │
│              │                                          │
│  Ctrl+B to   │  Click a game to see details             │
│  toggle      │  Space to toggle details panel           │
│              │                                          │
├──────────────┴──────────────────────────────────────────┤
│  Status Bar — game count, filter status, messages       │
└─────────────────────────────────────────────────────────┘
```

**Sidebar (Category Tree):** Shows all your collections, smart collections, and special categories (All Games, Uncategorized, Favorites, Hidden). Click to filter. Right-click for context menu.

**Game List:** Shows games in the selected category. Multi-select with Ctrl+Click or Shift+Click.

**Details Panel:** Shows metadata, artwork, playtime, achievements, and more for the selected game. Toggle with `Space`.

**Status Bar:** Live statistics about your current view — how many games are shown, which filters are active.

---

## Managing Collections

### Creating a Collection

Right-click in the category tree → "New Collection" → enter a name. The collection syncs to Steam automatically.

### Adding Games to Collections

1. Select one or more games in the game list
2. Drag them to a collection in the sidebar, OR
3. Right-click → "Add to Collection" → select target

### Removing Games from Collections

1. Select games within a collection
2. Press `Del`, OR
3. Right-click → "Remove from Collection"

### Renaming Collections

Select a collection → press `F2` → type the new name.

### Syncing with Steam

SLM reads and writes to Steam's cloud storage (`cloud-storage-namespace-1.json`). Changes you make in SLM appear in Steam after restarting Steam. Changes made in Steam appear in SLM after refreshing (`Ctrl+R`).

**Conflict handling:** If Steam's cloud file was modified while SLM was open, SLM creates a backup before saving and shows a warning.

---

## Smart Collections

Smart Collections are live-updating folders based on rules. They automatically include any game matching your criteria and update whenever your library changes.

### Creating a Smart Collection

1. Press `Ctrl+Shift+N` or go to Edit → Collections → Create Smart Collection
2. Give it a name
3. Add rules using the rule builder

### Rule Logic

Rules support three operators:

- **AND** — All conditions must be true (default)
- **OR** — At least one condition must be true
- **NOT** — Exclude games matching this condition

**Example:** "Linux RPGs under 20 hours"
```
Platform = Linux  AND
Genre contains "RPG"  AND
HLTB Main Story < 20h
```

**Example:** "Weekend picks" (games that are EITHER short OR highly rated)
```
(HLTB Main Story < 10h  OR  Review Score > 90%)
AND  Status = Not Started
```

### Available Rule Types

| Field | Operators | Example |
|-------|-----------|---------|
| Genre | contains, not contains | Genre contains "RPG" |
| Tags | contains, not contains | Tags contains "Open World" |
| Platform | equals | Platform = Linux |
| Playtime | <, >, =, between | Playtime < 120 minutes |
| Review Score | <, >, between | Review > 85% |
| HLTB Time | <, >, between | Main Story < 20h |
| Deck Status | equals | Deck = Verified |
| Achievement % | <, >, between | Achievements > 75% |
| Release Year | <, >, =, between | Year > 2020 |
| Developer | equals, contains | Developer = "Valve" |
| Publisher | equals, contains | Publisher contains "Devolver" |
| Language | supports | Language supports German |
| Name | contains, regex | Name contains "Dark" |

### Refreshing Smart Collections

Smart Collections update automatically when:
- You refresh data (`Ctrl+R`)
- Enrichment adds new metadata
- You manually refresh (Edit → Collections → Refresh Smart Collections)

---

## Auto-Categorization

AutoCat (`Ctrl+Shift+A`) automatically sorts games into categories based on their metadata.

### How to Use

1. Select games to categorize (or choose "All Games" in the dialog)
2. Open AutoCat: `Ctrl+Shift+A`
3. Enable the categorization types you want
4. Optional: Adjust settings per type (e.g., "Top 5 tags" instead of "Top 3")
5. Click "Start"

### AutoCat Types

| Type | Creates categories like... |
|------|---------------------------|
| Genre | "Action", "RPG", "Strategy" |
| Tags | "Open World", "Co-op", "Roguelike" |
| Developer | "Valve", "FromSoftware" |
| Publisher | "Devolver Digital", "Annapurna" |
| Platform | "Linux Native", "Windows Only" |
| Year | "2024", "2023", "Pre-2000" |
| User Score | "Overwhelmingly Positive", "Mixed" |
| Playtime | "Unplayed", "< 5h", "5-20h", "20h+" |
| HLTB | "Quick (< 5h)", "Medium", "Long (40h+)" |
| Deck Status | "Deck: Verified", "Deck: Playable" |
| Achievements | "100% Complete", "Almost (>90%)" |
| Language | "Supports German", "Japanese Available" |
| VR | "VR Supported", "VR Only" |
| Flags | "Early Access", "Free to Play" |
| Franchise | Game series groupings |
| Curator | Based on curator recommendations |

### Presets

Save your AutoCat configuration as a preset to reuse it:
- Click "Save Preset" → enter a name
- Next time, "Load Preset" to restore your exact configuration
- Delete presets you no longer need

**Tip:** Run AutoCat after enriching your library for the best results — more metadata means more accurate categorization.

---

## Data Enrichment

SLM can fetch additional data from multiple sources to enrich your game metadata.

### Available Sources

| Source | Menu Path | Data Added |
|--------|-----------|------------|
| Steam API | Tools → Batch → Update Metadata | Genres, tags, descriptions, screenshots, review scores |
| HLTB | Tools → Batch → Update HLTB | Main story, completionist, and all playstyles times |
| ProtonDB | Tools → Batch → Update ProtonDB | Linux compatibility ratings (Platinum, Gold, Silver, etc.) |
| Steam Deck | Tools → Batch → Update Deck Status | Verified, Playable, Unsupported, Unknown |
| Achievements | Tools → Batch → Update Achievements | Achievement count, completion percentage |
| Tags | Tools → Batch → Import Tags | Steam community tags from appinfo.vdf |

### Refresh ALL Data

Tools → Batch → "Refresh ALL Data" runs all enrichments in parallel with a multi-track progress display showing each source independently.

### Force Refresh

Each source has a "Force Refresh" variant that re-fetches ALL data, even cached entries. Use this when:
- Ratings have changed (e.g., a game got Deck Verified status)
- You suspect cached data is outdated
- After a major Steam sale (new games added)

---

## External Games

SLM can detect and manage games from 8 non-Steam platforms (`Ctrl+Shift+E`).

### Supported Platforms

| Platform | Detection Method |
|----------|-----------------|
| Epic Games Store | Local manifest files |
| GOG Galaxy | GOG database |
| Heroic Launcher | Heroic configuration |
| Lutris | Lutris database |
| Flatpak | Installed Flatpak games |
| Bottles | Bottles configuration |
| itch.io | itch app database |
| Amazon Games | Amazon launcher data |

### Adding External Games to Steam

1. Open External Games manager (`Ctrl+Shift+E`)
2. Click "Scan Platforms" to detect installed games
3. Select games to add
4. SLM creates Non-Steam shortcuts with:
   - Correct launch commands
   - Artwork from SteamGridDB (automatic)
   - Platform collection (e.g., "Epic Games")

---

## Import & Export

### Export Options (File → Export)

| Format | Content | Use Case |
|--------|---------|----------|
| Collections VDF | Category assignments | Backup or share your organization |
| Collections Text | Human-readable category list | Quick overview |
| CSV Simple | Basic game list | Spreadsheets, simple analysis |
| CSV Full | All metadata (17+ columns) | Data analysis, comparison |
| JSON | Database export | Full backup, migration |
| Smart Collections | Smart Collection rules | Share rules with others |
| DB Backup | Complete SQLite database | Full data backup |

### Import Options (File → Import)

| Format | What it restores |
|--------|-----------------|
| Collections VDF | Category assignments |
| Smart Collections | Smart Collection rules |
| DB Backup | Full database state |

---

## Profiles & Backup

### Profiles

Profiles save a snapshot of your entire category organization.

- **Save:** File → Profiles → Save Current
- **Load:** File → Profiles → Manage → select profile → Load
- **Use case:** Save before major reorganization, restore if unhappy with results

### Backup

Multiple backup mechanisms:

| Method | What | How |
|--------|------|-----|
| Auto-backup | Cloud storage backup before every save | Automatic |
| Manual backup | `Ctrl+Shift+S` | Database snapshot |
| Export | File → Export → DB Backup | Complete database |
| Profiles | File → Profiles → Save | Category snapshot |

---

## View Filters & Sorting

The View menu provides powerful filtering and sorting.

### Sort Options

| Sort | Behavior |
|------|----------|
| Name | Alphabetical A→Z |
| Playtime | Most played first |
| Last Played | Most recently played first |
| Release Date | Newest first |

### Filter Submenus

All filters are stackable — enable multiple to narrow your view.

**Type:** Games, Soundtracks, Software, Videos, DLCs, Tools (all enabled by default)

**Platform:** Linux, Windows, SteamOS (all enabled by default)

**Status:** Installed, Not Installed, Hidden, With Playtime, Favorites (all disabled by default — enable to filter)

**Language:** 15 languages available. Enable one or more to show only games supporting those languages.

**Steam Deck:** Verified, Playable, Unsupported, Unknown

**Achievements:** Perfect (100%), Almost (>90%), In Progress, Started, None

---

## Settings

Open settings with `Ctrl+P` or Tools → Settings.

### General Tab

- **Language:** Switch between English and German (more languages planned)
- **Steam Path:** Auto-detected, can be overridden
- **Steam User:** Select which Steam account to manage

### Other Tab

- Additional configuration options
- Backup settings

---

## Keyboard Shortcuts

See the full [Keyboard Shortcuts](KEYBOARD_SHORTCUTS.md) reference.

Quick overview:

| Shortcut | Action |
|----------|--------|
| `Ctrl+F` | Search |
| `Ctrl+S` | Save |
| `Ctrl+R` / `F5` | Refresh |
| `Ctrl+B` | Toggle sidebar |
| `Space` | Toggle details |
| `Esc` | Clear search / selection |
| `Ctrl+Shift+N` | New Smart Collection |
| `Ctrl+Shift+A` | Auto-Categorize |
| `F1` | This manual |

---

## Troubleshooting

### SLM doesn't find my Steam installation

SLM looks for Steam in standard locations (`~/.steam`, `~/.local/share/Steam`). If your Steam is installed elsewhere, set the path manually in Settings → General → Steam Path.

### Collections don't appear in Steam

1. Make sure you saved in SLM (`Ctrl+S`)
2. Restart Steam completely (not just minimize to tray)
3. Check if Steam Cloud Sync is enabled in Steam settings

### First launch is very slow

Normal! SLM builds its local SQLite database on first run. This indexes your entire library and takes 10-30 seconds depending on library size. Subsequent launches are under 3 seconds.

### Enrichment shows errors for some games

Some games (removed from Steam, region-locked, or very old) may not have data available from all sources. SLM skips these gracefully and enriches what it can.

### "Conflict detected" warning when saving

This means Steam's cloud storage file was modified while SLM was open (probably by Steam itself). SLM creates a backup before saving. Your data is safe — refresh (`Ctrl+R`) to see the latest state.

### External Games scanner finds nothing

Make sure the platform launcher (Epic, GOG, etc.) is actually installed and has been run at least once. SLM reads local configuration files that are created when you first run each launcher.

### ProtonDB / Deck Status filters show 0 results

Run Tools → Batch → Update ProtonDB and Update Deck Status first. These filters require enrichment data that isn't loaded by default.

---

*For more answers, see the [FAQ](FAQ.md).*

*Need more help? Visit Help → Online → Discussions or Report Issues on GitHub.*
