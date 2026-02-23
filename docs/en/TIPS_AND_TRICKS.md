# 💡 Tips & Tricks

Power-user tips to get the most out of Steam Library Manager.

---

## 🔍 Search Like a Pro

The search bar (`Ctrl+F`) does instant full-text filtering across game names. Combine it with View menu filters for powerful results:

- **Search + Type filter:** Search "dark" with only "Games" enabled → finds Dark Souls, Darkest Dungeon, etc. without matching soundtracks or DLCs.
- **Search + Platform filter:** Disable "Windows" in View → Platform to see only Linux-native games matching your search.
- **Quick clear:** Press `Esc` to instantly clear the search and see your full library again.

## 📂 Organize with Smart Collections

Smart Collections are live-updating folders that automatically include games matching your rules. They're the most powerful feature in SLM.

**Getting started:**
1. `Ctrl+Shift+N` to create a new Smart Collection
2. Add rules using AND/OR/NOT logic
3. The collection updates automatically when your library changes

**Useful Smart Collection ideas:**

| Collection Name | Rules |
|----------------|-------|
| "Quick Sessions" | Playtime < 2h AND Genre contains "Indie" |
| "Linux Native" | Platform = Linux AND Status = Installed |
| "Unplayed Gems" | Playtime = 0 AND Review Score > 85% |
| "Deck Ready" | Deck Status = Verified AND Playtime < 10h |
| "Almost Done" | Achievement % > 75% AND Achievement % < 100% |

## 🏷️ AutoCat — Automatic Categorization

AutoCat (`Ctrl+Shift+A`) can automatically sort your entire library into categories. With 15+ categorization types, you can organize by:

- **Genre** — RPG, Action, Strategy, etc.
- **Developer / Publisher** — Group by studio
- **Platform** — Linux, Windows, SteamOS
- **Tags** — Top N Steam tags per game
- **Year** — Release year categories
- **HLTB** — "Short (< 5h)", "Medium (5-20h)", "Long (20h+)"
- **Deck Status** — Verified, Playable, Unsupported
- **Achievements** — Perfect, Almost, In Progress
- **Language** — Games supporting specific languages
- **User Score** — Overwhelmingly Positive, Mixed, etc.
- And more!

**Pro tip:** Save your AutoCat configuration as a preset. You can load it anytime to re-categorize after adding new games.

## 🔄 Enrichment — Fill in Missing Data

Under Tools → Batch Operations, you can enrich your library with data from multiple sources:

| Source | What it adds | How long |
|--------|-------------|----------|
| Steam API | Genres, tags, descriptions, screenshots | ~2 min for 3000 games |
| HLTB | How Long to Beat times | ~5 min (rate limited) |
| ProtonDB | Linux compatibility ratings | ~1 min |
| Steam Deck | Deck verification status | ~2 min |
| Achievements | Achievement stats & percentages | ~3 min |

**"Refresh ALL Data"** runs all enrichments in parallel with a multi-track progress display. Best used after a fresh install or when you've added many new games.

**Force refresh** variants (available per source) re-fetch even cached data — useful when ratings change or new data becomes available.

## 🎮 External Games

SLM can find and manage games from other platforms (`Ctrl+Shift+E`):

- **Epic Games Store** — Scans local manifests
- **GOG Galaxy** — Reads GOG database
- **Heroic Launcher** — Epic/GOG via Heroic
- **Lutris** — Any game configured in Lutris
- **Flatpak** — Games installed as Flatpaks
- **Bottles** — Windows games via Bottles
- **itch.io** — Games from itch
- **Amazon Games** — Amazon Gaming library

Found games can be added to Steam as Non-Steam shortcuts, complete with artwork from SteamGridDB.

## 💾 Backup Strategy

SLM has multiple layers of protection:

1. **Auto-backup:** Cloud storage is backed up before every save
2. **Manual backup:** `Ctrl+Shift+S` creates a timestamped database snapshot
3. **Profiles:** File → Profiles → Save Current lets you snapshot your entire category setup
4. **Export:** File → Export gives you CSV, VDF, and JSON exports

**Recommendation:** Save a profile before major reorganization. If something goes wrong, load the profile to restore.

## ⚡ Performance Tips

- **First start is slow** — SLM builds its local database on first launch. Subsequent starts are much faster (< 3 seconds).
- **Use batch enrichment** — Run "Refresh ALL Data" once after setup, then use individual enrichments for updates.
- **Large libraries (3000+ games):** The sidebar may take a moment to rebuild after major AutoCat runs. This is normal.

## 🖥️ View Customization

The View menu has powerful filter submenus:

- **Sort by:** Name, Playtime, Last Played, Release Date
- **Type:** Show/hide Games, Soundtracks, Software, Videos, DLCs, Tools
- **Platform:** Filter by Linux, Windows, SteamOS support
- **Status:** Installed, Not Installed, Hidden, With Playtime, Favorites
- **Language:** Filter by 15 supported languages
- **Steam Deck:** Verified, Playable, Unsupported, Unknown
- **Achievements:** Perfect, Almost, In Progress, Started, None

All filters stack — enable multiple to narrow your view.

## 🔐 Security

- Steam login tokens are stored in your system keyring (or AES-GCM encrypted fallback)
- No passwords or API keys are stored in plain text
- Cloud storage sync uses Steam's own authentication

## 🎯 Hidden Features

- **Drag & Drop:** Drag games between categories in the sidebar
- **Multi-select:** Click games while holding `Ctrl` or `Shift` for bulk operations
- **Right-click context menus:** Right-click on games or categories for quick actions
- **Double-click:** Double-click a game to open its Steam store page
- **Status bar:** Shows live statistics about your current view (game count, filters active)

---

*Found a bug or have a feature request? Help → Online → Report Issues*
