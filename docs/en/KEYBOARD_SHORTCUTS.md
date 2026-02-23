# ⌨️ Keyboard Shortcuts

All keyboard shortcuts available in Steam Library Manager.

---

## File Operations

| Shortcut | Action | Notes |
|----------|--------|-------|
| `Ctrl+S` | Save collections | Saves to cloud storage or localconfig |
| `Ctrl+R` | Refresh data | Reloads game data from Steam |
| `F5` | Refresh data | Alternative to Ctrl+R |
| `Ctrl+Shift+S` | Create backup | Exports a database backup snapshot |
| `Ctrl+Q` | Exit application | |

## Navigation & View

| Shortcut | Action | Notes |
|----------|--------|-------|
| `Ctrl+F` | Focus search bar | Jump to search, start typing immediately |
| `Ctrl+B` | Toggle sidebar | Show/hide the category tree |
| `Space` | Toggle details panel | Show/hide game details (when tree has no focus) |
| `Esc` | Clear / Deselect | **Layered:** 1st press clears search, 2nd press clears selection |

## Game & Category Management

| Shortcut | Action | Notes |
|----------|--------|-------|
| `Ctrl+A` | Select all games | Selects all games in the current category |
| `Del` | Remove from category | Removes selected games from the active category |
| `F2` | Rename category | Renames the currently selected category |
| `Ctrl+I` | Image Browser | Opens the artwork browser for the selected game |

## Collections & AutoCat

| Shortcut | Action | Notes |
|----------|--------|-------|
| `Ctrl+Shift+N` | New Smart Collection | Create a new Smart Collection with AND/OR/NOT rules |
| `Ctrl+Shift+A` | Auto-Categorize | Opens the AutoCat dialog with 15+ categorization types |

## Tools

| Shortcut | Action | Notes |
|----------|--------|-------|
| `Ctrl+Shift+E` | External Games | Manage non-Steam games (Epic, GOG, Lutris, etc.) |
| `Ctrl+P` | Settings | Open application settings |

## Help

| Shortcut | Action | Notes |
|----------|--------|-------|
| `F1` | User Manual | Opens this documentation |

## Escape Key — Layered Behavior

The `Esc` key works in layers, which means pressing it multiple times does different things:

1. **First press:** If the search bar has text → clears the search
2. **Second press:** If games are selected → clears the selection
3. **Third press:** Nothing (you're already at the base state)

This design lets you quickly get back to a clean view without losing your place.

---

## Quick Reference Card

```
Navigation                    File Operations
─────────────────────────     ─────────────────────────
Ctrl+F    Search              Ctrl+S    Save
Ctrl+B    Toggle sidebar      Ctrl+R    Refresh
Space     Toggle details      F5        Refresh (alt)
Esc       Clear/Deselect      Ctrl+Shift+S  Backup
                              Ctrl+Q    Exit

Game Management               Tools & Features
─────────────────────────     ─────────────────────────
Ctrl+A    Select all          Ctrl+Shift+N  Smart Collection
Del       Remove from cat     Ctrl+Shift+A  Auto-Categorize
F2        Rename category     Ctrl+Shift+E  External Games
Ctrl+I    Image browser       Ctrl+P        Settings
                              F1            Help
```
