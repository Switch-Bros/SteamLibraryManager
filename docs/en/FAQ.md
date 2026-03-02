# ❓ Frequently Asked Questions

---

## General

### What is SLM?

Steam Library Manager (SLM) is a Linux-native tool for organizing large Steam game libraries. It creates, edits, and manages Steam collections and categories — like Depressurizer, but built for Linux with modern features.

### Is SLM a replacement for Depressurizer?

Yes. SLM has full Depressurizer feature parity (all 17 AutoCat types, profiles, filters) plus features Depressurizer doesn't have: Smart Collections with OR logic, ProtonDB integration, HLTB data, Steam Deck status, external games from 8 platforms, and a fast SQLite database.

### Does SLM work on Windows?

SLM is Linux-first. While the codebase is Python/PyQt6 and could theoretically run on Windows, it's designed and tested for Linux. Windows support may come in the future.

### Is SLM free?

Yes, SLM is free and open source. If you find it useful, you can support development via Help → Support (PayPal, GitHub Sponsors, or Ko-fi).

### Does SLM modify my Steam files?

SLM writes to Steam's `cloud-storage-namespace-1.json` (the cloud collections file) and optionally to `shortcuts.vdf` (for external games). It creates backups before every write. Your game installations are never touched.

---

## Setup & Installation

### What are the system requirements?

- Linux (any modern distribution)
- Python 3.11+ (if running from source)
- Steam installed and logged in at least once
- ~50 MB disk space for the application + database

### Which Steam accounts does SLM support?

SLM works with any Steam account that has been logged into on your machine. On first launch, you select which account to manage. You can switch accounts in Settings.

### Can I use SLM while Steam is running?

Yes, but with caution. If you modify collections in both SLM and Steam at the same time, a conflict can occur. SLM handles this gracefully (backup + warning), but it's best to save and close SLM before making changes in Steam.

### My Steam is installed in a non-standard location

Go to Settings (`Ctrl+P`) → General → Steam Path and set the correct path. SLM auto-detects `~/.steam` and `~/.local/share/Steam` but supports any location.

---

## Security & Privacy

### Is it safe to log into Steam through SLM?

Yes. SLM uses Steam's official OAuth2 API (`IAuthenticationService`) — the same authentication system the Steam desktop client uses. With QR code login (recommended), SLM never even sees your password. With password login, your password is RSA-encrypted with Steam's public key before it leaves your machine.

### Can SLM steal my inventory or trade my items?

No. This is technically impossible. SLM has no trade endpoints implemented, and the OAuth token scopes don't permit trades or purchases. Steam additionally requires Mobile Confirmation for all trades, which SLM cannot trigger.

### What can SLM actually do with my account?

SLM's access is limited to reading your game list, reading and writing your collections, and fetching Steam Store metadata. It cannot change your password, change your email, disable Steam Guard, make purchases, or access your inventory.

### How are my login tokens stored?

Tokens are stored using your system keyring (KWallet on KDE, GNOME Keyring, etc.) — the same secure storage your browser uses for passwords. If no keyring is available, SLM falls back to AES-GCM encrypted files where the key is derived from your machine ID via PBKDF2. Tokens are never stored in plain text.

### Do I need a Steam API key?

No. The Steam API key is optional. SLM's primary method reads your games directly from local Steam files (licensecache, packageinfo.vdf). The API key only enables some additional metadata lookups and is stored locally in your config — never transmitted to third parties.

### Does SLM collect any data or phone home?

No. SLM has zero telemetry and makes no network calls except to Steam's API, SteamGridDB, HowLongToBeat, and ProtonDB. You can verify this yourself:
```bash
grep -r "requests\.\(get\|post\)" src/ | grep -v test | grep -v __pycache__
```

### How do I revoke SLM's access to my account?

Three options: use Settings → Logout in SLM (deletes all local tokens), visit https://store.steampowered.com/twofactor/manage to deauthorize all devices, or simply delete `~/.config/SteamLibraryManager/tokens.enc`.

### I have an expensive inventory. Should I be worried?

No. Even in a worst-case scenario where someone stole your token, they could only read your game list — not trade items, make purchases, or change account settings. With 2FA active, your account remains secure regardless.

---

## Collections & Categories

### What's the difference between a Collection and a Smart Collection?

A **Collection** is a manual folder — you add and remove games yourself. A **Smart Collection** is rule-based — it automatically includes every game matching your criteria and updates itself when your library changes.

### Do my collections sync back to Steam?

Yes. SLM reads from and writes to Steam's cloud storage. After saving in SLM and restarting Steam, your collections appear in Steam's library.

### I made a mess of my categories. Can I undo?

Use File → Profiles → Manage to load a saved profile, or File → Import → DB Backup to restore from a backup. If you saved a profile before the changes, you can fully restore your previous organization.

### Can I have a game in multiple collections?

Yes. Games can belong to any number of collections simultaneously, just like in Steam.

### What does "Uncategorized" mean?

Games that aren't in any collection. This is a virtual category — you can't add games to it, but you can drag games from it into collections.

---

## Smart Collections

### What operators can I use?

AND (all conditions true), OR (at least one true), NOT (exclude matching games). You can nest these for complex logic like `(Genre = RPG OR Genre = Strategy) AND Platform = Linux AND NOT Status = Abandoned`.

### Why does my Smart Collection show 0 games?

Most likely the metadata your rules depend on hasn't been loaded yet. Run the appropriate enrichment (Tools → Batch) first. For example, HLTB-based rules need HLTB enrichment, Deck rules need Deck status enrichment.

### Do Smart Collections count against Steam's collection limit?

No. Smart Collections are evaluated locally by SLM. Only when you explicitly "export" or "convert" them to regular collections do they become Steam collections.

---

## Auto-Categorization

### Does AutoCat overwrite my existing categories?

No. AutoCat adds games to new categories (e.g., "Genre: RPG") but doesn't remove them from existing ones. Your manual organization is preserved.

### What's the best AutoCat setup for a large library?

For a library of 1000+ games, we recommend:
1. First run enrichment (Tools → Batch → Refresh ALL Data)
2. Then AutoCat with: Genre + Tags (Top 3) + Platform + Deck Status
3. Optionally add: HLTB + Year for further organization

### Can I customize the category names AutoCat creates?

AutoCat uses prefix patterns (e.g., "Genre: Action", "HLTB: Short"). The prefix format is determined by the AutoCat type and follows Steam community conventions.

---

## Data Enrichment

### Where does the enrichment data come from?

| Source | Provider | Rate Limits |
|--------|----------|-------------|
| Game metadata | Steam Web API | ~200 requests/5min |
| HLTB times | HowLongToBeat.com | ~1 request/sec |
| ProtonDB ratings | ProtonDB.com | Batch API, fast |
| Deck status | Steam API | ~200 requests/5min |
| Achievements | Steam Web API | ~200 requests/5min |

### How often should I run enrichment?

Once after initial setup, then occasionally when you add many new games (e.g., after a Steam sale). Individual game data can be refreshed by right-clicking a game.

### Does enrichment use my Steam API key?

No. SLM uses Steam's public API endpoints that don't require an API key. Your Steam login session is used only for cloud storage sync.

### HLTB data seems wrong for some games

HLTB matching uses fuzzy name matching with a 94.8% accuracy rate. Some games with very generic names or significant differences between Steam and HLTB naming may match incorrectly. This is rare but expected.

---

## External Games

### Which platforms are supported?

Epic Games Store, GOG Galaxy, Heroic Launcher, Lutris, Flatpak games, Bottles, itch.io, and Amazon Games.

### Do I need the platform launchers installed?

Yes. SLM reads each platform's local configuration files, which only exist if the launcher has been installed and run at least once.

### Can I remove games from Steam that I added via External Games?

Yes. Use the External Games manager (`Ctrl+Shift+E`) to manage your non-Steam shortcuts. Removing them there removes the Steam shortcut.

### Artwork isn't downloaded for external games

SLM uses SteamGridDB for artwork. Some very niche or new games may not have artwork available there. You can manually add artwork using the Image Browser (`Ctrl+I`).

---

## Performance

### How fast is SLM?

- Cold start (first launch): 10-30 seconds (database build)
- Warm start (subsequent): < 3 seconds
- Category rebuild: < 1 second for 3000 games
- Search: Instant (< 100ms)

### My library has 5000+ games. Will SLM handle it?

Yes. SLM is designed for large libraries. The SQLite database and batch operations are optimized for 3000-5000+ games. Some operations (full enrichment) may take longer, but the UI stays responsive.

### SLM uses a lot of memory

The local SQLite database caches all metadata for fast access. For a library of 3000 games, expect ~25-50 MB of database size and ~100-200 MB of RAM usage. This is normal.

---

## Backup & Data Safety

### Where does SLM store its data?

- Database: `~/.local/share/SteamLibraryManager/steamlibmgr.db`
- Configuration: `~/.config/SteamLibraryManager/`
- Backups: `~/.local/share/SteamLibraryManager/backups/`

### What happens if SLM crashes during a save?

SLM creates a backup of the cloud storage file before every write. If a crash occurs, the backup file remains intact. On next launch, SLM will use the latest valid file.

### Can I sync SLM data between multiple Linux machines?

SLM's collections sync through Steam's cloud storage, so they'll appear on any machine where you log into Steam. The local database (HLTB, ProtonDB, etc.) is per-machine but can be rebuilt quickly via enrichment.

---

## Troubleshooting

### "Permission denied" errors

Make sure SLM has read/write access to your Steam directory. If using Flatpak, ensure the Steam directory is in the Flatpak permissions.

### Collections disappeared after Steam update

Steam occasionally resets cloud storage. Use File → Import → DB Backup to restore from your latest backup, or File → Profiles to load a saved profile.

### The app won't start

Check the log file at `~/.local/share/SteamLibraryManager/steamlibmgr.log` for error details. Common causes: missing Python dependencies, incompatible PyQt6 version, or Steam not installed.

### I found a bug!

Please report it at Help → Online → Report Issues (or directly on GitHub). Include:
1. What you did
2. What you expected
3. What happened instead
4. Your log file (`~/.local/share/SteamLibraryManager/steamlibmgr.log`)

---

*Last updated: February 2026*
*More questions? Visit Help → Online → Discussions*
