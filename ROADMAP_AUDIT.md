# Steam Library Manager - Audit Roadmap (Feb 2026)

> **Ziel:** Diese Datei enthalt ALLE Audit-Funde, sortiert nach Prioritat und Phase.
> Jede KI oder Entwickler kann diese Datei Punkt fur Punkt abarbeiten, ohne etwas auszulassen.
> **Referenz:** Alle Regeln basieren auf `CLAUDE.md` im Projektroot.

---

## Projekt-Ubersicht

- **~16.455 LOC** in ~70 Python-Dateien unter `src/`
- **Architektur:** `src/core/` | `src/services/` | `src/integrations/` | `src/ui/` | `src/utils/`
- **UI Framework:** PyQt6
- **I18n:** Custom `t()` Funktion in `src/utils/i18n.py`
- **Aktive Sprachen:** EN, DE (je ~530 Keys in 3 JSON-Dateien: `main.json`, `date.json`, `emoji.json`)
- **Leere Sprachen:** ES, FR, IT, JA, KO, PT, ZH (Ordner existieren, aber keine Dateien!)

---

# PHASE 0 - CRITICAL (Sofort umsetzen)

> Phase 0 = Showstopper, Bugs, Sicherheit, fehlender Logger, I18N-Verstsse.
> Diese Punkte MUSSEN vor jeder weiteren Arbeit erledigt werden.

---

## 0.1 Zentralen Logger erstellen

**CLAUDE.md Regel:** Phase 0 Deliverable - "Define logging strategy and create central logging utility."
**Problem:** Es existiert KEIN zentraler Logger. Alle ~100+ Log-Ausgaben nutzen `print()`.

### Aufgabe:
1. Erstelle `src/core/logging.py` mit zentralem Logger:
   ```python
   import logging
   logger = logging.getLogger("steamlibmgr")
   ```
2. Konfiguriere Logging-Level, Console-Handler und optionalen File-Handler.
3. Ersetze dann ALLE `print()` Aufrufe (siehe 0.2).

---

## 0.2 ALLE print() durch Logger ersetzen

**CLAUDE.md Regel:** "NO print() in production code. Only in CLI tools/scripts."
**Anzahl:** ~100+ print()-Aufrufe im gesamten Projekt

### Vollstandige Liste aller print()-Aufrufe:

#### src/main.py (15 Aufrufe)
| Zeile | Code | Aktion |
|-------|------|--------|
| 45 | `print(t('logs.main.psutil_missing'))` | `logger.warning(t(...))` |
| 48 | `print(f"Error checking Steam processes: {e}")` | `logger.error(t('logs.main.steam_check_error', error=e))` + neuen i18n Key |
| 80 | `print(t('logs.main.file_load_error', ...))` | `logger.error(t(...))` |
| 113 | `print(f"\n{t('emoji.warning')} {t('logs.main.steam_running_exit')}")` | `logger.info(t(...))` |
| 121 | `print(t('logs.main.profile_setup_required'))` | `logger.info(t(...))` |
| 131 | `print(t('logs.main.profile_configured', ...))` | `logger.info(t(...))` |
| 136 | `print(f"\n{t('logs.main.setup_cancelled')}")` | `logger.info(t(...))` |
| 140 | `print("=" * 60)` | `logger.info("=" * 60)` oder entfernen |
| 141 | `print(t('app.name'))` | `logger.info(t(...))` |
| 142 | `print("=" * 60)` | `logger.info("=" * 60)` oder entfernen |
| 144 | `print(t('logs.main.initializing'))` | `logger.info(t(...))` |
| 147 | `print(t('logs.main.steam_found', ...))` | `logger.info(t(...))` |
| 152 | `print(t('logs.main.steam_not_found'))` | `logger.warning(t(...))` |
| 154 | `print(f"\n{t('common.loading')}\n")` | `logger.info(t(...))` |
| 163 | `print(f"\n{t('common.error')}: {e}")` | `logger.critical(t(...))` |

#### src/config.py (3 Aufrufe)
| Zeile | Code | Aktion |
|-------|------|--------|
| 118 | `print(t('logs.config.load_error', error=e))` | `logger.error(t(...))` |
| 143 | `print(t('logs.config.save_error', error=e))` | `logger.error(t(...))` |
| 203 | `print(f"Error reading libraries: {e}")` | `logger.error(t('logs.config.library_read_error', error=e))` + neuen i18n Key |

#### src/core/game_manager.py (13 Aufrufe)
| Zeile | Code | Aktion |
|-------|------|--------|
| 207 | `print(t('logs.manager.api_trying'))` | `logger.info(t(...))` |
| 214 | `print(t('logs.manager.local_loading'))` | `logger.info(t(...))` |
| 259 | `print(t('logs.manager.error_local', error="No local games found"))` | `logger.warning(t(...))` + i18n fur Parameter |
| 291 | `print(t('logs.manager.loaded_local', count=...))` | `logger.info(t(...))` |
| 295 | `print(t('logs.manager.error_local', error=e))` | `logger.error(t(...))` |
| 319 | `print("Info: No API Key or Access Token configured.")` | `logger.info(t('logs.manager.no_api_key'))` + neuen i18n Key |
| 327 | `print("Using OAuth2 Access Token for Steam API")` | `logger.info(t('logs.manager.using_oauth'))` + neuen i18n Key |
| 338 | `print("Using API Key for Steam API")` | `logger.info(t('logs.manager.using_api_key'))` + neuen i18n Key |
| 353 | `print(t('logs.manager.error_api', error="No games in response"))` | `logger.warning(t(...))` |
| 357 | `print(t('logs.manager.loaded_api', count=...))` | `logger.info(t(...))` |
| 375 | `print(t('logs.manager.error_api', error=e))` | `logger.error(t(...))` |
| 388 | `print(t('logs.manager.merging'))` | `logger.info(t(...))` |
| 590 | `print(t('logs.manager.applied_overrides', count=...))` | `logger.info(t(...))` |

#### src/core/cloud_storage_parser.py (6 Aufrufe)
| Zeile | Code | Aktion |
|-------|------|--------|
| 84 | `print(f"[ERROR] Cloud storage data is not a list!")` | `logger.error(t('logs.parser.not_a_list'))` + neuen i18n Key |
| 100 | `print(f"[WARN] Failed to parse collection: {key}")` | `logger.warning(t('logs.parser.parse_failed', key=key))` + neuen i18n Key |
| 105 | `print(f"[ERROR] Cloud storage file not found: ...")` | `logger.error(t('logs.parser.file_not_found', path=...))` + neuen i18n Key |
| 108 | `print(f"[ERROR] Failed to load cloud storage: {e}")` | `logger.error(t('logs.parser.load_error', error=e))` + neuen i18n Key |
| 209 | `print(t('logs.parser.save_cloud_error'))` | `logger.error(t(...))` |
| 210 | `print(f"[DEBUG] Error details: {e}")` | `logger.debug(t('logs.parser.error_details', error=e))` + neuen i18n Key |

#### src/core/steam_login_manager.py (10 Aufrufe)
| Zeile | Code | Aktion |
|-------|------|--------|
| 139 | `print(t("logs.auth.qr_challenge_approved"))` | `logger.info(t(...))` |
| 146 | `print(t("logs.auth.could_not_resolve_steamid"))` | `logger.warning(t(...))` |
| 402 | `print(t("logs.auth.steamid_resolved"))` | `logger.info(t(...))` |
| 406 | `print(t("logs.auth.steamid_missing"))` | `logger.warning(t(...))` |
| 408 | `print(t("logs.auth.get_owned_games_status", ...))` | `logger.info(t(...))` |
| 411 | `print(t("logs.auth.steamid_from_token_error", ...))` | `logger.error(t(...))` |
| 431 | `print(f"{t('emoji.success')} {t('logs.auth.steamid_from_jwt')}")` | `logger.info(t(...))` |
| 435 | `print(t("logs.auth.jwt_decode_failed", ...))` | `logger.error(t(...))` |
| 462 | `print(t("logs.auth.account_name_resolved"))` | `logger.info(t(...))` |
| 466 | `print(t("logs.auth.account_name_resolve_error", ...))` | `logger.error(t(...))` |

#### src/core/steam_account_scanner.py (16 Aufrufe)
| Zeile | Code | Aktion |
|-------|------|--------|
| 71 | `print(t('logs.scanner.warning_fetch_name', ...))` | `logger.warning(t(...))` |
| 94 | `print(t('logs.scanner.warning_no_userdata', ...))` | `logger.warning(t(...))` |
| 97 | `print(t('logs.scanner.scanning_accounts', ...))` | `logger.info(t(...))` |
| 105 | `print(t('logs.scanner.found_account', ...))` | `logger.info(t(...))` |
| 115 | `print(t('logs.scanner.display_name_found', ...))` | `logger.info(t(...))` |
| 118 | `print(t('logs.scanner.warning_invalid_dir', ...))` | `logger.warning(t(...))` |
| 120 | `print(t('logs.scanner.error_processing', ...))` | `logger.error(t(...))` |
| 124 | `print(t('logs.scanner.total_found', ...))` | `logger.info(t(...))` |
| 140 | `print(t('logs.scanner.warning_no_psutil'))` | `logger.warning(t(...))` |
| 154 | `print(t('logs.scanner.error_check_steam', ...))` | `logger.error(t(...))` |
| 169 | `print(t('logs.scanner.error_no_psutil_kill'))` | `logger.error(t(...))` |
| 180 | `print(t('logs.scanner.killing_steam', ...))` | `logger.info(t(...))` |
| 190 | `print(f"{t('emoji.success')} {t('logs.scanner.steam_closed')}")` | `logger.info(t(...))` |
| 193 | `print(f"{t('emoji.warning')} {t('logs.scanner.steam_still_running')}")` | `logger.warning(t(...))` |
| 196 | `print(t('logs.scanner.no_steam_process'))` | `logger.info(t(...))` |
| 200 | `print(t('logs.scanner.error_kill_steam', ...))` | `logger.error(t(...))` |

#### src/core/steam_assets.py (8 Aufrufe)
| Zeile | Code | Aktion |
|-------|------|--------|
| 138 | `print(f"Unknown asset type: {asset_type}")` | `logger.error(t('logs.assets.unknown_type', type=asset_type))` + neuen i18n Key |
| 150 | `print(t('logs.steamgrid.saved', ...))` | `logger.info(t(...))` |
| 151 | `print(f"  -> Saved to: {target_file}")` | `logger.debug(t('logs.assets.saved_to', path=target_file))` + neuen i18n Key |
| 157 | `print(t('logs.steamgrid.saved', ...))` | `logger.info(t(...))` |
| 158 | `print(f"  -> Saved to: {target_file}")` | `logger.debug(...)` (wie oben) |
| 162 | `print(t('logs.steamgrid.save_error', ...))` | `logger.error(t(...))` |
| 204 | `print(t('logs.steamgrid.deleted', ...))` | `logger.info(t(...))` |
| 209 | `print(t('logs.steamgrid.delete_error', ...))` | `logger.error(t(...))` |

#### src/core/appinfo_manager.py (14 Aufrufe)
| Zeile | Code | Aktion |
|-------|------|--------|
| 82 | `print(t('logs.appinfo.loaded_binary', ...))` | `logger.info(t(...))` |
| 85 | `print(t('logs.appinfo.incompatible_version', ...))` | `logger.error(t(...))` |
| 87 | `print(t('logs.appinfo.binary_error', ...))` | `logger.error(t(...))` |
| 126 | `print(t('logs.appinfo.loaded', ...))` | `logger.info(t(...))` |
| 129 | `print(t('logs.appinfo.error', ...))` | `logger.error(t(...))` |
| 301 | `print(t('logs.appinfo.set_error', ...))` | `logger.error(t(...))` |
| 315 | `print(t('logs.appinfo.saved_mods', ...))` | `logger.info(t(...))` |
| 318 | `print(t('logs.appinfo.error', ...))` | `logger.error(t(...))` |
| 335 | `print(t('logs.appinfo.not_loaded'))` | `logger.warning(t(...))` |
| 345 | `print(t('logs.appinfo.backup_created', ...))` | `logger.info(t(...))` |
| 347 | `print(t('logs.appinfo.backup_failed', ...))` | `logger.error(t(...))` |
| 352 | `print(t('logs.appinfo.saved_vdf'))` | `logger.info(t(...))` |
| 356 | `print(t('logs.appinfo.write_error', ...))` | `logger.error(t(...))` |
| 393 | `print(t('logs.appinfo.restored', ...))` | `logger.info(t(...))` |

#### src/core/backup_manager.py (4 Aufrufe)
| Zeile | Code | Aktion |
|-------|------|--------|
| 70 | `print(t('logs.backup.created', ...))` | `logger.info(t(...))` |
| 77 | `print(t('logs.backup.failed', ...))` | `logger.error(t(...))` |
| 99 | `print(t('logs.backup.rotated', ...))` | `logger.info(t(...))` |
| 101 | `print(t('logs.backup.delete_error', ...))` | `logger.error(t(...))` |

#### src/core/local_games_loader.py (6 Aufrufe)
| Zeile | Code | Aktion |
|-------|------|--------|
| 59 | `print(t('logs.local_loader.loaded_total', ...))` | `logger.info(t(...))` |
| 77 | `print(t('logs.local_loader.scanning_libraries', ...))` | `logger.info(t(...))` |
| 104 | `print(t('logs.local_loader.found_manifests_in_path', ...))` | `logger.info(t(...))` |
| 133 | `print(t('logs.local_loader.no_library_file'))` | `logger.warning(t(...))` |
| 154 | `print(t('logs.local_loader.path_not_exists', ...))` | `logger.warning(t(...))` |
| 157 | `print(t('logs.local_loader.library_error', ...))` | `logger.error(t(...))` |

#### src/core/localconfig_helper.py (3 Aufrufe)
| Zeile | Code | Aktion |
|-------|------|--------|
| 52 | `print(f"[ERROR] LocalConfig file not found: ...")` | `logger.error(t('logs.localconfig.not_found', path=...))` + neuen i18n Key |
| 55 | `print(f"[ERROR] Failed to load localconfig.vdf: {e}")` | `logger.error(t('logs.localconfig.load_error', error=e))` + neuen i18n Key |
| 74 | `print(f"[ERROR] Failed to save localconfig.vdf: {e}")` | `logger.error(t('logs.localconfig.save_error', error=e))` + neuen i18n Key |

#### src/utils/appinfo.py (12 Aufrufe in Produktivcode, + 7 im `__main__` Block)
| Zeile | Code | Aktion |
|-------|------|--------|
| 253 | `print(t('logs.appinfo.parse_error', ...))` | `logger.warning(t(...))` |
| 255 | `print(f"Warning: Failed to parse app ...")` | `logger.warning(t('logs.appinfo.parse_warning', ...))` + neuen i18n Key |
| 347 | `print(t('logs.appinfo.unknown_type', ...))` | `logger.warning(t(...))` |
| 349 | `print(f"Warning: Unknown VDF type ...")` | `logger.warning(t('logs.appinfo.unknown_vdf_type', ...))` + neuen i18n Key |
| 429 | `print(t('logs.appinfo.string_index_out_of_range', ...))` | `logger.warning(t(...))` |
| 432 | `print(f"Warning: String index ...")` | `logger.warning(t('logs.appinfo.string_index_warning', ...))` + neuen i18n Key |
| 487 | `print(t('logs.appinfo.write_error', ...))` | `logger.error(t(...))` |
| 489 | `print(f"Error writing appinfo.vdf: {e}")` | `logger.error(t('logs.appinfo.write_error_detail', error=e))` + neuen i18n Key |
| 490 | `import traceback; traceback.print_exc()` | `logger.exception(...)` |
| 845-867 | `__main__` Block (7x print) | OK - CLI Tool, darf print() nutzen |

#### src/utils/i18n.py (1 Aufruf)
| Zeile | Code | Aktion |
|-------|------|--------|
| 73 | `print(f"Error loading i18n file ...")` | `logger.error(...)` (Achtung: Logger darf hier NICHT t() nutzen - Zirkularitat!) |

#### src/integrations/steamgrid_api.py (3 Aufrufe)
| Zeile | Code | Aktion |
|-------|------|--------|
| 114 | `print(t('logs.steamgrid.api_error', ...))` | `logger.warning(t(...))` |
| 118 | `print(t('logs.steamgrid.exception', ...))` | `logger.error(t(...))` |
| 121 | `print(t('logs.steamgrid.found', ...))` | `logger.info(t(...))` |

#### src/integrations/steam_store.py (3 Aufrufe)
| Zeile | Code | Aktion |
|-------|------|--------|
| 135 | `print(t('logs.steam_store.fetch_error', ...))` | `logger.error(t(...))` |
| 253 | `print(f"Steam API fetch failed for ...")` | `logger.error(t('logs.steam_store.api_fetch_failed', ...))` + neuen i18n Key |
| 375 | `print(f"HTML scraping failed for ...")` | `logger.error(t('logs.steam_store.html_scrape_failed', ...))` + neuen i18n Key |

#### src/services/game_service.py (2 Aufrufe)
| Zeile | Code | Aktion |
|-------|------|--------|
| 71 | `print(f"[ERROR] Failed to init localconfig_helper: {e}")` | `logger.error(t('logs.service.localconfig_init_error', error=e))` + neuen i18n Key |
| 82 | `print(f"[WARN] Failed to initialize Cloud Storage parser: {e}")` | `logger.warning(t('logs.service.cloud_parser_init_error', error=e))` + neuen i18n Key |

#### src/ui/actions/steam_actions.py (5 Aufrufe)
| Zeile | Code | Aktion |
|-------|------|--------|
| 85 | `print(t("logs.auth.qr_login_success"))` | `logger.info(t(...))` |
| 94 | `print(t("logs.auth.password_login_success"))` | `logger.info(t(...))` |
| 100 | `print(t('logs.auth.login_success', ...))` | `logger.info(t(...))` |
| 127 | `print(t("logs.auth.load_games_error", ...))` | `logger.error(t(...))` |
| 135 | `print(t("logs.auth.data_load_handler_missing"))` | `logger.error(t(...))` |

#### src/ui/handlers/data_load_handler.py (5 Aufrufe)
| Zeile | Code | Aktion |
|-------|------|--------|
| 142 | `print(t("logs.auth.loading_games_after_login"))` | `logger.info(t(...))` |
| 146 | `print(t("logs.auth.auth_mode_token"))` | `logger.info(t(...))` |
| 148 | `print(t("logs.auth.auth_mode_session"))` | `logger.info(t(...))` |
| 252 | `print(t('logs.auth.profile_error', ...))` | `logger.error(t(...))` |
| 254 | `print(t("logs.auth.unexpected_profile_error", ...))` | `logger.error(t(...))` |

#### src/ui/steam_modern_login_dialog.py (2 Aufrufe)
| Zeile | Code | Aktion |
|-------|------|--------|
| 335 | `print(f"Failed to convert steam_id to int: ...")` | `logger.error(t('logs.auth.steamid_conversion_error', ...))` + neuen i18n Key |
| 425 | `print(f"Could not add logo to QR code: ...")` | `logger.warning(t('logs.auth.qr_logo_error', ...))` + neuen i18n Key |

#### src/ui/image_selection_dialog.py (1 Aufruf)
| Zeile | Code | Aktion |
|-------|------|--------|
| 220 | `print(t('logs.config.save_error', ...))` | `logger.error(t(...))` |

#### src/ui/widgets/clickable_image.py (3 Aufrufe)
| Zeile | Code | Aktion |
|-------|------|--------|
| 29 | `print(t('logs.image.pillow_missing'))` | `logger.warning(t(...))` |
| 365 | `print(f"[ClickableImage] Pillow load failed ...")` | `logger.debug(t('logs.image.pillow_fallback', error=e))` + neuen i18n Key |
| 430 | `print(f"[ClickableImage] Failed to load WEBM: {e}")` | `logger.debug(t('logs.image.webm_load_failed', error=e))` + neuen i18n Key |

---

## 0.3 ALLE Hardcoded Strings durch t() ersetzen

**CLAUDE.md Regel:** "Hardcoded strings = CRITICAL BUG."

### Neue i18n Keys die erstellt werden mussen (in EN + DE):

| Vorgeschlagener Key | EN Wert | DE Wert | Genutzt in |
|---------------------|---------|---------|------------|
| `logs.main.steam_check_error` | `"Error checking Steam processes: {error}"` | `"Fehler bei Steam-Prozessprüfung: {error}"` | `main.py:48` |
| `logs.config.library_read_error` | `"Error reading libraries: {error}"` | `"Fehler beim Lesen der Bibliotheken: {error}"` | `config.py:203` |
| `logs.manager.no_api_key` | `"No API Key or Access Token configured"` | `"Kein API-Key oder Access Token konfiguriert"` | `game_manager.py:319` |
| `logs.manager.using_oauth` | `"Using OAuth2 Access Token for Steam API"` | `"Verwende OAuth2 Access Token für Steam API"` | `game_manager.py:327` |
| `logs.manager.using_api_key` | `"Using API Key for Steam API"` | `"Verwende API-Key für Steam API"` | `game_manager.py:338` |
| `logs.parser.not_a_list` | `"Cloud storage data is not a list"` | `"Cloud-Storage-Daten sind keine Liste"` | `cloud_storage_parser.py:84` |
| `logs.parser.parse_failed` | `"Failed to parse collection: {key}"` | `"Sammlung konnte nicht geparst werden: {key}"` | `cloud_storage_parser.py:100` |
| `logs.parser.file_not_found` | `"Cloud storage file not found: {path}"` | `"Cloud-Storage-Datei nicht gefunden: {path}"` | `cloud_storage_parser.py:105` |
| `logs.parser.load_error` | `"Failed to load cloud storage: {error}"` | `"Cloud-Storage konnte nicht geladen werden: {error}"` | `cloud_storage_parser.py:108` |
| `logs.parser.error_details` | `"Error details: {error}"` | `"Fehlerdetails: {error}"` | `cloud_storage_parser.py:210` |
| `logs.localconfig.not_found` | `"LocalConfig file not found: {path}"` | `"LocalConfig-Datei nicht gefunden: {path}"` | `localconfig_helper.py:52` |
| `logs.localconfig.load_error` | `"Failed to load localconfig.vdf: {error}"` | `"Fehler beim Laden von localconfig.vdf: {error}"` | `localconfig_helper.py:55` |
| `logs.localconfig.save_error` | `"Failed to save localconfig.vdf: {error}"` | `"Fehler beim Speichern von localconfig.vdf: {error}"` | `localconfig_helper.py:74` |
| `logs.assets.unknown_type` | `"Unknown asset type: {type}"` | `"Unbekannter Asset-Typ: {type}"` | `steam_assets.py:138` |
| `logs.assets.saved_to` | `"Saved to: {path}"` | `"Gespeichert unter: {path}"` | `steam_assets.py:151,158` |
| `logs.service.localconfig_init_error` | `"Failed to init localconfig helper: {error}"` | `"LocalConfig-Helper konnte nicht initialisiert werden: {error}"` | `game_service.py:71` |
| `logs.service.cloud_parser_init_error` | `"Failed to init Cloud Storage parser: {error}"` | `"Cloud-Storage-Parser konnte nicht initialisiert werden: {error}"` | `game_service.py:82` |
| `logs.steam_store.api_fetch_failed` | `"Steam API fetch failed for {app_id}: {error}"` | `"Steam-API-Abruf fehlgeschlagen für {app_id}: {error}"` | `steam_store.py:253` |
| `logs.steam_store.html_scrape_failed` | `"HTML scraping failed for {app_id}: {error}"` | `"HTML-Scraping fehlgeschlagen für {app_id}: {error}"` | `steam_store.py:375` |
| `logs.appinfo.parse_warning` | `"Failed to parse app {app_id}: {error}"` | `"App {app_id} konnte nicht geparst werden: {error}"` | `appinfo.py:255` |
| `logs.appinfo.unknown_vdf_type` | `"Unknown VDF type {type}, skipping"` | `"Unbekannter VDF-Typ {type}, wird übersprungen"` | `appinfo.py:349` |
| `logs.appinfo.string_index_warning` | `"String index {index} out of range (table size: {size})"` | `"String-Index {index} außerhalb des Bereichs (Tabellengröße: {size})"` | `appinfo.py:432` |
| `logs.appinfo.write_error_detail` | `"Error writing appinfo.vdf: {error}"` | `"Fehler beim Schreiben von appinfo.vdf: {error}"` | `appinfo.py:489` |
| `logs.auth.steamid_conversion_error` | `"Failed to convert steam_id to int: {value}, error: {error}"` | `"steam_id konnte nicht in int konvertiert werden: {value}, Fehler: {error}"` | `steam_modern_login_dialog.py:335` |
| `logs.auth.qr_logo_error` | `"Could not add logo to QR code: {error}"` | `"Logo konnte nicht zum QR-Code hinzugefügt werden: {error}"` | `steam_modern_login_dialog.py:425` |
| `logs.image.pillow_fallback` | `"Pillow load failed, falling back to Qt: {error}"` | `"Pillow-Laden fehlgeschlagen, Fallback auf Qt: {error}"` | `clickable_image.py:365` |
| `logs.image.webm_load_failed` | `"Failed to load WEBM: {error}"` | `"WEBM konnte nicht geladen werden: {error}"` | `clickable_image.py:430` |

### Hardcoded Strings in deutschen Ubersetzungen fixen:

| Datei | Zeile | Aktuell | Korrektur |
|-------|-------|---------|-----------|
| `resources/i18n/de/main.json` | 329 | `"...and {count} weitere"` | `"...und {count} weitere"` |
| `resources/i18n/de/main.json` | 566 | `"...and {count} weitere Anderungen"` | `"...und {count} weitere Anderungen"` |

---

## 0.4 Hardcoded Kategorie-Namen durch i18n ersetzen

**Problem:** Kategorie-Namen wie `'Favoriten'`, `'Versteckt'`, `'Uncategorized'` etc. sind direkt im Code hardcoded.

| Datei | Zeile | Hardcoded Strings |
|-------|-------|-------------------|
| `cloud_storage_parser.py` | 38-39 | `'Unkategorisiert'`, `'Uncategorized'`, `'Alle Spiele'`, `'All Games'` |
| `cloud_storage_parser.py` | 45-48 | `'Favoriten'`: `'favorite'`, `'Favorites'`: `'favorite'`, `'Versteckt'`: `'hidden'`, `'Hidden'`: `'hidden'` |
| `game_manager.py` | 405 | `col_name in ['Favoriten', 'Favorites']` |
| `game_manager.py` | 409 | `col_name in ['Versteckt', 'Hidden']` |

**Aktion:** Beide Sprachen uber i18n Keys abfragen, z.B. `t('categories.favorites')`, `t('categories.hidden')`, etc.

---

## 0.5 Undefinierte Attribute im Game Dataclass fixen

**Problem:** Code referenziert Felder die im `Game` Dataclass NICHT existieren.

| Datei | Zeile | Referenz | Status |
|-------|-------|----------|--------|
| `game_manager.py` | 585 | `game.pegi_rating` | EXISTIERT NICHT in Game Dataclass (Zeile 23) |
| `game_manager.py` | 981 | `game.esrb_rating` | EXISTIERT NICHT in Game Dataclass (Zeile 23) |

**Aktion:** Entweder die Felder `pegi_rating: str | None = None` und `esrb_rating: str | None = None` zum Game Dataclass hinzufugen, oder die Referenzen entfernen.

---

## 0.6 Leere Locale-Verzeichnisse behandeln

**Problem:** 7 Sprachen sind in den Settings wahlbar, haben aber KEINE Dateien:
- `resources/i18n/es/` (leer)
- `resources/i18n/fr/` (leer)
- `resources/i18n/it/` (leer)
- `resources/i18n/ja/` (leer)
- `resources/i18n/ko/` (leer)
- `resources/i18n/pt/` (leer)
- `resources/i18n/zh/` (leer)

**Aktion:** Entweder aus den Settings entfernen (`resources/i18n/en/main.json` Zeile 197-206) oder Stub-Dateien erstellen die auf EN fallen.

---

## 0.7 Sicherheitsproblem: Passwort-"Verschlusselung"

**CLAUDE.md Regel:** "Security by default - no secrets in plain text."

| Datei | Zeile | Problem |
|-------|-------|---------|
| `steam_login_manager.py` | 280-290 | `_encrypt_password()` nutzt Base64 statt RSA-Verschlusselung |

**Aktion:** Prufen ob dieses Feature noch genutzt wird. Falls ja: echte RSA-Verschlusselung implementieren.

---

# PHASE 1 - IMPORTANT (Code Quality & Modernisierung)

> Phase 1 = Typ-Modernisierung, fehlende Exporte, Docstrings, Return Types.
> Verbessert IDE-Support, mypy-Kompatibilitat und Wartbarkeit.

---

## 1.1 `from __future__ import annotations` in ALLEN Modulen

**Aktion:** Fuege `from __future__ import annotations` als erste Zeile (nach Docstring) in JEDE Python-Datei ein. Dies ermoglicht `X | None` Syntax auch ohne Python 3.10+.

---

## 1.2 ALLE `Optional[X]` durch `X | None` ersetzen

**CLAUDE.md Regel:** "Optional[str] - write str | None. Shorter and Python 3.10+ standard."

### Vollstandige Liste (88 Stellen):

#### src/config.py (8 Stellen)
- Zeile 43: `STEAM_API_KEY: Optional[str]` -> `str | None`
- Zeile 44: `STEAMGRIDDB_API_KEY: Optional[str]` -> `str | None`
- Zeile 46: `STEAM_PATH: Optional[Path]` -> `Path | None`
- Zeile 47: `STEAM_USER_ID: Optional[str]` -> `str | None`
- Zeile 152: Return `Optional[Path]` -> `Path | None`
- Zeile 207: Return `Tuple[Optional[str], Optional[str]]` -> `tuple[str | None, str | None]`
- Zeile 220: Return `Optional[Path]` -> `Path | None`
- Zeile 12: Entferne `Optional, Tuple` aus typing Import

#### src/core/game_manager.py (8 Stellen)
- Zeile 35: `last_played: Optional[datetime]` -> `datetime | None`
- Zeile 158: `steam_api_key: Optional[str]` -> `str | None`
- Zeile 174: `self.steam_user_id: Optional[str]` -> `str | None`
- Zeile 182: `progress_callback: Optional[Callable[...]]` -> `Callable[...] | None`
- Zeile 236: `progress_callback: Optional[Callable]` -> `Callable | None`
- Zeile 485: Return `Optional[str]` -> `str | None`
- Zeile 592: Return `Optional[Game]` -> `Game | None`
- Zeile 16: Entferne `Optional` aus typing Import

#### src/core/steam_login_manager.py (8 Stellen)
- Zeile 115: Return `Optional[Dict]` -> `dict[str, Any] | None`
- Zeile 246: Return `Optional[Dict]` -> `dict[str, Any] | None`
- Zeile 317: `self.qr_thread: Optional[QRCodeLoginThread]` -> `QRCodeLoginThread | None`
- Zeile 318: `self.pwd_thread: Optional[...]` -> `... | None`
- Zeile 375: Return `Optional[str]` -> `str | None`
- Zeile 440: Return `Optional[str]` -> `str | None`
- Zeile 471: Return `Optional[Dict]` -> `dict[str, Any] | None`
- Zeile 13: Entferne `Optional` aus typing Import

#### src/core/appinfo_manager.py (6 Stellen)
- Zeile 27: `steam_path: Optional[Path]` -> `Path | None`
- Zeile 44: `self.appinfo: Optional[AppInfo]` -> `AppInfo | None`
- Zeile 45: `self.appinfo_path: Optional[Path]` -> `Path | None`
- Zeile 53: `_app_ids: Optional[List[str]]` -> `list[str] | None`
- Zeile 361: `app_ids: Optional[List[str]]` -> `list[str] | None`
- Zeile 13: Entferne `Optional` aus typing Import

#### src/core/backup_manager.py (3 Stellen)
- Zeile 27: `backup_dir: Optional[Path]` -> `Path | None`
- Zeile 38: Return `Optional[Path]` -> `Path | None`
- Zeile 104: Return `Optional[str]` -> `str | None`

#### src/core/steam_account.py (1 Stelle)
- Zeile 24: `avatar_url: Optional[str]` -> `str | None`

#### src/core/local_games_loader.py (1 Stelle)
- Zeile 162: Return `Optional[Dict]` -> `dict[str, Any] | None`

#### src/utils/i18n.py (1 Stelle)
- Zeile 114: `_i18n_instance: Optional[I18n]` -> `I18n | None`

#### src/utils/appinfo.py (3 Stellen)
- Zeile 132: `path: Optional[str]` -> `str | None`
- Zeile 442: `output_path: Optional[str]` -> `str | None`
- Zeile 729: Return `Optional[Dict]` -> `dict[str, Any] | None`

#### src/integrations/steam_store.py (6 Stellen)
- Zeile 139, 192, 256: Return `Optional[str]` -> `str | None`
- Zeile 379: Return `Optional[str]` -> `str | None`
- Zeile 460: Return `Optional[str]` -> `str | None`
- Zeile 15: Entferne `Optional` aus typing Import

#### src/integrations/steamgrid_api.py (5 Stellen)
- Zeile 35: Return `Dict[str, Optional[str]]` -> `dict[str, str | None]`
- Zeile 124: Return `Optional[int]` -> `int | None`
- Zeile 145: `params: Optional[Dict[str, Any]]` -> `dict[str, Any] | None`, Return `Optional[str]` -> `str | None`
- Zeile 10: Entferne `Optional` aus typing Import

#### src/services/*.py (12 Stellen)
- `game_service.py` Zeile 44-47: 4x `Optional[...]` -> `... | None`
- `game_service.py` Zeile 87: `Optional[Callable]` -> `Callable | None`
- `game_service.py` Zeile 149: Return `Optional[CloudStorageParser]` -> `CloudStorageParser | None`
- `category_service.py` Zeile 27-28: 2x `Optional[...]` -> `... | None`
- `metadata_service.py` Zeile 35, 73, 98: 3x `Optional[...]` -> `... | None`
- `autocategorize_service.py` Zeile 30, 50, 96, 138, 184: 5x `Optional[Callable]` -> `Callable | None`
- `asset_service.py` Zeile 29: `Optional[SteamGridDB]` -> `SteamGridDB | None`

#### src/ui/*.py (25+ Stellen)
- `main_window.py` Zeile 83-91: 9x `Optional[...]` -> `... | None`
- `main_window.py` Zeile 106, 109, 113: 3x `Optional[...]` -> `... | None`
- `steam_modern_login_dialog.py` Zeile 43-44, 53-54: 4x `Optional[...]` -> `... | None`
- `auto_categorize_dialog.py` Zeile 39, 56, 276: 3x `Optional[...]` -> `... | None`
- `metadata_dialogs.py` Zeile 36, 310, 473: 3x `Optional[...]` -> `... | None`
- `ui_helper.py` Zeile 20, 35, 50, 65, 80: 5x `Optional[str]` -> `str | None`
- `dialog_helpers.py` Zeile 54, 104, 221: 3x `Optional[...]` -> `... | None`
- `handlers/data_load_handler.py` Zeile 47-48, 108: 3x
- `handlers/empty_collection_handler.py` Zeile 27: 1x
- `dialogs/profile_setup_dialog.py` Zeile 66-67, 287: 3x
- `actions/edit_actions.py` Zeile 96: 1x
- `actions/tools_actions.py` Zeile 72: 1x
- `widgets/category_tree.py` Zeile 39, 70: 2x
- `utils/qt_utils.py` Zeile 28: 1x

---

## 1.3 ALLE Old-Style Generics durch lowercase ersetzen

**CLAUDE.md Regel:** Moderner Python 3.10+ Style.

### Dateien mit `from typing import List, Dict, Tuple` (35 Dateien):

| Datei | Zu ersetzen |
|-------|-------------|
| `src/config.py:12` | `List` -> `list`, `Tuple` -> `tuple` |
| `src/core/game_manager.py:16` | `Dict` -> `dict`, `List` -> `list`, `Callable` bleibt |
| `src/core/cloud_storage_parser.py:27` | `Dict` -> `dict`, `List` -> `list` |
| `src/core/steam_login_manager.py:13` | `Dict` -> `dict` |
| `src/core/steam_account_scanner.py:8` | `List` -> `list` |
| `src/core/localconfig_helper.py:15` | `List` -> `list`, `Dict` -> `dict` |
| `src/core/local_games_loader.py:13` | `List` -> `list`, `Dict` -> `dict` |
| `src/core/appinfo_manager.py:13` | `Dict` -> `dict`, `List` -> `list` |
| `src/utils/i18n.py:7` | `Dict` -> `dict` |
| `src/utils/appinfo.py:21` | `Dict` -> `dict`, `List` -> `list` |
| `src/utils/manifest.py:11` | `Dict` -> `dict` |
| `src/integrations/steam_store.py:15` | `List` -> `list` |
| `src/integrations/steamgrid_api.py:10` | `Dict` -> `dict`, `List` -> `list` |
| `src/services/category_service.py:11` | `List` -> `list`, `Dict` -> `dict` |
| `src/services/search_service.py:2` | `List` -> `list` |
| `src/services/autocategorize_service.py:15` | `List` -> `list`, `Dict` -> `dict` |
| `src/services/metadata_service.py:13` | `Dict` -> `dict`, `List` -> `list` |
| `src/ui/main_window.py:9` | `List` -> `list` |
| `src/ui/game_details_widget.py:20` | `List` -> `list` |
| `src/ui/auto_categorize_dialog.py:16` | `List` -> `list`, `Dict` -> `dict` |
| `src/ui/metadata_dialogs.py:15` | `Dict` -> `dict`, `List` -> `list` |
| `src/ui/settings_dialog.py:11` | `Dict` -> `dict` |
| `src/ui/missing_metadata_dialog.py:17` | `List` -> `list` |
| `src/ui/actions/steam_actions.py:11` | `Dict` -> `dict` |
| `src/ui/actions/settings_actions.py:10` | `Dict` -> `dict` |
| `src/ui/actions/edit_actions.py:14` | `List` -> `list` |
| `src/ui/handlers/category_action_handler.py:19` | `List` -> `list` |
| `src/ui/handlers/selection_handler.py:16` | `List` -> `list` |
| `src/ui/handlers/category_change_handler.py:15` | `List` -> `list` |
| `src/ui/widgets/ui_helper.py:9` | `Tuple` -> `tuple` |
| `src/ui/widgets/category_tree.py:10` | `Dict` -> `dict`, `List` -> `list` |
| `src/ui/builders/central_widget_builder.py:8` | `Dict` -> `dict` |
| `src/ui/utils/ui_helpers.py:7` | `Tuple` -> `tuple` |
| `src/ui/utils/dialog_helpers.py:7` | `List` -> `list` |
| `src/ui/utils/qt_utils.py:7` | `List` -> `list` |

**Aktion:** Nach Einfugen von `from __future__ import annotations` konnen ALLE Old-Style Generics durch lowercase ersetzt und die Imports aus `typing` entfernt werden.

---

## 1.4 Fehlende `__all__` Definitionen hinzufugen

**CLAUDE.md Regel:** "Define __all__ in every module - explicit is better than implicit."

### Module die `__all__` HABEN (OK):
- `src/utils/acf.py` ✓
- `src/utils/appinfo.py` ✓
- `src/utils/manifest.py` ✓
- `src/ui/workers/__init__.py` ✓
- `src/ui/builders/__init__.py` ✓
- `src/ui/actions/__init__.py` ✓
- `src/ui/widgets/__init__.py` ✓
- `src/ui/handlers/__init__.py` ✓
- `src/ui/utils/__init__.py` ✓

### Module die `__all__` BRAUCHEN:

| Datei | Vorgeschlagener Export |
|-------|----------------------|
| `src/main.py` | `__all__ = ['main']` |
| `src/config.py` | `__all__ = ['Config', 'config']` |
| `src/version.py` | `__all__ = ['VERSION']` |
| `src/core/__init__.py` | `__all__: list[str] = []` |
| `src/core/game_manager.py` | `__all__ = ['Game', 'GameManager']` |
| `src/core/cloud_storage_parser.py` | `__all__ = ['CloudStorageParser']` |
| `src/core/steam_login_manager.py` | `__all__ = ['SteamLoginManager', 'QRCodeLoginThread', 'UsernamePasswordLoginThread']` |
| `src/core/appinfo_manager.py` | `__all__ = ['AppInfoManager']` |
| `src/core/backup_manager.py` | `__all__ = ['BackupManager']` |
| `src/core/localconfig_helper.py` | `__all__ = ['LocalConfigHelper']` |
| `src/core/local_games_loader.py` | `__all__ = ['LocalGamesLoader']` |
| `src/core/non_game_apps.py` | `__all__ = ['NON_GAME_APP_IDS', 'is_real_game']` |
| `src/core/steam_account.py` | `__all__ = ['SteamAccount']` |
| `src/core/steam_account_scanner.py` | `__all__ = ['scan_steam_accounts', 'is_steam_running', 'kill_steam_process', 'STEAM_ID_BASE']` |
| `src/core/steam_assets.py` | `__all__ = ['SteamAssets']` |
| `src/services/__init__.py` | `__all__: list[str] = []` |
| `src/services/game_service.py` | `__all__ = ['GameService']` |
| `src/services/category_service.py` | `__all__ = ['CategoryService']` |
| `src/services/autocategorize_service.py` | `__all__ = ['AutoCategorizeService']` |
| `src/services/metadata_service.py` | `__all__ = ['MetadataService']` |
| `src/services/asset_service.py` | `__all__ = ['AssetService']` |
| `src/services/search_service.py` | `__all__ = ['SearchService']` |
| `src/integrations/__init__.py` | `__all__: list[str] = []` |
| `src/integrations/steamgrid_api.py` | `__all__ = ['SteamGridDB']` |
| `src/integrations/steam_store.py` | `__all__ = ['SteamStoreScraper']` |
| `src/utils/__init__.py` | `__all__: list[str] = []` |
| `src/utils/i18n.py` | `__all__ = ['I18n', 'init_i18n', 't']` |
| `src/utils/date_utils.py` | `__all__ = ['parse_date_to_timestamp', 'format_timestamp_to_date']` |

---

## 1.5 Fehlende Return-Type-Hints hinzufugen

| Datei | Zeile | Methode | Fehlender Typ |
|-------|-------|---------|---------------|
| `main_window.py` | 433 | `_get_active_parser(self)` | `-> CloudStorageParser \| None` |
| `main_window.py` | 491 | `_add_app_category(self, ...)` | `-> None` |
| `main_window.py` | 496 | `_remove_app_category(self, ...)` | `-> None` |
| `main_window.py` | 501 | `_rename_category(self, ...)` | `-> None` |
| `main_window.py` | 509 | `_delete_category(self, ...)` | `-> None` |
| `main_window.py` | 339 | `on_game_right_click(self, game, pos)` | `pos: QPoint` + `-> None` |
| `main_window.py` | 350 | `on_category_right_click(self, category, pos)` | `pos: QPoint` + `-> None` |
| `main_window.py` | 412 | `closeEvent(self, event)` | `event: QCloseEvent` + `-> None` |
| `main_window.py` | 522 | `keyPressEvent(self, event)` | `event: QKeyEvent` + `-> None` |
| `category_service.py` | 42 | `get_active_parser(self)` | `-> CloudStorageParser \| None` |
| `acf.py` | 16 | `loads(data)` | `data: str` + `-> dict[str, Any]` |
| `acf.py` | 61 | `load(filename)` | `filename: str` + `-> dict[str, Any]` |
| `acf.py` | 109 | `_prepare_subsection(data)` | `data: dict` + `-> dict[str, Any]` |

---

## 1.6 Fehlende Docstrings hinzufugen

**CLAUDE.md Regel:** "Every public method gets a docstring."

| Datei | Zeile | Methode |
|-------|-------|---------|
| `game_details_widget.py` | 263 | `_create_ui()` |
| `game_details_widget.py` | 687 | `clear()` |
| `game_details_widget.py` | 704 | `_on_pegi_clicked()` |
| `game_details_widget.py` | 722 | `_on_pegi_right_click()` |
| `game_details_widget.py` | 760 | `_on_edit()` |
| `game_details_widget.py` | 765 | `_open_current_store()` |
| `settings_dialog.py` | 236 | `_load_current_settings()` |
| `settings_dialog.py` | 260 | `_browse_steam_path()` |
| `settings_dialog.py` | 266 | `_add_library()` |
| `settings_dialog.py` | 276 | `_remove_library()` |
| `auto_categorize_dialog.py` | 67 | `_center_on_parent()` |
| `auto_categorize_dialog.py` | 76 | `_create_ui()` |

---

# PHASE 2 - MODERATE (Architektur & Refactoring)

> Phase 2 = Architektur-Verstsse, Dateien >500 Zeilen, Dataclass-Compliance.
> Sollte nach Phase 0 und 1 angegangen werden.

---

## 2.1 QMessageBox aus Service-Layer entfernen

**CLAUDE.md Regel:** "Domain logic before UI; services decoupled."

| Datei | Zeile | Problem |
|-------|-------|---------|
| `category_service.py` | 143-153 | `check_empty_collection()` erzeugt `QMessageBox` im Service |

**Aktion:** Service soll nur `bool` zuruckgeben. UI-Layer (Handler/Action) zeigt die MessageBox.

---

## 2.2 Dataclasses auf `frozen=True` prufen

**CLAUDE.md Regel:** "@dataclass(frozen=True) or NamedTuple for all data containers."

| Datei | Zeile | Klasse | Aktuell | Aktion |
|-------|-------|--------|---------|--------|
| `steam_account.py` | 11 | `SteamAccount` | `@dataclass` (nicht frozen) | `@dataclass(frozen=True)` |
| `config.py` | 22 | `Config` | `@dataclass` (nicht frozen) | Prufen ob frozen moglich (hat `save()` Methode, daher evtl. nicht frozen) |
| `game_manager.py` | 23 | `Game` | `@dataclass` (nicht frozen) | Prufen ob frozen moglich (wird durch `__post_init__` mutiert) |

**Hinweis:** `Config` und `Game` haben mutable State. Hier muss bewertet werden ob `frozen=True` realistisch ist oder ob eine Begrundung im Code dokumentiert wird.

---

## 2.3 Dateien uber 500 Zeilen (Refactoring-Kandidaten)

**CLAUDE.md Regel:** "Flag files >500 lines and propose modular splits."

| Datei | LOC | Vorgeschlagener Split |
|-------|-----|----------------------|
| `game_manager.py` | 1078 | `Game` Dataclass -> `src/core/game.py`, Fetch-Methoden -> `src/core/game_fetcher.py`, Statistics -> `src/core/game_statistics.py` |
| `appinfo.py` | 867 | Utility-Datei, akzeptabel aber gross. Parser + Writer konnten getrennt werden. |
| `game_details_widget.py` | 818 | `InfoLabel` + `HorizontalCategoryList` -> `src/ui/widgets/info_widgets.py` |
| `clickable_image.py` | 656 | `ImageLoader` -> `src/ui/workers/image_loader.py` |
| `metadata_dialogs.py` | 556 | 3 Klassen -> je eigene Datei in `src/ui/dialogs/` |
| `main_window.py` | 536 | Knapp uber Limit. Delegate-Methoden (491-522) konnten in Handler extrahiert werden. |

---

## 2.4 i18n Consistency Check in CI

**CLAUDE.md Regel:** Phase 0 Deliverable - "i18n consistency check in CI."

**Aktion:** Script erstellen das:
1. Alle Keys in EN und DE vergleicht
2. Fehlende Keys meldet
3. Leere Werte meldet
4. In `.github/workflows/test.yml` als CI-Step einbinden

---

## 2.5 `typing.List` Import-Reste entfernen

Nach Abschluss von 1.1-1.3 sicherstellen, dass KEINE `from typing import List, Dict, Tuple, Optional` Imports mehr existieren (ausser `TYPE_CHECKING`, `Callable`, `Any`, `BinaryIO` die weiterhin benotigt werden).

**Validierung:**
```bash
grep -r "from typing import.*\b(List|Dict|Tuple|Optional)\b" src/ --include="*.py"
```
Muss 0 Ergebnisse liefern.

---

## 2.6 `# type: ignore` Audit

**CLAUDE.md Regel:** "Every ignore needs a comment explaining why."

| Datei | Zeile | Aktuell | Aktion |
|-------|-------|---------|--------|
| `manifest_pb2.py` | 4 | `# type: ignore` | OK - generierter Code |

**Status:** Aktuell sauber. Bei zukunftigen Anderungen drauf achten.

---

## 2.7 Smoke-Compile Test in CI

**CLAUDE.md Regel:** Phase 0 Deliverable.

**Aktion:** In `.github/workflows/test.yml` hinzufugen:
```yaml
- name: Smoke compile
  run: python -c "import src.main"
```
Stellt sicher, dass keine Import-Fehler oder Zirkularitaten existieren.

---

# CHECKLISTE

## Phase 0 Checkliste:
- [ ] 0.1 Zentralen Logger (`src/core/logging.py`) erstellen
- [ ] 0.2 ALLE ~100+ print() Aufrufe durch Logger ersetzen
- [ ] 0.3 ALLE ~26 neuen i18n Keys in EN + DE erstellen
- [ ] 0.3b Hardcoded English in DE-Ubersetzungen fixen (2 Stellen)
- [ ] 0.4 Hardcoded Kategorie-Namen durch i18n ersetzen
- [ ] 0.5 Undefinierte Game-Attribute fixen (pegi_rating, esrb_rating)
- [ ] 0.6 Leere Locale-Verzeichnisse behandeln
- [ ] 0.7 Passwort-Verschlusselung prufen

## Phase 1 Checkliste:
- [ ] 1.1 `from __future__ import annotations` in alle Module
- [ ] 1.2 ALLE 88+ `Optional[X]` -> `X | None`
- [ ] 1.3 ALLE 35 Dateien: Old-Style Generics -> lowercase
- [ ] 1.4 `__all__` in 28 Modulen hinzufugen
- [ ] 1.5 13 fehlende Return-Type-Hints hinzufugen
- [ ] 1.6 12 fehlende Docstrings hinzufugen

## Phase 2 Checkliste:
- [ ] 2.1 QMessageBox aus category_service.py entfernen
- [ ] 2.2 Dataclasses auf frozen=True prufen
- [ ] 2.3 Dateien >500 LOC splitten (6 Kandidaten)
- [ ] 2.4 i18n Consistency Check Script + CI
- [ ] 2.5 typing-Import Reste validieren
- [ ] 2.6 type: ignore Audit
- [ ] 2.7 Smoke-Compile Test in CI
