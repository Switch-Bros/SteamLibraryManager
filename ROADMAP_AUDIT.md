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
