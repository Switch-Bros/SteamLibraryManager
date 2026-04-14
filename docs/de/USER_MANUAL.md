# 📖 Steam Library Manager - Benutzerhandbuch

**Version:** 1.3.9
**Plattform:** Linux (CachyOS, Ubuntu, Fedora, Arch, SteamOS, etc.)

---

## Inhaltsverzeichnis

1. [Was ist Steam Library Manager?](#was-ist-steam-library-manager)
2. [Installation](#installation)
3. [Erster Start](#erster-start)
4. [Steam Login](#steam-login)
5. [Hauptfenster](#hauptfenster)
6. [Sammlungen verwalten](#sammlungen-verwalten)
7. [Smart Collections](#smart-collections)
8. [Auto-Kategorisierung](#auto-kategorisierung)
9. [Daten-Enrichment](#daten-enrichment)
10. [Metadaten-Editor](#metadaten-editor)
11. [Artwork Manager](#artwork-manager)
12. [Externe Spiele](#externe-spiele)
13. [Import & Export](#import--export)
14. [Cloud Sync](#cloud-sync)
15. [Profile & Backup](#profile--backup)
16. [Ansichtsfilter & Sortierung](#ansichtsfilter--sortierung)
17. [Library Health Check](#library-health-check)
18. [Auto-Updates (AppImage)](#auto-updates-appimage)
19. [Einstellungen](#einstellungen)
20. [Tastenkürzel](#tastenkürzel)
21. [Problemlösung](#problemlösung)

---

## Was ist Steam Library Manager?

Steam Library Manager (SLM) ist ein leistungsstarkes Werkzeug zur Organisation großer Steam-Spielebibliotheken unter Linux. Stell es dir als moderne, Linux-native Alternative zu Depressurizer vor - mit Extras.

**Hauptfunktionen:**
- 3000+ Spiele in Sammlungen organisieren, die mit Steam synchronisiert werden
- 17 automatische Kategorisierungstypen (Genre, Tags, Spielzeit, HLTB und mehr)
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
flatpak install flathub io.github.switch_bros.SteamLibraryManager
```

### AUR (Arch Linux / CachyOS)

```bash
yay -S steam-library-manager
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
python steam_library_manager/main.py
```

Erfordert Python 3.11+ und PyQt6.

---

## Erster Start

Beim ersten Start wird SLM:

1. **Deine Steam-Installation erkennen** - findet automatisch deinen Steam-Pfad
2. **Nach deinem Steam-Account fragen** - wähle welchen Steam-Benutzer du verwalten willst
3. **Die lokale Datenbank aufbauen** - das dauert beim ersten Mal 10-30 Sekunden
4. **Deine Sammlungen laden** - liest deine bestehenden Steam-Kategorien aus dem Cloud Storage

Nach dem initialen Setup dauern Folgestarts weniger als 3 Sekunden.

**Wichtig:** Stelle sicher, dass Steam nicht läuft wenn du SLM zum ersten Mal nutzt, oder ändere zumindest keine Sammlungen in Steam während SLM geöffnet ist. SLM synchronisiert mit Steams Cloud Storage, und gleichzeitige Schreibvorgänge können Konflikte verursachen.

---

## Steam Login

SLM bietet zwei Methoden zur Authentifizierung mit Steam:

### QR-Code Login (Empfohlen)

1. Öffne den Login-Dialog über Werkzeuge > Steam Login
2. Ein QR-Code wird angezeigt
3. Öffne die Steam Mobile App auf deinem Handy
4. Scanne den QR-Code mit der App
5. Bestätige den Login in der App

### Passwort Login

1. Öffne den Login-Dialog über Werkzeuge > Steam Login
2. Gib deinen Steam-Benutzernamen und dein Passwort ein
3. Bestätige den Login über die Steam Mobile App (2FA)

### Token-Speicherung

Login-Tokens werden verschlüsselt im System-Keyring gespeichert (KWallet, GNOME Keyring, etc.). Falls kein Keyring verfügbar ist, nutzt SLM AES-GCM-verschlüsselte Dateien als Fallback. Tokens werden niemals im Klartext gespeichert.

### Automatische Session-Wiederherstellung

Beim Start versucht SLM automatisch, die letzte Session wiederherzustellen. Solange dein Token gültig ist, musst du dich nicht erneut einloggen.

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
│  Statusleiste - Spielanzahl, Filterstatus, Meldungen    │
└─────────────────────────────────────────────────────────┘
```

**Seitenleiste (Kategoriebaum):** Zeigt alle Sammlungen, Smart Collections und Sonderkategorien (Alle Spiele, Unkategorisiert, Favoriten, Versteckt). Klicken zum Filtern. Rechtsklick für Kontextmenü.

**Spielliste:** Zeigt Spiele in der gewählten Kategorie. Mehrfachauswahl mit Strg+Klick oder Umschalt+Klick.

**Detailbereich:** Zeigt Metadaten, Artwork, Spielzeit, Erfolge und mehr für das ausgewählte Spiel. Umschalten mit `Leertaste`.

**Statusleiste:** Live-Statistiken zur aktuellen Ansicht - wie viele Spiele angezeigt werden, welche Filter aktiv sind.

---

## Sammlungen verwalten

### Sammlung erstellen

Rechtsklick im Kategoriebaum > „Neue Sammlung" > Namen eingeben. Die Sammlung wird automatisch mit Steam synchronisiert.

### Spiele zu Sammlungen hinzufügen

1. Wähle ein oder mehrere Spiele in der Spielliste
2. Ziehe sie auf eine Sammlung in der Seitenleiste, ODER
3. Rechtsklick > „Zu Sammlung hinzufügen" > Ziel wählen

### Spiele aus Sammlungen entfernen

1. Wähle Spiele innerhalb einer Sammlung
2. Drücke `Entf`, ODER
3. Rechtsklick > „Aus Sammlung entfernen"

### Sammlungen umbenennen

Sammlung auswählen > `F2` drücken > neuen Namen eingeben.

### Synchronisation mit Steam

SLM liest und schreibt in Steams Cloud Storage (`cloud-storage-namespace-1.json`). Änderungen in SLM erscheinen in Steam nach einem Steam-Neustart. Änderungen in Steam erscheinen in SLM nach dem Aktualisieren (`Strg+R`).

**Konflikterkennung:** Wenn Steams Cloud-Datei geändert wurde während SLM offen war, erstellt SLM ein Backup vor dem Speichern und zeigt eine Warnung.

---

## Smart Collections

Smart Collections sind sich automatisch aktualisierende Ordner basierend auf Regeln. Sie schließen automatisch jedes Spiel ein, das deinen Kriterien entspricht.

### Smart Collection erstellen

1. Drücke `Strg+Umschalt+N` oder gehe zu Bearbeiten > Sammlungen > Smart Collection erstellen
2. Gib einen Namen ein
3. Füge Regeln mit dem Regel-Editor hinzu

### Regel-Logik

Regeln unterstützen drei Operatoren:

- **UND** - Alle Bedingungen müssen zutreffen (Standard)
- **ODER** - Mindestens eine Bedingung muss zutreffen
- **NICHT** - Spiele ausschließen, die dieser Bedingung entsprechen

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
| PEGI | „PEGI 03", „PEGI 12", „PEGI 18" |
| Franchise | Spieleserien-Gruppierungen |
| Kurator | Basierend auf Kurator-Empfehlungen |

### Presets

Speichere deine AutoCat-Konfiguration als Preset zur Wiederverwendung:
- Klicke „Preset speichern" > gib einen Namen ein
- Beim nächsten Mal „Preset laden", um deine exakte Konfiguration wiederherzustellen

**Tipp:** Führe AutoCat nach dem Enrichment aus für die besten Ergebnisse - mehr Metadaten bedeuten genauere Kategorisierung.

---

## Daten-Enrichment

SLM kann zusätzliche Daten aus mehreren Quellen abrufen, um deine Spielmetadaten anzureichern.

### Verfügbare Quellen

| Quelle | Menüpfad | Hinzugefügte Daten |
|--------|----------|-------------------|
| Steam-API | Werkzeuge > Batch > Metadaten aktualisieren | Genres, Tags, Beschreibungen, Screenshots, Bewertungen |
| HLTB | Werkzeuge > Batch > HLTB aktualisieren | Hauptstory-, Completionist- und alle Spielstil-Zeiten |
| ProtonDB | Werkzeuge > Batch > ProtonDB aktualisieren | Linux-Kompatibilitätsbewertungen (Platinum, Gold, Silver, etc.) |
| Steam Deck | Werkzeuge > Batch > Deck-Status abrufen | Verified, Playable, Unsupported, Unknown |
| Erfolge | Werkzeuge > Batch > Achievements aktualisieren | Erfolgsanzahl, Abschlussquote |
| Tags | Werkzeuge > Batch > Tags importieren | Steam-Community-Tags aus appinfo.vdf |

### ALLE Daten NEU einlesen

Werkzeuge > Batch > „ALLE Daten NEU einlesen" führt alle Enrichments parallel aus mit einer Multi-Track-Fortschrittsanzeige, die jede Quelle unabhängig zeigt.

### Force Refresh

Jede Quelle hat eine „Force Refresh"-Variante, die ALLE Daten erneut abruft. Verwende dies wenn:
- Sich Bewertungen geändert haben (z.B. ein Spiel wurde Deck Verified)
- Du vermutest, dass zwischengespeicherte Daten veraltet sind
- Nach einem großen Steam Sale (viele neue Spiele)

---

## Metadaten-Editor

SLM erlaubt es, Spielmetadaten manuell zu bearbeiten - unabhängig von Steam-Updates.

### Einzelnes Spiel bearbeiten

1. Rechtsklick auf ein Spiel > „Metadaten bearbeiten", oder Spiel auswählen und den Edit-Button klicken
2. Bearbeitbare Felder: Name, Sortiertitel, Entwickler, Herausgeber, Erscheinungsdatum
3. Änderungen speichern

### Overlay-System

Manuelle Änderungen werden separat als Overlay gespeichert. Wenn Steam seine Metadaten aktualisiert, bleiben deine Anpassungen erhalten - sie überleben Steam-Updates.

### Bulk-Edit

1. Wähle mehrere Spiele aus (Strg+Klick oder Umschalt+Klick)
2. Rechtsklick > „Metadaten bearbeiten"
3. Änderungen an einem Feld werden auf alle ausgewählten Spiele angewendet

### VDF-Schreib-Option

Optional können Metadaten-Änderungen direkt in Steams `appinfo.vdf` geschrieben werden. Dafür ist ein Steam-Neustart nötig, damit die Änderungen wirksam werden.

---

## Artwork Manager

SLM integriert SteamGridDB zum Durchsuchen und Anwenden von Spielgrafiken.

### Artwork durchsuchen

1. Klicke auf das Cover eines Spiels im Detailbereich, um den SteamGridDB-Browser zu öffnen
2. Durchsuche verfügbare Grafiken: Grids, Heroes, Logos, Icons
3. Nutze Filter-Badges: statisch/animiert, NSFW, Humor, Epilepsie
4. Ein Klick auf ein Bild wendet es an

### SteamGridDB API Key

Beim ersten Öffnen des Artwork-Browsers wird ein SteamGridDB API Key abgefragt. Diesen kannst du kostenlos auf [steamgriddb.com](https://www.steamgriddb.com/) erstellen. Der Key wird sicher im System-Keyring gespeichert.

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

### Export-Optionen (Datei > Export)

| Format | Inhalt | Verwendungszweck |
|--------|--------|-----------------|
| Collections VDF | Kategoriezuordnungen | Backup oder Organisation teilen |
| Collections Text | Menschenlesbare Kategorieliste | Schnellübersicht |
| CSV Einfach | Einfache Spieleliste | Tabellen, einfache Analyse |
| CSV Vollständig | Alle Metadaten (17+ Spalten) | Datenanalyse, Vergleich |
| JSON | Datenbankexport | Vollständiges Backup, Migration |
| Smart Collections | Smart-Collection-Regeln | Regeln mit anderen teilen |
| DB Backup | Komplette SQLite-Datenbank | Vollständiges Daten-Backup |

### Import-Optionen (Datei > Import)

| Format | Was wiederhergestellt wird |
|--------|--------------------------|
| Collections VDF | Kategoriezuordnungen |
| Smart Collections | Smart-Collection-Regeln |
| DB Backup | Vollständiger Datenbankzustand |

---

## Cloud Sync

SLM kann deine Daten mit Cloud-Speicherdiensten synchronisieren, um sie zwischen mehreren Rechnern zu teilen.

### Einrichtung

Öffne Einstellungen (`Strg+P`) > Cloud Sync Tab und wähle einen Anbieter:

- **rclone** - Unterstützt 40+ Cloud-Backends (MEGA, Google Drive, Dropbox, OneDrive, etc.). SLM bietet einen integrierten Setup-Wizard, der rclone automatisch herunterlädt und die Konfiguration durchführt.
- **WebDAV** - Direktverbindung zu WebDAV-kompatiblen Servern. Konfiguriere URL, Benutzername und Passwort in den Einstellungen.
- **Keiner** - Cloud Sync deaktiviert.

### Sync-Modi

| Modus | Verhalten |
|-------|-----------|
| Manuell | Du löst Sync manuell über die Menüs aus |
| Auto-Upload beim Beenden | SLM lädt deine Daten automatisch beim Schließen in die Cloud hoch |
| Vollautomatisch | SLM synchronisiert beim Start und beim Beenden automatisch |

### Manueller Sync über Menüs

- **Datei > Exportieren > In die Cloud hochladen** - Einzelne Datentypen in die Cloud hochladen
- **Datei > Importieren > Aus der Cloud herunterladen** - Einzelne Datentypen aus der Cloud herunterladen
- **Datei > Exportieren > Alle Daten in die Cloud** - Bulk-Upload aller Daten
- **Datei > Importieren > Alle Daten aus der Cloud** - Bulk-Download aller Daten

### Konflikterkennung

Wenn sowohl lokale als auch Cloud-Daten seit dem letzten Sync geändert wurden, erkennt SLM den Konflikt und fragt, ob die lokale Version hochgeladen oder die Cloud-Version heruntergeladen werden soll.

### Profil Cloud-Sync

Profile können über die Cloud-Export/Import-Buttons im Profil-Manager direkt in die Cloud hochgeladen oder von dort heruntergeladen werden.

---

## Profile & Backup

### Profile

Profile speichern einen Snapshot deiner gesamten Kategorieorganisation.

- **Speichern:** Datei > Profile > Aktuelles speichern
- **Laden:** Datei > Profile > Verwalten > Profil wählen > Laden
- **Anwendungsfall:** Vor größeren Umstrukturierungen speichern, bei Unzufriedenheit wiederherstellen

### Backup

Mehrere Backup-Mechanismen:

| Methode | Was | Wie |
|---------|-----|-----|
| Auto-Backup | Cloud-Storage-Backup vor jedem Speichern | Automatisch |
| Manuelles Backup | `Strg+Umschalt+S` | Datenbank-Snapshot |
| Export | Datei > Export > DB Backup | Komplette Datenbank |
| Profile | Datei > Profile > Speichern | Kategorie-Snapshot |

---

## Ansichtsfilter & Sortierung

Das Ansicht-Menü bietet leistungsstarke Filter- und Sortiermöglichkeiten.

### Sortieroptionen

| Sortierung | Verhalten |
|------------|-----------|
| Name | Alphabetisch A>Z |
| Spielzeit | Meistgespielte zuerst |
| Zuletzt gespielt | Zuletzt gespielte zuerst |
| Erscheinungsdatum | Neueste zuerst |

### Filter-Untermenüs

Alle Filter sind stapelbar - aktiviere mehrere, um die Ansicht einzugrenzen.

**Typ:** Spiele, Soundtracks, Software, Videos, DLCs, Tools (standardmäßig alle aktiviert)

**Plattform:** Linux, Windows, SteamOS (standardmäßig alle aktiviert)

**Status:** Installiert, Nicht installiert, Versteckt, Mit Spielzeit, Favoriten (standardmäßig alle deaktiviert - aktivieren zum Filtern)

**Sprache:** 15 Sprachen verfügbar. Eine oder mehrere aktivieren, um nur Spiele mit dieser Sprachunterstützung anzuzeigen.

**Steam Deck:** Verified, Playable, Unsupported, Unknown

**Erfolge:** Perfekt (100%), Fast (>90%), In Arbeit, Angefangen, Keine

---

## Library Health Check

Werkzeuge > Store-Seiten prüfen startet eine umfassende Prüfung deiner Bibliothek.

### Was wird geprüft?

- **Store-Verfügbarkeit** - Erkennt Spiele, die im Steam Store nicht mehr verfügbar sind (delistet, regiongesperrt)
- **Fehlende Metadaten** - Findet Spiele ohne Genre, Tags, Beschreibung oder andere wichtige Daten
- **Veraltete Caches** - Identifiziert zwischengespeicherte Daten, die aktualisiert werden sollten

### Ergebnisse

Die Ergebnisse werden gruppiert nach Tabs angezeigt: Store, Daten, Cache. So behältst du den Überblick und kannst gezielt Probleme beheben.

---

## Auto-Updates (AppImage)

Die AppImage-Version von SLM prüft automatisch auf neue Versionen.

### Funktionsweise

- **Automatische Prüfung:** SLM prüft die GitHub Releases-Seite auf neue Versionen
- **Konfigurierbares Intervall:** Täglich, wöchentlich, monatlich oder nie (Einstellungen > Allgemein)
- **Hintergrund-Download:** Neue Versionen werden im Hintergrund heruntergeladen
- **Atomarer Austausch:** Die AppImage-Datei wird atomar ersetzt - mit Rollback bei Fehlern
- **Version überspringen:** Wenn du eine Version nicht willst, kannst du sie überspringen

**Hinweis:** AUR- und Flatpak-Installationen werden über ihre jeweiligen Paketmanager aktualisiert.

---

## Einstellungen

Öffne die Einstellungen mit `Strg+P` oder Werkzeuge > Einstellungen.

### Allgemein Tab

- **UI-Sprache:** Zwischen Deutsch und Englisch wechseln (weitere Sprachen geplant)
- **Tag-Sprache:** Sprache für Steam-Tags (unabhängig von der UI-Sprache)
- **Steam-Pfad:** Automatisch erkannt, kann überschrieben werden
- **Steam-Benutzer:** Welchen Steam-Account verwalten

### Weitere Tab

- **API Keys:** Steam API Key und SteamGridDB Key (werden im System-Keyring gespeichert)
- **Tags pro Spiel:** Anzahl der Tags, die pro Spiel bei AutoCat verwendet werden
- **Backup-Einstellungen:** Auto-Backup-Verhalten konfigurieren

### Cloud Sync Tab

- **Anbieter:** rclone, WebDAV oder keiner
- **Remote-Auswahl:** Scrollbare Liste der konfigurierten Cloud-Remotes
- **Sync-Modus:** Manuell, Auto-Upload beim Beenden oder Vollautomatisch
- Siehe [Cloud Sync](#cloud-sync) für Details

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
| `F1` | Benutzerhandbuch |
| `F12` | Über SLM |

---

## Problemlösung

### SLM findet meine Steam-Installation nicht

SLM sucht an Standardpfaden (`~/.steam`, `~/.local/share/Steam`). Wenn dein Steam woanders installiert ist, setze den Pfad manuell unter Einstellungen > Allgemein > Steam-Pfad.

### Sammlungen erscheinen nicht in Steam

1. Stelle sicher, dass du in SLM gespeichert hast (`Strg+S`)
2. Starte Steam komplett neu (nicht nur ins Tray minimieren)
3. Prüfe ob Steam Cloud Sync in den Steam-Einstellungen aktiviert ist

### Erster Start ist sehr langsam

Normal! SLM baut beim ersten Start seine lokale SQLite-Datenbank auf. Das indexiert deine gesamte Bibliothek und dauert je nach Bibliotheksgröße 10-30 Sekunden. Folgestarts brauchen unter 3 Sekunden.

### Enrichment zeigt Fehler für einige Spiele

Manche Spiele (aus Steam entfernt, regiongesperrt oder sehr alt) haben möglicherweise nicht bei allen Quellen Daten verfügbar. SLM überspringt diese und reichert an, was möglich ist.

### „Konflikt erkannt"-Warnung beim Speichern

Das bedeutet, dass Steams Cloud-Storage-Datei geändert wurde, während SLM geöffnet war (vermutlich von Steam selbst). SLM erstellt ein Backup vor dem Speichern. Deine Daten sind sicher - aktualisiere (`Strg+R`) um den neuesten Stand zu sehen.

### Scanner für externe Spiele findet nichts

Stelle sicher, dass der jeweilige Plattform-Launcher (Epic, GOG, etc.) tatsächlich installiert ist und mindestens einmal gestartet wurde. SLM liest lokale Konfigurationsdateien, die beim ersten Start jedes Launchers erstellt werden.

### ProtonDB- / Deck-Status-Filter zeigen 0 Ergebnisse

Führe zuerst Werkzeuge > Batch > ProtonDB aktualisieren und Deck-Status abrufen aus. Diese Filter benötigen Enrichment-Daten, die nicht standardmäßig geladen werden.

---

*Weitere Antworten findest du in den [Häufig gestellten Fragen](FAQ.md).*

*Brauchst du weitere Hilfe? Besuche Hilfe > Online > Discussions oder melde Issues auf GitHub.*
