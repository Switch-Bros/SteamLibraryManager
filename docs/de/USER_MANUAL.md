# 📖 Steam Library Manager — Benutzerhandbuch

**Version:** 1.0
**Plattform:** Linux (CachyOS, Ubuntu, Fedora, Arch, SteamOS, etc.)

---

## Inhaltsverzeichnis

1. [Was ist Steam Library Manager?](#was-ist-steam-library-manager)
2. [Installation](#installation)
3. [Erster Start](#erster-start)
4. [Hauptfenster](#hauptfenster)
5. [Sammlungen verwalten](#sammlungen-verwalten)
6. [Smart Collections](#smart-collections)
7. [Auto-Kategorisierung](#auto-kategorisierung)
8. [Daten-Enrichment](#daten-enrichment)
9. [Externe Spiele](#externe-spiele)
10. [Import & Export](#import--export)
11. [Profile & Backup](#profile--backup)
12. [Ansichtsfilter & Sortierung](#ansichtsfilter--sortierung)
13. [Einstellungen](#einstellungen)
14. [Tastenkürzel](#tastenkürzel)
15. [Problemlösung](#problemlösung)

---

## Was ist Steam Library Manager?

Steam Library Manager (SLM) ist ein leistungsstarkes Werkzeug zur Organisation großer Steam-Spielebibliotheken unter Linux. Stell es dir als moderne, Linux-native Alternative zu Depressurizer vor — mit Extras.

**Hauptfunktionen:**
- 3000+ Spiele in Sammlungen organisieren, die mit Steam synchronisiert werden
- 15+ automatische Kategorisierungstypen (Genre, Tags, Spielzeit, HLTB und mehr)
- Smart Collections mit UND/ODER/NICHT-Logik (was Steam selbst nicht kann)
- Datenanreicherung von HLTB, ProtonDB und Steam-Deck-Kompatibilität
- Nicht-Steam-Spiele von Epic, GOG, Lutris und 5 weiteren Plattformen verwalten
- Vollständiger Import/Export-Support (CSV, VDF, JSON)

**Was unterscheidet SLM von Depressurizer?**
- Linux-first (Flatpak, AppImage)
- Smart Collections mit ODER-Logik (Depressurizer und Steam können nur UND)
- ProtonDB- und Steam-Deck-Integration
- HLTB-Daten direkt in der Bibliothek
- Verwaltung externer Spiele (8 Plattform-Parser)
- Moderne SQLite-Datenbank für schnelle Performance

---

## Installation

### Flatpak (Empfohlen)

```bash
flatpak install flathub com.github.steamlibmgr.SteamLibraryManager
```

### AppImage

1. Lade das neueste `.AppImage` von der [GitHub Releases](https://github.com/HeikesFootSlave/SteamLibraryManager/releases)-Seite herunter
2. Mach es ausführbar: `chmod +x SteamLibraryManager-*.AppImage`
3. Starte es: `./SteamLibraryManager-*.AppImage`

### Aus Quellcode

```bash
git clone https://github.com/HeikesFootSlave/SteamLibraryManager.git
cd SteamLibraryManager
pip install -r requirements.txt
python -m src.main
```

Erfordert Python 3.11+ und PyQt6.

---

## Erster Start

Beim ersten Start wird SLM:

1. **Deine Steam-Installation erkennen** — findet automatisch deinen Steam-Pfad
2. **Nach deinem Steam-Account fragen** — wähle welchen Steam-Benutzer du verwalten willst
3. **Die lokale Datenbank aufbauen** — das dauert beim ersten Mal 10-30 Sekunden
4. **Deine Sammlungen laden** — liest deine bestehenden Steam-Kategorien aus dem Cloud Storage

Nach dem initialen Setup dauern Folgestarts weniger als 3 Sekunden.

**Wichtig:** Stelle sicher, dass Steam nicht läuft wenn du SLM zum ersten Mal nutzt, oder ändere zumindest keine Sammlungen in Steam während SLM geöffnet ist. SLM synchronisiert mit Steams Cloud Storage, und gleichzeitige Schreibvorgänge können Konflikte verursachen.

---

## Hauptfenster

Das Hauptfenster hat vier Bereiche:

```
┌─────────────────────────────────────────────────────────┐
│  Menüleiste  |  Symbolleiste                            │
├──────────────┬──────────────────────────────────────────┤
│              │                                          │
│  Kategorie-  │  Spielliste / Details                    │
│  baum        │                                          │
│  (Seiten-    │                                          │
│  leiste)     │                                          │
│              │                                          │
│  Strg+B zum  │  Klicke ein Spiel für Details            │
│  Ein/Aus     │  Leertaste für Detailbereich             │
│              │                                          │
├──────────────┴──────────────────────────────────────────┤
│  Statusleiste — Spielanzahl, Filterstatus, Meldungen    │
└─────────────────────────────────────────────────────────┘
```

**Seitenleiste (Kategoriebaum):** Zeigt alle Sammlungen, Smart Collections und Sonderkategorien (Alle Spiele, Unkategorisiert, Favoriten, Versteckt). Klicken zum Filtern. Rechtsklick für Kontextmenü.

**Spielliste:** Zeigt Spiele in der gewählten Kategorie. Mehrfachauswahl mit Strg+Klick oder Umschalt+Klick.

**Detailbereich:** Zeigt Metadaten, Artwork, Spielzeit, Erfolge und mehr für das ausgewählte Spiel. Umschalten mit `Leertaste`.

**Statusleiste:** Live-Statistiken zur aktuellen Ansicht — wie viele Spiele angezeigt werden, welche Filter aktiv sind.

---

## Sammlungen verwalten

### Sammlung erstellen

Rechtsklick im Kategoriebaum → „Neue Sammlung" → Namen eingeben. Die Sammlung wird automatisch mit Steam synchronisiert.

### Spiele zu Sammlungen hinzufügen

1. Wähle ein oder mehrere Spiele in der Spielliste
2. Ziehe sie auf eine Sammlung in der Seitenleiste, ODER
3. Rechtsklick → „Zu Sammlung hinzufügen" → Ziel wählen

### Spiele aus Sammlungen entfernen

1. Wähle Spiele innerhalb einer Sammlung
2. Drücke `Entf`, ODER
3. Rechtsklick → „Aus Sammlung entfernen"

### Sammlungen umbenennen

Sammlung auswählen → `F2` drücken → neuen Namen eingeben.

### Synchronisation mit Steam

SLM liest und schreibt in Steams Cloud Storage (`cloud-storage-namespace-1.json`). Änderungen in SLM erscheinen in Steam nach einem Steam-Neustart. Änderungen in Steam erscheinen in SLM nach dem Aktualisieren (`Strg+R`).

**Konflikterkennung:** Wenn Steams Cloud-Datei geändert wurde während SLM offen war, erstellt SLM ein Backup vor dem Speichern und zeigt eine Warnung.

---

## Smart Collections

Smart Collections sind sich automatisch aktualisierende Ordner basierend auf Regeln. Sie schließen automatisch jedes Spiel ein, das deinen Kriterien entspricht.

### Smart Collection erstellen

1. Drücke `Strg+Umschalt+N` oder gehe zu Bearbeiten → Sammlungen → Smart Collection erstellen
2. Gib einen Namen ein
3. Füge Regeln mit dem Regel-Editor hinzu

### Regel-Logik

Regeln unterstützen drei Operatoren:

- **UND** — Alle Bedingungen müssen zutreffen (Standard)
- **ODER** — Mindestens eine Bedingung muss zutreffen
- **NICHT** — Spiele ausschließen, die dieser Bedingung entsprechen

**Beispiel:** „Linux-RPGs unter 20 Stunden"
```
Plattform = Linux  UND
Genre enthält „RPG"  UND
HLTB Hauptstory < 20h
```

**Beispiel:** „Wochenend-Picks" (Spiele die ENTWEDER kurz ODER hoch bewertet sind)
```
(HLTB Hauptstory < 10h  ODER  Bewertung > 90%)
UND  Status = Nicht gestartet
```

### Verfügbare Regeltypen

| Feld | Operatoren | Beispiel |
|------|------------|----------|
| Genre | enthält, enthält nicht | Genre enthält „RPG" |
| Tags | enthält, enthält nicht | Tags enthält „Open World" |
| Plattform | gleich | Plattform = Linux |
| Spielzeit | <, >, =, zwischen | Spielzeit < 120 Minuten |
| Bewertung | <, >, zwischen | Bewertung > 85% |
| HLTB-Zeit | <, >, zwischen | Hauptstory < 20h |
| Deck-Status | gleich | Deck = Verified |
| Erfolge % | <, >, zwischen | Erfolge > 75% |
| Erscheinungsjahr | <, >, =, zwischen | Jahr > 2020 |
| Entwickler | gleich, enthält | Entwickler = „Valve" |
| Publisher | gleich, enthält | Publisher enthält „Devolver" |
| Sprache | unterstützt | Sprache unterstützt Deutsch |
| Name | enthält, regex | Name enthält „Dark" |

---

## Auto-Kategorisierung

AutoCat (`Strg+Umschalt+A`) sortiert Spiele automatisch basierend auf ihren Metadaten in Kategorien.

### Verwendung

1. Wähle die zu kategorisierenden Spiele (oder wähle „Alle Spiele" im Dialog)
2. Öffne AutoCat: `Strg+Umschalt+A`
3. Aktiviere die gewünschten Kategorisierungstypen
4. Optional: Passe Einstellungen pro Typ an (z.B. „Top 5 Tags" statt „Top 3")
5. Klicke „Starten"

### AutoCat-Typen

| Typ | Erstellt Kategorien wie... |
|-----|---------------------------|
| Genre | „Action", „RPG", „Strategie" |
| Tags | „Open World", „Co-op", „Roguelike" |
| Entwickler | „Valve", „FromSoftware" |
| Publisher | „Devolver Digital", „Annapurna" |
| Plattform | „Linux Nativ", „Nur Windows" |
| Jahr | „2024", „2023", „Vor 2000" |
| Nutzerbewertung | „Overwhelmingly Positive", „Mixed" |
| Spielzeit | „Ungespielt", „< 5h", „5-20h", „20h+" |
| HLTB | „Kurz (< 5h)", „Mittel", „Lang (40h+)" |
| Deck-Status | „Deck: Verified", „Deck: Playable" |
| Erfolge | „100% Komplett", „Fast (>90%)" |
| Sprache | „Unterstützt Deutsch", „Japanisch verfügbar" |
| VR | „VR-Unterstützung", „VR Only" |
| Flags | „Early Access", „Free to Play" |
| Franchise | Spieleserien-Gruppierungen |
| Kurator | Basierend auf Kurator-Empfehlungen |

### Presets

Speichere deine AutoCat-Konfiguration als Preset zur Wiederverwendung:
- Klicke „Preset speichern" → gib einen Namen ein
- Beim nächsten Mal „Preset laden", um deine exakte Konfiguration wiederherzustellen

**Tipp:** Führe AutoCat nach dem Enrichment aus für die besten Ergebnisse — mehr Metadaten bedeuten genauere Kategorisierung.

---

## Daten-Enrichment

SLM kann zusätzliche Daten aus mehreren Quellen abrufen, um deine Spielmetadaten anzureichern.

### Verfügbare Quellen

| Quelle | Menüpfad | Hinzugefügte Daten |
|--------|----------|-------------------|
| Steam-API | Werkzeuge → Batch → Metadaten aktualisieren | Genres, Tags, Beschreibungen, Screenshots, Bewertungen |
| HLTB | Werkzeuge → Batch → HLTB aktualisieren | Hauptstory-, Completionist- und alle Spielstil-Zeiten |
| ProtonDB | Werkzeuge → Batch → ProtonDB aktualisieren | Linux-Kompatibilitätsbewertungen (Platinum, Gold, Silver, etc.) |
| Steam Deck | Werkzeuge → Batch → Deck-Status abrufen | Verified, Playable, Unsupported, Unknown |
| Erfolge | Werkzeuge → Batch → Achievements aktualisieren | Erfolgsanzahl, Abschlussquote |
| Tags | Werkzeuge → Batch → Tags importieren | Steam-Community-Tags aus appinfo.vdf |

### ALLE Daten NEU einlesen

Werkzeuge → Batch → „ALLE Daten NEU einlesen" führt alle Enrichments parallel aus mit einer Multi-Track-Fortschrittsanzeige, die jede Quelle unabhängig zeigt.

### Force Refresh

Jede Quelle hat eine „Force Refresh"-Variante, die ALLE Daten erneut abruft. Verwende dies wenn:
- Sich Bewertungen geändert haben (z.B. ein Spiel wurde Deck Verified)
- Du vermutest, dass zwischengespeicherte Daten veraltet sind
- Nach einem großen Steam Sale (viele neue Spiele)

---

## Externe Spiele

SLM kann Spiele von 8 Nicht-Steam-Plattformen erkennen und verwalten (`Strg+Umschalt+E`).

### Unterstützte Plattformen

| Plattform | Erkennungsmethode |
|-----------|-------------------|
| Epic Games Store | Lokale Manifest-Dateien |
| GOG Galaxy | GOG-Datenbank |
| Heroic Launcher | Heroic-Konfiguration |
| Lutris | Lutris-Datenbank |
| Flatpak | Installierte Flatpak-Spiele |
| Bottles | Bottles-Konfiguration |
| itch.io | itch-App-Datenbank |
| Amazon Games | Amazon-Launcher-Daten |

### Externe Spiele zu Steam hinzufügen

1. Öffne den Externe-Spiele-Manager (`Strg+Umschalt+E`)
2. Klicke „Plattformen scannen" um installierte Spiele zu erkennen
3. Wähle Spiele zum Hinzufügen aus
4. SLM erstellt Nicht-Steam-Verknüpfungen mit:
   - Korrekten Startbefehlen
   - Artwork von SteamGridDB (automatisch)
   - Plattform-Sammlung (z.B. „Epic Games")

---

## Import & Export

### Export-Optionen (Datei → Export)

| Format | Inhalt | Verwendungszweck |
|--------|--------|-----------------|
| Collections VDF | Kategoriezuordnungen | Backup oder Organisation teilen |
| Collections Text | Menschenlesbare Kategorieliste | Schnellübersicht |
| CSV Einfach | Einfache Spieleliste | Tabellen, einfache Analyse |
| CSV Vollständig | Alle Metadaten (17+ Spalten) | Datenanalyse, Vergleich |
| JSON | Datenbankexport | Vollständiges Backup, Migration |
| Smart Collections | Smart-Collection-Regeln | Regeln mit anderen teilen |
| DB Backup | Komplette SQLite-Datenbank | Vollständiges Daten-Backup |

### Import-Optionen (Datei → Import)

| Format | Was wiederhergestellt wird |
|--------|--------------------------|
| Collections VDF | Kategoriezuordnungen |
| Smart Collections | Smart-Collection-Regeln |
| DB Backup | Vollständiger Datenbankzustand |

---

## Profile & Backup

### Profile

Profile speichern einen Snapshot deiner gesamten Kategorieorganisation.

- **Speichern:** Datei → Profile → Aktuelles speichern
- **Laden:** Datei → Profile → Verwalten → Profil wählen → Laden
- **Anwendungsfall:** Vor größeren Umstrukturierungen speichern, bei Unzufriedenheit wiederherstellen

### Backup

Mehrere Backup-Mechanismen:

| Methode | Was | Wie |
|---------|-----|-----|
| Auto-Backup | Cloud-Storage-Backup vor jedem Speichern | Automatisch |
| Manuelles Backup | `Strg+Umschalt+S` | Datenbank-Snapshot |
| Export | Datei → Export → DB Backup | Komplette Datenbank |
| Profile | Datei → Profile → Speichern | Kategorie-Snapshot |

---

## Ansichtsfilter & Sortierung

Das Ansicht-Menü bietet leistungsstarke Filter- und Sortiermöglichkeiten.

### Sortieroptionen

| Sortierung | Verhalten |
|------------|-----------|
| Name | Alphabetisch A→Z |
| Spielzeit | Meistgespielte zuerst |
| Zuletzt gespielt | Zuletzt gespielte zuerst |
| Erscheinungsdatum | Neueste zuerst |

### Filter-Untermenüs

Alle Filter sind stapelbar — aktiviere mehrere, um die Ansicht einzugrenzen.

**Typ:** Spiele, Soundtracks, Software, Videos, DLCs, Tools (standardmäßig alle aktiviert)

**Plattform:** Linux, Windows, SteamOS (standardmäßig alle aktiviert)

**Status:** Installiert, Nicht installiert, Versteckt, Mit Spielzeit, Favoriten (standardmäßig alle deaktiviert — aktivieren zum Filtern)

**Sprache:** 15 Sprachen verfügbar. Eine oder mehrere aktivieren, um nur Spiele mit dieser Sprachunterstützung anzuzeigen.

**Steam Deck:** Verified, Playable, Unsupported, Unknown

**Erfolge:** Perfekt (100%), Fast (>90%), In Arbeit, Angefangen, Keine

---

## Einstellungen

Öffne die Einstellungen mit `Strg+P` oder Werkzeuge → Einstellungen.

### Allgemein

- **Sprache:** Zwischen Deutsch und Englisch wechseln (weitere Sprachen geplant)
- **Steam-Pfad:** Automatisch erkannt, kann überschrieben werden
- **Steam-Benutzer:** Welchen Steam-Account verwalten

### Sonstiges

- Zusätzliche Konfigurationsoptionen
- Backup-Einstellungen

---

## Tastenkürzel

Siehe die vollständige [Tastenkürzel-Referenz](KEYBOARD_SHORTCUTS.md).

Kurzübersicht:

| Tastenkürzel | Aktion |
|--------------|--------|
| `Strg+F` | Suche |
| `Strg+S` | Speichern |
| `Strg+R` / `F5` | Aktualisieren |
| `Strg+B` | Seitenleiste ein/aus |
| `Leertaste` | Detailbereich ein/aus |
| `Esc` | Suche/Auswahl leeren |
| `Strg+Umschalt+N` | Neue Smart Collection |
| `Strg+Umschalt+A` | Auto-Kategorisieren |
| `F1` | Dieses Handbuch |

---

## Problemlösung

### SLM findet meine Steam-Installation nicht

SLM sucht an Standardpfaden (`~/.steam`, `~/.local/share/Steam`). Wenn dein Steam woanders installiert ist, setze den Pfad manuell unter Einstellungen → Allgemein → Steam-Pfad.

### Sammlungen erscheinen nicht in Steam

1. Stelle sicher, dass du in SLM gespeichert hast (`Strg+S`)
2. Starte Steam komplett neu (nicht nur ins Tray minimieren)
3. Prüfe ob Steam Cloud Sync in den Steam-Einstellungen aktiviert ist

### Erster Start ist sehr langsam

Normal! SLM baut beim ersten Start seine lokale SQLite-Datenbank auf. Das indexiert deine gesamte Bibliothek und dauert je nach Bibliotheksgröße 10-30 Sekunden. Folgestarts brauchen unter 3 Sekunden.

### Enrichment zeigt Fehler für einige Spiele

Manche Spiele (aus Steam entfernt, regiongesperrt oder sehr alt) haben möglicherweise nicht bei allen Quellen Daten verfügbar. SLM überspringt diese und reichert an, was möglich ist.

### „Konflikt erkannt"-Warnung beim Speichern

Das bedeutet, dass Steams Cloud-Storage-Datei geändert wurde, während SLM geöffnet war (vermutlich von Steam selbst). SLM erstellt ein Backup vor dem Speichern. Deine Daten sind sicher — aktualisiere (`Strg+R`) um den neuesten Stand zu sehen.

### Scanner für externe Spiele findet nichts

Stelle sicher, dass der jeweilige Plattform-Launcher (Epic, GOG, etc.) tatsächlich installiert ist und mindestens einmal gestartet wurde. SLM liest lokale Konfigurationsdateien, die beim ersten Start jedes Launchers erstellt werden.

### ProtonDB- / Deck-Status-Filter zeigen 0 Ergebnisse

Führe zuerst Werkzeuge → Batch → ProtonDB aktualisieren und Deck-Status abrufen aus. Diese Filter benötigen Enrichment-Daten, die nicht standardmäßig geladen werden.

---

*Weitere Antworten findest du in den [Häufig gestellten Fragen](FAQ.md).*

*Brauchst du weitere Hilfe? Besuche Hilfe → Online → Discussions oder melde Issues auf GitHub.*
