# 🎮 Steam Library Manager

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-FDE100?style=plastic&logo=python&logoColor=FDE100&labelColor=000000)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Steam%20Deck-FDE100?style=plastic&logo=linux&logoColor=FDE100&labelColor=000000)](https://store.steampowered.com/steamdeck)
[![made with PyCharm](https://img.shields.io/badge/made%20with-PyCharm-FDE100?style=plastic&logo=pycharm&color=FDE100&labelColor=000000)](https://www.jetbrains.com/pycharm/)
[![Status](https://img.shields.io/badge/Status-In%20Development-FDE100?style=plastic&labelColor=000000)](https://github.com/HeikesFootSlave/SteamLibraryManager)
[![License](https://img.shields.io/badge/License-MIT-FDE100?style=plastic&labelColor=000000)](https://github.com/HeikesFootSlave/SteamLibraryManager/blob/main/LICENSE)
[![Steam API](https://img.shields.io/badge/Steam%20API-Required-FDE100?style=plastic&logo=steam&logoColor=FDE100&labelColor=000000)](https://steamcommunity.com/dev/apikey)
[![SteamGridDB](https://img.shields.io/badge/SteamGridDB-Required-FDE100?style=plastic&logo=steam&logoColor=FDE100&labelColor=000000)](https://www.steamgriddb.com/api)
[![ProtonDB](https://img.shields.io/badge/ProtonDB-Included-FDE100?style=plastic&logo=linux&logoColor=FDE100&labelColor=000000)](https://www.protondb.com/)
[![HLTB](https://img.shields.io/badge/HLTB-Planned-FDE100?style=plastic&logo=howlongtobeat&logoColor=FDE100&labelColor=000000)](https://howlongtobeat.com/)
[![Downloads](https://img.shields.io/badge/Downloads-Coming%20Soon-FDE100?style=plastic&logo=github&logoColor=FDE100&labelColor=000000)](https://github.com/Switch-Bros/SteamLibraryManager/releases)
<!-- [![Downloads](https://img.shields.io/github/downloads/Switch-Bros/SteamLibraryManager/total?color=FDE100&labelColor=000000&style=plastic&logo=github&logoColor=FDE100&label=Downloads&labelColor=000000)](https://github.com/Switch-Bros/SteamLibraryManager/releases) -->

[![Donate](https://img.shields.io/badge/Donate-Consider%20Supporting%20me%20on%20PayPal-FDE100?style=plastic&logo=paypal&logoColor=FDE100&labelColor=000000)](https://www.paypal.com/donate/?hosted_button_id=HWPG6YAGXAWJJ)

<details>
  <summary><h2>🔧 API & Authentication Requirements <small>(english)</small></h2></summary>

  This project uses the following services:

  ### **1. Steam Authentication**
  - **Purpose:** Users can log in with their Steam account to display their **Steam profile name** in the app.
  - **How it works:**
    - Uses Steam's **OpenID/Steamworks** for authentication.
    - **No Steam Web API key required** (only standard Steam login flow).
    - **No user data** (beyond the profile name) is stored or retrieved.

  ### **2. SteamGridDB**
  - **Required for:** Customizing game covers and assets.
  - **How to get the API key:**
    - The app **automatically prompts** for the SteamGridDB API key when you click on a game cover for the first time.
    - A window will open where you can:
      1. **Get your API key** from [SteamGridDB](https://www.steamgriddb.com/api).
      2. **Paste the key** into the app's input field.
      3. Click **OK** – the key is saved locally, and covers are ready to use!
    - **Note:** Users must comply with [SteamGridDB's Terms of Service](https://www.steamgriddb.com/terms).

  ### **3. HowLongToBeat (HLTB)**
  - **Planned for:** Displaying game completion times.
  - **Note:** HLTB does not officially provide a public API. Integration will respect their [terms](https://howlongtobeat.com/).

  ### **4. ProtonDB**
  - **Required for:** Checking Linux/Proton compatibility for games.
  - **Note:** No API key is required for read-only access.

  ---
  ### **Important Legal Notice**
  - You **must** comply with the terms of service of each API provider.
  - The developer (**HeikesFootSlave**) is **not responsible** for misuse of API keys or violations of third-party terms.
  - API keys (e.g., for SteamGridDB) are **stored locally** (Base64-encoded) and **never transmitted**.

  ---
  ### **How to Configure**
  1. Log in with Steam to display your profile name.
  2. Click on a game cover to **automatically trigger the SteamGridDB API key setup**.
  3. Follow the in-app instructions to **paste your key** and start customizing covers!
</details>
<details>
  <summary><h2>🔧 API- & Authentifizierungs-Anforderungen <small>(deutsch)</small></h2></summary>

  Dieses Projekt nutzt folgende Dienste:

  ### **1. Steam-Authentifizierung**
  - **Zweck:** Nutzer können sich mit ihrem Steam-Konto anmelden, um ihren **Steam-Profilnamen** in der App anzuzeigen.
  - **Funktionsweise:**
    - Nutzt **OpenID/Steamworks** von Steam für die Authentifizierung.
    - **Kein Steam-Web-API-Schlüssel nötig** (nur der Standard-Steam-Login-Prozess).
    - **Keine Nutzerdaten** (außer dem Profilnamen) werden gespeichert oder abgerufen.

  ### **2. SteamGridDB**
  - **Erforderlich für:** Anpassung von Spiel-Covern und Assets.
  - **So erhältst du den API-Schlüssel:**
    - Die App **fragt automatisch** nach dem SteamGridDB-API-Schlüssel, sobald du zum ersten Mal auf ein Spiel-Cover klickst.
    - Es öffnet sich ein Fenster, in dem du:
      1. **Deinen API-Schlüssel** von [SteamGridDB](https://www.steamgriddb.com/api) holst.
      2. **Den Schlüssel** in das Eingabefeld der App einfügst.
      3. Auf **OK** klickst – der Schlüssel wird lokal gespeichert, und die Cover-Funktionen sind sofort nutzbar!
  - **Hinweis:** Nutzer müssen die [Nutzungsbedingungen von SteamGridDB](https://www.steamgriddb.com/terms) einhalten.

  ### **3. HowLongToBeat (HLTB)**
  - **Geplant für:** Anzeige von Spielzeiten.
  - **Hinweis:** HLTB bietet offiziell keine öffentliche API an. Die Integration wird deren [Nutzungsbedingungen](https://howlongtobeat.com/) respektieren.

  ### **4. ProtonDB**
  - **Erforderlich für:** Überprüfung der Linux/Proton-Kompatibilität von Spielen.
  - **Hinweis:** Kein API-Schlüssel nötig für den Lesezugriff.

  ---
  ### **Wichtiger rechtlicher Hinweis**
  - Du **musst** die Nutzungsbedingungen der jeweiligen API-Anbieter einhalten.
  - Der Entwickler (**HeikesFootSlave**) **übernimmt keine Haftung** für Missbrauch von API-Schlüsseln oder Verstöße gegen die Nutzungsbedingungen Dritter.
  - API-Schlüssel (z. B. für SteamGridDB) werden **lokal gespeichert** (Base64-kodiert) und **niemals übertragen**.

  ---
  ### **Konfiguration in der App**
  1. Melde dich mit Steam an, um deinen Profilnamen anzuzeigen.
  2. Klicke auf ein Spiel-Cover, um **automatisch den SteamGridDB-API-Schlüssel einzurichten**.
  3. Folge den Anweisungen in der App, um **deinen Schlüssel einzufügen** und Cover anzupassen!
</details>

---

## 🌍 **Steam Library Manager** *(English)*

A modern, powerful library manager for Steam on **Linux and Steam Deck**. Organize your collection, edit metadata, and automate categories.

> ⚠️ **Note:** This project is currently in **active development** (Alpha/Beta). Backups are created automatically, but use at your own risk.

---

### ✨ **Features**

* **🏷️ Auto-Categorization:**
  * Automatically create categories based on **Steam tags**, **genres**, **publishers**, or **franchises**.
  * Ignore generic tags (e.g., "Singleplayer", "Controller Support") automatically.

* **✏️ Metadata Editor:**
  * Edit game names, sort titles, developers, and release dates locally.
  * **Bulk Edit:** Change data for hundreds of games at once.

* **🌍 Multilingual (i18n):**
  * Full support for **German 🇩🇪** and **English 🇬🇧**.
  * Separate settings for UI language and tag language (e.g., English UI with German categories).

* **🔒 Secure:**
  * Automatic backup of `localconfig.vdf` and `appinfo.vdf` before any changes.
  * Built-in restore function.

* **🐧 Linux Native:**
  * Developed with **PyQt6** for seamless integration with Linux desktops.

---

### 🚀 **Installation & Startup**

Ensure you have **Python 3.10 or newer** installed.

```bash
# 1. Clone the repository
git clone https://github.com/Switch-Bros/SteamLibraryManager.git
cd SteamLibraryManager

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements-user.txt

# 4. Start the app
python src/main.py
```
---
## 🌍 **Steam Library Manager** *(Deutsch)*

Ein moderner, leistungsstarker Bibliotheks-Manager für Steam auf Linux und dem Steam Deck.  
Organisiere deine Sammlung, bearbeite Metadaten und automatisiere Kategorien.

> ⚠️ **Hinweis:** Dieses Projekt befindet sich aktuell in der aktiven Entwicklung (Alpha/Beta). Backups werden automatisch erstellt, aber Nutzung auf eigene Gefahr.

---

## ✨ Features

* **🏷️ Auto-Kategorisierung:**
    * Erstelle automatisch Kategorien basierend auf **Steam Tags**, **Genres**, **Publishern** oder **Franchises**.
    * Ignoriere generische Tags (wie "Singleplayer", "Controller Support") automatisch.
* **✏️ Metadaten-Editor:**
    * Bearbeite Spielnamen, Sortierungstitel, Entwickler und Release-Datum lokal.
    * **Bulk-Edit:** Ändere Daten für hunderte Spiele gleichzeitig.
* **🌍 Mehrsprachig (i18n):**
    * Vollständige Unterstützung für **Deutsch 🇩🇪** und **Englisch 🇬🇧**.
    * Getrennte Einstellung für UI-Sprache und Tag-Sprache (z.B. englische Oberfläche, aber deutsche Kategorien).
* **🔒 Sicher:**
    * Automatisches Backup von `localconfig.vdf` und `appinfo.vdf` vor jeder Änderung.
    * Wiederherstellungsfunktion integriert.
* **🐧 Linux Native:**
    * Entwickelt mit PyQt6 für optimale Integration in Linux-Desktops.

---

## 🚀 Installation & Start

Stelle sicher, dass du Python 3.10 oder neuer installiert hast.

```bash
# 1. Repository klonen
git clone [https://github.com/Switch-Bros/SteamLibraryManager.git](https://github.com/Switch-Bros/SteamLibraryManager.git)
cd steamlibrarymanager

# 2. Virtuelle Umgebung erstellen
python3 -m venv .venv
source .venv/bin/activate

# 3. Abhängigkeiten installieren
pip install -r requirements-user.txt

# 4. Starten
python src/main.py
```

---

☕ Support the Project:
Developing this tool takes time and caffeine. If it helps you tame your library, I’d be thrilled if you’d buy me a coffee!

[![17688665364546846464391088987251](https://github.com/user-attachments/assets/a2495674-be9e-4d64-bc23-058094635036)
](https://www.paypal.com/donate/?hosted_button_id=HWPG6YAGXAWJJ)

(Screenshots and detailed documentation coming soon!)

---

☕ Unterstütze das Projekt:
Die Entwicklung dieses Tools kostet Zeit und Koffein. Wenn dir der Manager hilft, deine Bibliothek zu bändigen, freue ich mich riesig über einen Kaffee!

[![17688665364546846464391088987251](https://github.com/user-attachments/assets/a2495674-be9e-4d64-bc23-058094635036)
](https://www.paypal.com/donate/?hosted_button_id=HWPG6YAGXAWJJ) 

(Screenshots und detaillierte Dokumentation folgen in Kürze)
