# 🎮 Steam Library Manager

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Steam%20Deck-FCC624?style=for-the-badge&logo=linux&logoColor=black)](https://store.steampowered.com/steamdeck)
[![Made with PyCharm](https://img.shields.io/badge/Made%20with-PyCharm-000000?style=for-the-badge&logo=pycharm&logoColor=white)](https://www.jetbrains.com/pycharm/)
[![Status](https://img.shields.io/badge/Status-In%20Development-orange?style=for-the-badge)]()
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)]()

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
