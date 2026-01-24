# 🎮 Steam Library Manager

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-FDE100?style=plastic&logo=python&logoColor=FDE100&labelColor=000000)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Steam%20Deck-FDE100?style=plastic&logo=linux&logoColor=FDE100&labelColor=000000)](https://store.steampowered.com/steamdeck)
[![made with PyCharm](https://img.shields.io/badge/made%20with-PyCharm-FDE100?style=plastic&logo=pycharm&color=FDE100&labelColor=000000)](https://www.jetbrains.com/pycharm/)
[![Status](https://img.shields.io/badge/Status-In%20Development-FDE100?style=plastic&labelColor=000000)](https://github.com/HeikesFootSlave/SteamLibraryManager)
[![License](https://img.shields.io/badge/License-MIT-FDE100?style=plastic&labelColor=000000)](https://github.com/HeikesFootSlave/SteamLibraryManager/blob/main/LICENSE)

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
git clone [https://github.com/HeikesFootSlave/steamlibrarymanager.git](https://github.com/HeikesFootSlave/steamlibrarymanager.git)
cd steamlibrarymanager

# 2. Virtuelle Umgebung erstellen
python3 -m venv .venv
source .venv/bin/activate

# 3. Abhängigkeiten installieren
pip install -r requirements.txt

# 4. Starten
python src/main.py
```

☕ Unterstütze das Projekt
Die Entwicklung dieses Tools kostet Zeit und Koffein. Wenn dir der Manager hilft, deine Bibliothek zu bändigen, freue ich mich riesig über einen Kaffee!

[![17688665364546846464391088987251](https://github.com/user-attachments/assets/a2495674-be9e-4d64-bc23-058094635036)
](https://www.paypal.com/donate/?hosted_button_id=HWPG6YAGXAWJJ) 

(Screenshots und detaillierte Dokumentation folgen in Kürze)
