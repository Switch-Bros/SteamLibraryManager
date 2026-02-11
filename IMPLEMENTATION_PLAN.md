# Steam Library Manager – Technischer Umsetzungsplan (Linux-first, Depressurizer++)

Dieser Plan ist auf **schnelle Iteration**, **hohe Stabilität** und **klare PR-Schritte** ausgelegt.

---

## Ziele

1. **Login ohne API-Key Copy/Paste** stabil und sicher machen.
2. **Schneller Start** durch lokale Datenbank statt vollem `appinfo.vdf` Parse bei jedem Start.
3. **Collections als Source of Truth** aus `cloud-storage-namespace-1.json` sauber verwalten.
4. **Depressurizer-Parität + Mehrwert** (Linux-first UX, Automatisierung, bessere Performance).

---

## Leitprinzipien

- **Linux-first, Windows-second** (keine Blocker für Linux-Features).
- **Security by default** (keine sensitiven Secrets im Klartext speichern).
- **Fast boot** (UI sofort, Daten async nachladen).
- **Small PRs** (jede PR einzeln testbar, rollback-fähig).
- **Domain vor UI** (Businesslogik von Qt trennen).

---

## Architektur-Zielbild

### Neue Kernkomponenten

- `src/core/db/metadata_db.py`
  - SQLite-Zugriff, Schema-Migrationen, Indizes.
- `src/core/db/repositories.py`
  - Typed Read/Write-Methoden für Apps, Overrides, Collections.
- `src/core/sync/appinfo_sync.py`
  - Inkrementelles Synchronisieren von `appinfo.vdf` in DB.
- `src/core/sync/cloud_sync.py`
  - Import/Export + Konfliktbehandlung für Cloud-Collections.
- `src/core/auth/token_store.py`
  - Sichere lokale Speicherung von Tokens (Keyring/Fallback-Policy).
- `src/services/bootstrap_service.py`
  - Orchestriert Startup-Pipeline (fast boot + async enrichment).

### Refactor-Ziele bestehender Module

- `src/core/game_manager.py`
  - API/Cache/Enrichment in spezialisierte Services aufteilen.
- `src/core/appinfo_manager.py`
  - Nur VDF-nahe Funktionen behalten; Datenzugriff in DB-Repos.
- `src/services/game_service.py`
  - Auf Bootstrap + Repository-Layer umstellen.
- `src/services/category_service.py`
  - UI-Dialog-Logik entkoppeln, reine Domain-Operationen.

---

## Geplantes DB-Schema (SQLite)

### Tabelle `apps`

- `app_id TEXT PRIMARY KEY`
- `name TEXT`
- `sort_name TEXT`
- `developer TEXT`
- `publisher TEXT`
- `release_date TEXT`
- `review_percentage INTEGER`
- `metacritic_score INTEGER`
- `last_updated TEXT`
- `source_hash TEXT`
- `updated_at INTEGER`

### Tabelle `overrides`

- `app_id TEXT PRIMARY KEY`
- `name_override TEXT`
- `sort_override TEXT`
- `developer_override TEXT`
- `publisher_override TEXT`
- `release_override TEXT`
- `pegi_override TEXT`
- `updated_at INTEGER`

### Tabelle `collections`

- `id TEXT`
- `name TEXT`
- `app_id TEXT`
- `is_special INTEGER`
- `source TEXT` (`cloud` | `local`)
- `updated_at INTEGER`
- `PRIMARY KEY (name, app_id)`

### Tabelle `sync_state`

- `key TEXT PRIMARY KEY`
- `value TEXT`

Beispiele:
- `appinfo_mtime`
- `appinfo_size`
- `cloud_mtime`
- `schema_version`

---

## Detaillierte PR-Reihenfolge (empfohlen)

## PR 1 – Infrastruktur & DB-Grundlage

**Ziel:** Datenbank einführen ohne Verhalten zu brechen.

### Änderungen
- Neue Module:
  - `src/core/db/metadata_db.py`
  - `src/core/db/repositories.py`
  - `tests/unit/test_core/test_metadata_db.py`
- Config-Erweiterung:
  - DB-Pfad in `src/config.py` (z. B. `data/metadata.db`).

### Akzeptanzkriterien
- DB wird beim Start erzeugt.
- Migrationen laufen idempotent.
- Unit-Tests für Schema + CRUD grün.

---

## PR 2 – AppInfo inkrementell synchronisieren

**Ziel:** Kein Full-Parse mehr bei jedem Start.

### Änderungen
- Neues Modul:
  - `src/core/sync/appinfo_sync.py`
- Refactor:
  - `src/core/appinfo_manager.py` (Parser nur on-demand)
  - `src/services/game_service.py` (DB zuerst lesen)

### Strategie
- Bei Start: mtime/size/hash prüfen.
- Nur bei Änderung: parse/sync.
- UI liest sofort aus DB, Enrichment im Hintergrund.

### Akzeptanzkriterien
- Startzeit deutlich besser bei unveränderter `appinfo.vdf`.
- Funktionale Gleichheit für sichtbare Metadaten.

---

## PR 3 – Collections sauber auf Cloud Source of Truth

**Ziel:** Einheitliche Collections-Logik über Cloud JSON.

### Änderungen
- Neues Modul:
  - `src/core/sync/cloud_sync.py`
- Refactor:
  - `src/core/cloud_storage_parser.py`
  - `src/services/category_service.py`

### Inhalt
- Read/Write-Transaktionen mit Backup.
- Konfliktstrategie (Last-write-wins + optional Merge-Hooks).
- Sonderkategorien (`Favorites`, `Hidden`) konsistent behandeln.

### Akzeptanzkriterien
- Kategorien bleiben nach Steam-Neustart stabil.
- Keine Duplikate/inkonsistente IDs nach Rename/Merge.

---

## PR 4 – Auth-Härtung (sicher + bequem)

**Ziel:** Login ohne API-Key robust und sicher.

### Änderungen
- Neues Modul:
  - `src/core/auth/token_store.py`
- Refactor:
  - `src/core/steam_login_manager.py`
  - `src/ui/actions/steam_actions.py`
  - `src/config.py` (keine sensitiven Tokens in JSON persistieren)

### Inhalt
- Access/Refresh Tokens im sicheren Store.
- Session Refresh, Logout, Token-Revoke-Flow.
- Unsicheren Platzhalter für Passwort-Encryption entfernen/ersetzen.

### Akzeptanzkriterien
- Login über Neustart hinweg stabil.
- Keine Secrets im Klartext-Settingsfile.

---

## PR 5 – GameManager zerlegen (Wartbarkeit)

**Ziel:** Große Klasse entkoppeln.

### Änderungen
- Neue Module:
  - `src/services/enrichment/store_enrichment_service.py`
  - `src/services/enrichment/review_enrichment_service.py`
  - `src/services/enrichment/proton_enrichment_service.py`
- Refactor:
  - `src/core/game_manager.py`

### Akzeptanzkriterien
- Öffentliche APIs kompatibel oder klar migriert.
- Testabdeckung für neue Services vorhanden.

---

## PR 6 – UI Bootstrap für Fast Boot

**Ziel:** Schnell sichtbare UI, Daten kommen progressiv.

### Änderungen
- Neues Modul:
  - `src/services/bootstrap_service.py`
- Refactor:
  - `src/ui/main_window.py`
  - `src/ui/handlers/data_load_handler.py`
  - `src/ui/workers/game_load_worker.py`

### Inhalt
- Skeleton/Placeholder-Ladezustände.
- Progressives Rendern nach Kategorien/Chunks.
- Fehlerzustände nutzerfreundlich darstellen.

### Akzeptanzkriterien
- App reagiert sofort nach Start.
- Lange Netzwerk-/Parse-Jobs blockieren UI nicht.

---

## PR 7 – Depressurizer-Parität + Plus

**Ziel:** Feature-Parität und Differenzierungsfeatures.

### Änderungen
- Regelbasierte Auto-Kategorisierung erweitern:
  - `src/services/autocategorize_service.py`
- Neue Rule-Engine:
  - `src/services/rules/rule_engine.py`
  - `src/services/rules/rule_types.py`
- UI-Dialoge für Rules/Presets:
  - `src/ui/auto_categorize_dialog.py`

### Plus-Features
- Presets pro Gerät (Deck/Desktop)
- Bulk-Operationen nach Rule-Preview
- Dry-run + Undo-Stack

---

## Teststrategie (pro PR)

- Unit-Tests für neue Kernlogik.
- Contract-Tests für Parser/Sync.
- Smoke-Tests für Startup-Flow.
- Optional später: E2E-UI-Tests (Playwright/PyQt-Events).

### Wichtige neue Testdateien

- `tests/unit/test_core/test_metadata_db.py`
- `tests/unit/test_core/test_appinfo_sync.py`
- `tests/unit/test_core/test_cloud_sync.py`
- `tests/unit/test_auth/test_token_store.py`
- `tests/unit/test_services/test_bootstrap_service.py`

---

## Migrations- und Rollout-Plan

1. **Versioniertes Schema** (`schema_version` in `sync_state`).
2. **One-way Migration** von JSON-Metadaten nach DB.
3. **Fallback-Pfad**: bei DB-Fehler read-only aus alten Quellen.
4. **Backup vor write** für `cloud-storage-namespace-1.json` und `appinfo.vdf`.

---

## Performance-Ziele (messbar)

- Cold start (ohne DB): baseline dokumentieren.
- Warm start (mit DB): Ziel >50% schneller.
- Kategorie-Render für große Libraries: <200 ms für initiale Sicht.
- Hintergrund-Enrichment mit Rate-Limit + Retry.

---

## Security-Ziele

- Keine Access/Refresh-Tokens im Klartext speichern.
- Keine Passwort-Workarounds mit Base64-"Encryption".
- Logging ohne Sensitive Data Leaks.

---

## Quick Wins (direkt umsetzbar)

1. `CategoryService` von UI-Dialogen trennen (saubere Domain-API).
2. Zentrales Logging statt verteilter `print`/silent `pass`.
3. Test-Mismatch bereinigen (`LocalConfigParser` vs `LocalConfigHelper`).
4. Startup: zuerst DB laden, dann Netzwerk/Parser asynchron.

---

## Ergebnisbild nach Phase 1

- Login bequem ohne API-Key-Manuell.
- App startet schnell und fühlt sich sofort responsiv an.
- Collections sind robust mit dem realen Steam-Cloud-Format.
- Solide Basis für Depressurizer-Parität + Linux-first Zusatzfeatures.

