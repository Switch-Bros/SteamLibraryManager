# 💡 Tipps & Tricks

Power-User-Tipps, um das Beste aus dem Steam Library Manager herauszuholen.

---

## 🔍 Suchen wie ein Profi

Die Suchleiste (`Strg+F`) filtert sofort nach Spielnamen. Kombiniere sie mit den Ansichtsfiltern für noch bessere Ergebnisse:

- **Suche + Typfilter:** Suche „dark" mit nur „Spiele" aktiviert > findet Dark Souls, Darkest Dungeon, etc. ohne Soundtracks oder DLCs.
- **Suche + Plattformfilter:** Deaktiviere „Windows" unter Ansicht > Plattform, um nur Linux-native Spiele zu sehen.
- **Schnell leeren:** Drücke `Esc`, um die Suche sofort zu leeren und die gesamte Bibliothek zu sehen.

## 📂 Organisieren mit Smart Collections

Smart Collections sind sich automatisch aktualisierende Ordner, die Spiele anhand deiner Regeln einschließen. Sie sind das mächtigste Feature in SLM.

**So geht's los:**
1. `Strg+Umschalt+N` zum Erstellen einer neuen Smart Collection
2. Regeln mit UND/ODER/NICHT-Logik hinzufügen
3. Die Sammlung aktualisiert sich automatisch, wenn sich deine Bibliothek ändert

**Nützliche Smart-Collection-Ideen:**

| Sammlungsname | Regeln |
|---------------|--------|
| „Kurze Sessions" | Spielzeit < 2h UND Genre enthält „Indie" |
| „Linux Nativ" | Plattform = Linux UND Status = Installiert |
| „Ungespielte Perlen" | Spielzeit = 0 UND Bewertung > 85% |
| „Deck-Ready" | Deck-Status = Verified UND Spielzeit < 10h |
| „Fast Geschafft" | Erfolge > 75% UND Erfolge < 100% |

## 🏷️ AutoCat - Automatische Kategorisierung

AutoCat (`Strg+Umschalt+A`) sortiert deine gesamte Bibliothek automatisch in Kategorien. Mit 17 Kategorisierungstypen organisierst du nach:

- **Genre** - RPG, Action, Strategie, etc.
- **Entwickler / Publisher** - Gruppierung nach Studio
- **Plattform** - Linux, Windows, SteamOS
- **Tags** - Top N Steam-Tags pro Spiel
- **Jahr** - Erscheinungsjahr-Kategorien
- **HLTB** - „Kurz (< 5h)", „Mittel (5-20h)", „Lang (20h+)"
- **Deck-Status** - Verified, Playable, Unsupported
- **Erfolge** - Perfekt, Fast geschafft, In Arbeit
- **Sprache** - Spiele mit bestimmter Sprachunterstützung
- **Nutzerbewertung** - Overwhelmingly Positive, Mixed, etc.
- Und mehr!

**Profitipp:** Speichere deine AutoCat-Konfiguration als Preset. So kannst du sie jederzeit laden, um nach neuen Spielen erneut zu kategorisieren.

## 🔄 Enrichment - Fehlende Daten ergänzen

Unter Werkzeuge > Batch-Operationen kannst du deine Bibliothek mit Daten aus mehreren Quellen anreichern:

| Quelle | Was wird hinzugefügt | Dauer |
|--------|---------------------|-------|
| Steam-API | Genres, Tags, Beschreibungen, Screenshots | ~2 Min. für 3000 Spiele |
| HLTB | How Long to Beat-Zeiten | ~5 Min. (Rate Limited) |
| ProtonDB | Linux-Kompatibilitätsbewertungen | ~1 Min. |
| Steam Deck | Deck-Verifizierungsstatus | ~2 Min. |
| Erfolge | Erfolgsstatistiken & Prozentangaben | ~3 Min. |

**„ALLE Daten NEU einlesen"** führt alle Enrichments parallel aus mit einer Multi-Track-Fortschrittsanzeige. Am besten nach einer Neuinstallation oder wenn viele neue Spiele hinzugekommen sind.

**Force-Refresh**-Varianten (pro Quelle verfügbar) holen auch zwischengespeicherte Daten erneut - nützlich wenn sich Bewertungen ändern oder neue Daten verfügbar sind.

## 🎮 Externe Spiele

SLM kann Spiele von anderen Plattformen finden und verwalten (`Strg+Umschalt+E`):

- **Epic Games Store** - Scannt lokale Manifeste
- **GOG Galaxy** - Liest die GOG-Datenbank
- **Heroic Launcher** - Epic/GOG via Heroic
- **Lutris** - Jedes in Lutris konfigurierte Spiel
- **Flatpak** - Als Flatpak installierte Spiele
- **Bottles** - Windows-Spiele via Bottles
- **itch.io** - Spiele von itch
- **Amazon Games** - Amazon-Gaming-Bibliothek

Gefundene Spiele können als Nicht-Steam-Verknüpfungen zu Steam hinzugefügt werden, inklusive Artwork von SteamGridDB.

## 💾 Backup-Strategie

SLM hat mehrere Schutzebenen:

1. **Auto-Backup:** Cloud Storage wird vor jedem Speichern gesichert
2. **Manuelles Backup:** `Strg+Umschalt+S` erstellt einen Datenbank-Snapshot mit Zeitstempel
3. **Profile:** Datei > Profile > Aktuelles speichern sichert deine gesamte Kategoriestruktur
4. **Export:** Datei > Export bietet CSV-, VDF- und JSON-Exporte

**Empfehlung:** Speichere ein Profil vor größeren Umstrukturierungen. Falls etwas schiefgeht, lade das Profil zum Wiederherstellen.

## ⚡ Performance-Tipps

- **Erster Start ist langsam** - SLM baut beim ersten Start seine lokale Datenbank auf. Folgestarts sind deutlich schneller (< 3 Sekunden).
- **Batch-Enrichment nutzen** - Führe „ALLE Daten NEU einlesen" einmal nach dem Setup aus, dann einzelne Enrichments für Updates.
- **Große Bibliotheken (3000+ Spiele):** Die Seitenleiste braucht nach großen AutoCat-Läufen einen Moment zum Neuaufbau. Das ist normal.

## 🖥️ Ansicht anpassen

Das Ansicht-Menü bietet mächtige Filter-Untermenüs:

- **Sortieren nach:** Name, Spielzeit, Zuletzt gespielt, Erscheinungsdatum
- **Typ:** Spiele, Soundtracks, Software, Videos, DLCs, Tools ein/ausblenden
- **Plattform:** Nach Linux-, Windows-, SteamOS-Unterstützung filtern
- **Status:** Installiert, Nicht installiert, Versteckt, Mit Spielzeit, Favoriten
- **Sprache:** Filter für 15 unterstützte Sprachen
- **Steam Deck:** Verified, Playable, Unsupported, Unknown
- **Erfolge:** Perfekt, Fast, In Arbeit, Angefangen, Keine

Alle Filter sind stapelbar - aktiviere mehrere, um die Ansicht einzugrenzen.

## 🔐 Sicherheit

- Steam-Login-Tokens werden im System-Keyring gespeichert (oder AES-GCM-verschlüsselt als Fallback)
- Keine Passwörter oder API-Keys im Klartext
- Cloud-Storage-Sync nutzt Steams eigene Authentifizierung

## 🎯 Versteckte Features

- **Drag & Drop:** Ziehe Spiele zwischen Kategorien in der Seitenleiste
- **Mehrfachauswahl:** Klicke Spiele mit gedrückter `Strg`- oder `Umschalt`-Taste für Massenoperationen
- **Rechtsklick-Kontextmenüs:** Rechtsklick auf Spiele oder Kategorien für schnelle Aktionen
- **Doppelklick:** Doppelklick auf ein Spiel öffnet seine Steam-Store-Seite
- **Statusleiste:** Zeigt Live-Statistiken zur aktuellen Ansicht (Spielanzahl, aktive Filter)

## ☁️ Cloud Sync

Nutze rclone mit MEGA für kostenlosen 20GB Cloud-Speicher. Setze den Sync-Modus auf „Auto-Upload beim Beenden" unter Einstellungen > Cloud Sync, und deine Bibliothek wird automatisch gesichert. So hast du auf allen Rechnern den gleichen Stand.

## ✏️ Metadaten-Editor

Nutze Bulk-Edit um allen Spielen eines Publishers ein Präfix hinzuzufügen, oder korrigiere Sortiertitel damit „The Witcher 3" unter W sortiert wird. Wähle mehrere Spiele mit Strg+Klick aus, dann Rechtsklick > „Metadaten bearbeiten". Änderungen werden als Overlay gespeichert und überleben Steam-Updates.

## 🖼️ Artwork Manager

Nutze die Filter-Badges im SteamGridDB-Browser um schnell animierte Cover (GIF) zu finden. Schalte den NSFW-Filter um wenn du Artwork für Erwachsene möchtest. Klicke einfach auf das Spielcover im Detailbereich um den Browser zu öffnen.

## 🩺 Library Health Check

Führe den Library Health Check regelmäßig aus (Werkzeuge > Store-Seiten prüfen) um delistete Spiele, fehlende Metadaten und veraltete Caches zu finden. Die Ergebnisse sind nach Tabs gruppiert (Store, Daten, Cache), sodass du gezielt Probleme beheben kannst.

## 🔑 API Keys & Sicherheit

Deine API-Keys werden jetzt im System-Keyring gespeichert für bessere Sicherheit. Auf Systemen ohne Keyring (z.B. minimale Installationen) nutzt SLM verschlüsselte Datei-Speicherung als Fallback. Alte Keys in der settings.json werden beim Start automatisch migriert.

---

*Einen Bug gefunden oder einen Feature-Wunsch? Hilfe > Online > Issues melden*
