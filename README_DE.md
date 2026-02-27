<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="resources/images/readme_header_dark.webp">
    <source media="(prefers-color-scheme: light)" srcset="resources/images/readme_header_light.webp">
    <img src="resources/images/readme_header_light.webp" alt="" width="800">
  </picture>
</p>

# 🎮 Steam Library Manager


[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-FDE100?style=plastic&logo=python&logoColor=FDE100&labelColor=000000)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Steam%20Deck-FDE100?style=plastic&logo=linux&logoColor=FDE100&labelColor=000000)](https://store.steampowered.com/steamdeck)
[![Lizenz](https://img.shields.io/badge/Lizenz-MIT-FDE100?style=plastic&labelColor=000000)](https://github.com/Switch-Bros/SteamLibraryManager/blob/main/LICENSE)
[![Tests](https://img.shields.io/badge/Tests-1540%20passed-FDE100?style=plastic&labelColor=000000)](https://github.com/Switch-Bros/SteamLibraryManager)
[![Steam API](https://img.shields.io/badge/Steam%20API-Optional-FDE100?style=plastic&logo=steam&logoColor=FDE100&labelColor=000000)](https://steamcommunity.com/dev/apikey)
[![SteamGridDB](https://img.shields.io/badge/SteamGridDB-Required-FDE100?style=plastic&logoColor=FDE100&labelColor=000000)](https://www.steamgriddb.com/api)
[![i18n](https://img.shields.io/badge/i18n-🇬🇧%20🇩🇪-FDE100?style=plastic&labelColor=000000)](https://github.com/Switch-Bros/SteamLibraryManager)
[![Downloads](https://img.shields.io/badge/Downloads-Coming%20Soon-FDE100?style=plastic&logo=github&logoColor=FDE100&labelColor=000000)](https://github.com/Switch-Bros/SteamLibraryManager/releases)

> **Die Depressurizer-Alternative für Linux.**
> Organisiere deine Steam-Bibliothek, kategorisiere Spiele automatisch, bearbeite Metadaten und behalte die Kontrolle über deine Sammlung — mit Features, die Steam nicht hat.

<p align="center">
  <a href="README.md">
    <img src="https://img.shields.io/badge/🇬🇧_Read_in_English-FDE100?style=for-the-badge&labelColor=000000" alt="Read in English" height="35">
  </a>
</p>

<!-- Hero Screenshot -->
<p align="center">
  <img src="resources/screenshots/de_01_hero_main_window.webp" alt="Steam Library Manager — Hauptfenster (Deutsch)" width="900">
</p>


## ✨ Features

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="resources/images/readme_divider_dark.webp">
    <source media="(prefers-color-scheme: light)" srcset="resources/images/readme_divider_light.webp">
    <img src="resources/images/readme_divider_light.webp" alt="" width="800">
  </picture>
</p>

### 🧠 Smart Collections — *Besser als Steams eigene dynamische Kollektionen*

Steam hat dynamische Kollektionen — aber die haben **seit ihrer Einführung nur UND-Logik**. Spiele die *entweder* "Platinum auf ProtonDB" *oder* "Native Linux" sind anzeigen? Geht nicht in Steam. Du kannst nur einschränken, nie Alternativen kombinieren.

Unsere Smart Collections sprengen diese Limitierung mit vollständiger **boolescher Logik**:

- **UND / ODER / NICHT** Operatoren mit **verschachtelten Regelgruppen** — kombiniere beliebig viele Bedingungen
- Filtere nach **Spielzeitbereichen**, **Bewertungen**, **Steam Deck-Kompatibilität**, **ProtonDB-Ratings**, **Achievement-Fortschritt**, **HowLongToBeat-Zeiten**, **Tags**, **Genres** und mehr
- Kollektionen **aktualisieren sich selbst** sobald sich deine Bibliotheksdaten ändern
- **Import & Export** als JSON — teile deine Setups mit Freunden oder sichere sie

Der Clou: Im Steam Client erscheinen unsere Smart Collections als **ganz normale statische Kollektionen** — Steam merkt keinen Unterschied. Aber in SLM sind sie volldynamisch und unendlich mächtiger als alles was Steam bietet.

*Beispiel: "Zeige mir alle Spiele mit 'Platinum' auf ProtonDB, über 20 Stunden Spielzeit, die ich noch nicht zu 100% abgeschlossen habe — aber ohne 'Visual Novels'."*
Eine Kollektion. Automatisch. Immer aktuell. **In Steam unmöglich.**

<p align="center">
  <img src="resources/screenshots/de_02_smart_collections_editor.webp" alt="Smart Collections Editor (Deutsch)" width="800">
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="resources/images/readme_divider_dark.webp">
    <source media="(prefers-color-scheme: light)" srcset="resources/images/readme_divider_light.webp">
    <img src="resources/images/readme_divider_light.webp" alt="" width="800">
  </picture>
</p>

### 💛 Unterstütze dieses Projekt

Wenn SLM dir hilft deine Bibliothek zu organisieren, denk darüber nach die Entwicklung zu unterstützen. Jeder Beitrag — egal wie klein — hilft dieses Projekt am Leben zu halten.

<p align="center">
  <a href="https://www.paypal.com/donate/?hosted_button_id=HWPG6YAGXAWJJ">
    <img src="resources/images/paypal_de.webp" alt="Unterstütze uns auf PayPal" height="80">
  </a>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <a href="https://ko-fi.com/S6S51T9G3Y">
    <img src="resources/images/ko-fi_de.webp" alt="Unterstütze uns auf Ko-fi" height="80">
  </a>
</p>

<p align="center"><i>Danke an alle die schon etwas gegeben haben — ihr seid großartig! 🙏</i></p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="resources/images/readme_divider_dark.webp">
    <source media="(prefers-color-scheme: light)" srcset="resources/images/readme_divider_light.webp">
    <img src="resources/images/readme_divider_light.webp" alt="" width="800">
  </picture>
</p>

### 🏷️ Auto-Kategorisierung — *16 Regeltypen, unendliche Möglichkeiten*

Organisiere deine gesamte Bibliothek automatisch in sinnvolle Kollektionen mit **16 verschiedenen AutoCat-Regeltypen**:

**Tags** · **Genres** · **Publisher** · **Entwickler** · **Franchises** · **Flags** · **User Score** · **HowLongToBeat** · **Name** · **VR-Unterstützung** · **Sprache** · **Kurator** · **Plattform** · **Spielstunden** · **Manuell** · **Gruppe**

Jeder Regeltyp hat eigene Konfigurationsmöglichkeiten — Schwellenwerte, Ignorier-Listen, Präfix/Suffix-Muster und die Kombination mehrerer Regeln zu leistungsstarken Kategorisierungsprofilen. Intelligente Ignorier-Listen filtern generische Tags wie "Singleplayer" heraus.

*500+ Spiele? Klick auf "Auto-Kategorisieren" und schau zu wie sie sich in Sekunden in saubere, logische Kollektionen sortieren.*

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="resources/images/readme_divider_dark.webp">
    <source media="(prefers-color-scheme: light)" srcset="resources/images/readme_divider_light.webp">
    <img src="resources/images/readme_divider_light.webp" alt="" width="800">
  </picture>
</p>

### ✏️ Metadaten-Editor — *Deine Änderungen überleben Steam-Updates*

Bearbeite Spielnamen, Sortiertitel, Entwickler, Publisher und Erscheinungsdaten — alles lokal gespeichert. Was das besonders macht:

- **Overlay-System:** Deine Änderungen werden getrennt von Steams Daten gespeichert. Wenn Steam die `appinfo.vdf` überschreibt (was regelmäßig passiert), werden deine Änderungen **automatisch erneut angewendet**. Wie Git-Rebasing für Metadaten — Steam liefert den "Upstream", deine Änderungen sind die "Patches".
- **Bulk-Edit:** Hunderte Spiele auswählen, ein Feld ändern, anwenden. Fertig.
- **Eigene Sortiertitel:** "The Witcher 3" unter "W" einsortieren statt unter "T".

*Kein anderes Steam-Library-Tool kann das. Depressurizer verliert deine Änderungen bei Steam-Updates. Wir nicht.*

<p align="center">
  <img src="resources/screenshots/de_06_metadata_editor.webp" alt="Metadaten-Editor (Deutsch)" width="800">
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="resources/images/readme_divider_dark.webp">
    <source media="(prefers-color-scheme: light)" srcset="resources/images/readme_divider_light.webp">
    <img src="resources/images/readme_divider_light.webp" alt="" width="800">
  </picture>
</p>

### 🖼️ Artwork-Manager — *SteamGridDB auf Knopfdruck*

Durchsuche und lade **Cover, Heroes, Logos und Icons** von [SteamGridDB](https://www.steamgriddb.com/) herunter — der größten Community-getriebenen Spiele-Artwork-Datenbank.

- **Visueller Browser** mit Vorschaubildern — sieh was du auswählst bevor du es anwendest
- **Filtere nach Typ:** statisch, animiert (GIF/APNG/WebM), NSFW, Humor, Epilepsie-Warnung
- **Badge-System** mit animierten Slide-Down-Indikatoren — farbige Streifen zeigen Inhalts-Tags auf einen Blick
- **Ein Klick zum Anwenden** — Artwork wird heruntergeladen und sofort als Cover gesetzt

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="resources/images/readme_divider_dark.webp">
    <source media="(prefers-color-scheme: light)" srcset="resources/images/readme_divider_light.webp">
    <img src="resources/images/readme_divider_light.webp" alt="" width="800">
  </picture>
</p>

### 📊 Daten-Anreicherung — *Wisse alles über deine Spiele*

Reichere deine gesamte Bibliothek im Batch mit Daten aus mehreren Quellen an — alles lokal in SQLite gecacht für sofortigen Zugriff:

| Quelle | Daten | API-Key nötig? |
|--------|-------|:-:|
| **HowLongToBeat** | Hauptstory, Komplett, alle Spielstile | Nein |
| **ProtonDB** | Linux-Kompatibilität (Platinum/Gold/Silver/Bronze/Borked) | Nein |
| **Steam Achievements** | Abschlussquote pro Spiel | Nein (mit OAuth2) |
| **Steam Tags** | Community-Tags direkt aus Steam importiert | Nein (mit OAuth2) |
| **Steam Store** | Beschreibungen, DLC-Info, Altersfreigaben | Nein |

*Klick auf "Alle anreichern" und hol dir einen Kaffee. Wenn du zurückkommst hat jedes Spiel vollständige Metadaten.*

<p align="center">
  <img src="resources/screenshots/de_11_game_detail_panel.webp" alt="Spiel-Detailansicht mit allen Daten (Deutsch)" width="800">
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="resources/images/readme_divider_dark.webp">
    <source media="(prefers-color-scheme: light)" srcset="resources/images/readme_divider_light.webp">
    <img src="resources/images/readme_divider_light.webp" alt="" width="800">
  </picture>
</p>

### 🔒 Sicherheit — *Kein Copy-Paste, kein Klartext*

- **QR-Code-Login** oder Passwort-Login über Steams offizielles **OAuth2** (`IAuthenticationService`)
- Tokens **verschlüsselt** (AES-GCM) mit maschinengebundenen Schlüsseln oder im **System-Keyring** gespeichert
- Automatische **Token-Erneuerung** — kein erneutes Anmelden bei jedem App-Start
- Der **Steam Web API Key** ist dank OAuth2 **optional** — wird aber für volle Funktionalität **dringend empfohlen**. Konfiguration direkt in der App unter Einstellungen.

*Keine dubiosen Browser-Session-Tokens. Keine API-Keys in Klartext-Konfigdateien. Einfach scannen, einloggen, fertig.*

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="resources/images/readme_divider_dark.webp">
    <source media="(prefers-color-scheme: light)" srcset="resources/images/readme_divider_light.webp">
    <img src="resources/images/readme_divider_light.webp" alt="" width="800">
  </picture>
</p>

### 🌍 Mehrsprachig — *Deine Sprache, dein Weg*

Vollständige **Englisch 🇬🇧** und **Deutsch 🇩🇪** Oberfläche mit **kompletter i18n** — null hardcodierte Strings im gesamten Code.

- **Getrennte Einstellungen** für UI-Sprache und Tag-Sprache — englische Oberfläche mit deutschen Steam-Kategorien, oder jede beliebige Kombination
- **Lokalisierte Datumsformate** — "07. Dez 2024" auf Deutsch, "07 Dec 2024" auf Englisch
- **Community-Übersetzungen willkommen** — Beitragen ist einfach, keine Programmierkenntnisse nötig ([siehe unten](#-übersetzungen))

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="resources/images/readme_divider_dark.webp">
    <source media="(prefers-color-scheme: light)" srcset="resources/images/readme_divider_light.webp">
    <img src="resources/images/readme_divider_light.webp" alt="" width="800">
  </picture>
</p>

### 🐧 Linux Native — *Hier gebaut, für hier gemacht*

Entwickelt mit **PyQt6** für nahtlose Desktop-Integration. Das ist keine Windows-App mit angeschraubtem Linux-Port — es ist **auf Linux gebaut, für Linux**, von Tag eins an.

- **Steam Deck kompatibel** — funktioniert im Desktop-Modus
- **Wayland & X11** unterstützt
- **Flatpak & AppImage** Pakete (AUR kommt bald)
- Windows-Unterstützung ist geplant — aber Linux hat immer Vorrang

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="resources/images/readme_divider_dark.webp">
    <source media="(prefers-color-scheme: light)" srcset="resources/images/readme_divider_light.webp">
    <img src="resources/images/readme_divider_light.webp" alt="" width="800">
  </picture>
</p>

### 🎮 Externe Spiele — *Eine Bibliothek für alles*

Spiele verstreut über Epic, GOG, Amazon, Lutris, Bottles, itch.io und Flatpak? **SLM findet sie alle** — und fügt sie in einem Rutsch als Non-Steam-Shortcuts zu Steam hinzu.

- **8 Plattform-Parser** — Heroic (Epic/GOG/Amazon), Lutris, Bottles, itch.io, Flatpak und bestehende shortcuts.vdf
- **Auto-Erkennung** — SLM scannt nach installierten Launchern (nativ und Flatpak) und liest deren Spielebibliotheken direkt aus. Steams „Steam fremdes Spiel hinzufügen"-Dialog sieht nur Programme in deinem PATH — er hat keine Ahnung was Heroic, Lutris oder Bottles installiert haben
- **Duplikat-Schutz** — bereits in Steam vorhandene Spiele werden erkannt und übersprungen
- **Plattform-Kollektionen** — importierte Spiele werden automatisch nach Plattform in Steam-Kollektionen einsortiert. In SLMs Seitenleiste bekommt jede Kollektion einen visuellen Emoji-Indikator zur sofortigen Erkennung:

| Kollektion | Indikator |
|---|---|
| Epic Games 🟦 | Blau (Epic-Markenfarbe) |
| GOG Galaxy 🟣 | Lila (GOG-Markenfarbe) |
| Amazon Games 🟠 | Orange (Amazon-Markenfarbe) |
| Lutris 🎮 | Controller |
| Bottles 🍾 | Flasche |
| itch.io 🎲 | Würfel |
| Flatpak 📦 | Paket |

- **Binärer VDF-Parser** — liest und schreibt Steams `shortcuts.vdf`-Format mit Byte-genauer Präzision
- **Batch-Import** — alle Plattformen auf einmal scannen, auswählen, alle mit Fortschrittsanzeige hinzufügen

*Steams eigener „Steam fremdes Spiel hinzufügen"-Dialog kann zwar mehrere Apps markieren — aber er sieht nur was in deinem PATH liegt, nicht deine tatsächlichen Spielebibliotheken. SLM scannt Heroic, Lutris, Bottles und mehr direkt, weiß genau was installiert ist, und organisiert alles automatisch in saubere Kollektionen.*

<p align="center">
  <img src="resources/screenshots/17_external_games.webp" alt="External Games Manager — Scannen und Importieren" width="800">
</p>


## 📦 Download & Installation

| Format | Download | Hinweise |
|--------|----------|----------|
| 🐧 **AppImage** | [Neueste Version](https://github.com/Switch-Bros/SteamLibraryManager/releases) | Funktioniert auf jeder Distro — herunterladen, chmod +x, starten |
| 📦 **Flatpak** | *Kommt bald* | Sandboxed, Auto-Updates |
| 🏗️ **AUR** | *Kommt bald* | Arch / Manjaro / CachyOS / EndeavourOS |

<details>
<summary>🔧 Aus Quellcode bauen (für Entwickler)</summary>

```bash
# Klonen
git clone https://github.com/Switch-Bros/SteamLibraryManager.git
cd SteamLibraryManager

# Virtuelle Umgebung
python3 -m venv .venv
source .venv/bin/activate

# Abhängigkeiten
pip install -r requirements.txt

# Starten
python src/main.py
```

Benötigt **Python 3.10+** und einen laufenden **Steam Client** (nicht Big Picture).

</details>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="resources/images/readme_divider_dark.webp">
    <source media="(prefers-color-scheme: light)" srcset="resources/images/readme_divider_light.webp">
    <img src="resources/images/readme_divider_light.webp" alt="" width="800">
  </picture>
</p>

<details>
<summary><h2>🔧 API- & Authentifizierungs-Anforderungen</h2></summary>

Dieses Projekt nutzt folgende Dienste:

### **1. Steam-Authentifizierung (OAuth2)**
- **Zweck:** Anmeldung mit deinem Steam-Konto für Zugriff auf deine Bibliothek und Anzeige deines Profilnamens.
- **Funktionsweise:**
  - Nutzt Steams offizielles **OAuth2** über `IAuthenticationService` (QR-Code oder Passwort-Login).
  - Tokens werden **verschlüsselt** (AES-GCM) oder im System-Keyring gespeichert.
  - Der **Steam Web API Key** ist dank OAuth2 **optional** — wird aber für volle Funktionalität **dringend empfohlen** (Metadaten-Anreicherung, Achievement-Sync etc.).
  - Du kannst deinen API-Key direkt in der App unter **Einstellungen → Steam Web API Key** eintragen.
  - Key hier beantragen: [Steam Web API Key](https://steamcommunity.com/dev/apikey)

### **2. SteamGridDB**
- **Erforderlich für:** Anpassung von Spiel-Covern, Heroes, Logos und Icons.
- **So erhältst du den API-Schlüssel:**
  - Die App **fragt automatisch** nach dem SteamGridDB-API-Schlüssel, sobald du zum ersten Mal auf ein Spiel-Cover klickst.
  - Es öffnet sich ein Fenster, in dem du:
    1. **Deinen API-Schlüssel** von [SteamGridDB](https://www.steamgriddb.com/api) holst.
    2. **Den Schlüssel** in das Eingabefeld der App einfügst.
    3. Auf **OK** klickst – der Schlüssel wird lokal gespeichert, und die Cover-Funktionen sind sofort nutzbar!
  - **Hinweis:** Nutzer müssen die [Nutzungsbedingungen von SteamGridDB](https://www.steamgriddb.com/terms) einhalten.

### **3. HowLongToBeat (HLTB)**
- **Enthalten für:** Anzeige von Spielzeiten und Auto-Kategorisierung nach Spielzeitbereichen.
- **Kein API-Key nötig.** Daten werden automatisch abgerufen und lokal gecacht.
- **Hinweis:** HLTB bietet keine offizielle öffentliche API an. Die Integration respektiert deren [Nutzungsbedingungen](https://howlongtobeat.com/).

### **4. ProtonDB**
- **Enthalten für:** Linux/Proton-Kompatibilitätsbewertungen.
- **Kein API-Key nötig.** Lesender Zugriff, lokal gecacht mit 7-Tage TTL.

</details>


## 🗺️ Roadmap

| Meilenstein | Status |
|-------------|--------|
| Core-Engine, Datenbank, Cloud Sync, Auth | ✅ Fertig |
| Architektur-Refactoring, Menü-Redesign | ✅ Fertig |
| Depressurizer Feature-Parität (16 AutoCat-Typen) | ✅ Fertig |
| Smart Collections, Steam Deck Optimizer, HLTB | ✅ Fertig |
| Externe Spiele (8 Parser), ProtonDB, Kuratoren | ✅ Fertig |
| UI-Polish, Keyboard Shortcuts, Dokumentation | ✅ Fertig |
| **Erste öffentliche Veröffentlichung** | 🔜 **Kommt bald** |
| CI/CD-Pipeline (automatisierte Flatpak/AppImage Builds) | 🔄 In Arbeit |
| Windows-Unterstützung | 📋 Geplant |


## 🌍 Übersetzungen

Steam Library Manager kommt mit **Englisch** und **Deutsch**. Du willst es in deiner Sprache sehen?

**Eine Übersetzung beizutragen ist einfach — keine Programmierkenntnisse nötig!**

1. Kopiere eine beliebige JSON-Datei aus `resources/i18n/en/` als Vorlage
2. Übersetze die Werte (niemals die Keys ändern!)
3. Platzhalter wie `{count}` und `{name}` unverändert lassen
4. Deine Sprache in `resources/i18n/languages.json` eintragen:
   ```json
   "tr": "🇹🇷  Türkçe"
   ```
5. Pull Request erstellen

Der Sprachname muss immer in der **eigenen Originalschrift** stehen — "Türkçe", nicht "Turkish".


## 🛡️ Datenschutz & Sicherheit

- **Keine Telemetrie.** Steam Library Manager telefoniert nicht nach Hause.
- **Keine Datenerfassung.** Deine Bibliothek, deine Daten, dein Rechner.
- **Token-Verschlüsselung.** Steam-Zugangsdaten mit AES-GCM verschlüsselt oder im System-Keyring.
- **API-Keys lokal gespeichert.** Werden niemals an Dritte übermittelt.
- **Automatische Backups.** Vor jedem Schreibvorgang auf Steam-Dateien wird ein Backup erstellt.


## 🤝 Mitmachen

- 🐛 **Bug gefunden?** → [Issue erstellen](https://github.com/Switch-Bros/SteamLibraryManager/issues)
- 💡 **Idee?** → [Diskussion starten](https://github.com/Switch-Bros/SteamLibraryManager/discussions)
- 🌍 **Sprichst du eine andere Sprache?** → [Hilf beim Übersetzen!](#-übersetzungen)
- 🔧 **Willst du coden?** → Schau dir [`CLAUDE.md`](CLAUDE.md) für Architektur- & Coding-Guidelines an


## 🙏 Danksagungen

- [SteamGridDB](https://www.steamgriddb.com/) — Spiel-Artwork
- [HowLongToBeat](https://howlongtobeat.com/) — Spielzeit-Daten
- [ProtonDB](https://www.protondb.com/) — Linux-Kompatibilitätsbewertungen
- [SteamKit2](https://github.com/SteamRE/SteamKit) / [ValvePython/steam](https://github.com/solsticegamestudios/steam) — Steam-Protokoll-Forschung
- [steamapi.xpaw.me](https://steamapi.xpaw.me/) — Steam Web API Dokumentation


## ⚖️ Rechtlicher Hinweis

Diese Software wird **„WIE SIE IST"** bereitgestellt, ohne jegliche ausdrückliche oder stillschweigende Gewährleistung, einschließlich, aber nicht beschränkt auf die Gewährleistung der Marktgängigkeit, der Eignung für einen bestimmten Zweck und der Nichtverletzung von Rechten Dritter.

In keinem Fall haften die Autoren oder Urheberrechtsinhaber für Ansprüche, Schäden oder sonstige Haftung, ob aus Vertrag, unerlaubter Handlung oder anderweitig, die sich aus der Software oder der Nutzung der Software oder dem sonstigen Umgang mit der Software ergeben.

- Du **musst** die Nutzungsbedingungen der jeweiligen API-Anbieter (Steam, SteamGridDB, HLTB, ProtonDB) einhalten.
- Der Entwickler (**Switch Bros**) übernimmt **keine Verantwortung** für den Missbrauch von API-Schlüsseln oder Verstöße gegen die Nutzungsbedingungen Dritter.
- API-Schlüssel werden **lokal gespeichert** und **niemals** an Dritte übermittelt.
- Steam Library Manager ist **nicht verbunden mit, unterstützt von oder assoziiert mit Valve Corporation** oder einem anderen Drittanbieter-Dienst.


## 📜 Lizenz

[MIT License](LICENSE) — Copyright © 2026 Switch Bros.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="resources/images/readme_footer_dark.webp">
    <source media="(prefers-color-scheme: light)" srcset="resources/images/readme_footer_light.webp">
    <img src="resources/images/readme_footer_light.webp" alt="" width="800">
  </picture>
</p>

<p align="center">
  Mit ❤️ auf Linux gebaut von <a href="https://github.com/Switch-Bros">Switch Bros</a>
</p>
