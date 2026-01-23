#!/usr/bin/env python3
"""
Steam Library Manager - Main Entry Point (PyQt6 Version)
Speichern als: src/main.py
"""
import sys
from pathlib import Path

# Projekt-Wurzelverzeichnis zum Pfad hinzufügen
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.utils import acf, appinfo
from PyQt6.QtWidgets import QApplication, QMessageBox
from src.config import config
from src.utils.i18n import init_i18n, t
from src.ui.main_window import MainWindow


def check_steam_running() -> bool:
    """
    Prüft ob Steam gerade läuft
    Returns: True wenn Steam läuft, False, wenn nicht
    """
    try:
        import psutil
        for proc in psutil.process_iter(['name']):
            try:
                proc_name = proc.info['name'].lower()
                # Prüfe verschiedene Steam-Prozesse
                if proc_name in ['steam', 'steam.exe', 'steamwebhelper', 'steamwebhelper.exe']:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    except ImportError:
        # psutil nicht installiert - überspringen
        print("Warning: psutil not installed, cannot check if Steam is running")
        return False
    except Exception as e:
        print(f"Error checking Steam processes: {e}")
        return False


def load_steam_file(file_path: Path):
    """
    Lädt eine Steam-Datei basierend auf ihrer Endung/Namen.
    """
    if not file_path.exists():
        return None

    ext = file_path.suffix.lower()
    name = file_path.name.lower()

    try:
        # Prüfung auf Text-VDF Formate
        if ext == '.acf' or name == 'localconfig.vdf':
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return acf.load(f)

        # Prüfung auf Binär-VDF (AppInfo)
        elif name == 'appinfo.vdf':
            with open(file_path, 'rb') as f:
                return appinfo.load(f)

        # Manifest support entfernt (nicht benötigt)

    except Exception as e:
        print(f"Fehler beim Laden der Datei {file_path.name}: {e}")
        return None

    return None


def main():
    # 1. Sprache initialisieren (VORHER für Warnung!)
    init_i18n(config.DEFAULT_LOCALE)

    # 2. QApplication erstellen (VORHER für MessageBox!)
    app = QApplication(sys.argv)
    app.setApplicationName("Steam Library Manager")

    # 3. KRITISCH: Prüfe ob Steam läuft!
    if check_steam_running():
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(t('ui.dialogs.steam_running_title'))
        msg.setText(t('ui.dialogs.steam_running_message'))

        # Exit Button
        exit_btn = msg.addButton(
            t('ui.dialogs.steam_running_button'),
            QMessageBox.ButtonRole.AcceptRole
        )
        exit_btn.setDefault(True)  # ← Variable wird jetzt verwendet!

        msg.exec()

        # App beenden
        print("\n⚠️ Steam is running - exiting application")
        sys.exit(0)

    # 4. Start-Logs
    print("=" * 60)
    print(t('cli.banner'))
    print("=" * 60)

    print(t('cli.initializing'))

    if config.STEAM_PATH:
        print(t('cli.steam_found', path=config.STEAM_PATH))

        short_id, long_id = config.get_detected_user()
        if short_id:
            print(t('cli.users_found', count=1))

            if not config.STEAM_USER_ID and long_id:
                config.STEAM_USER_ID = long_id
    else:
        print(t('cli.steam_not_found'))

    print(f"\n{t('cli.starting')}\n")

    try:
        print(t('cli.qt_theme'))

        window = MainWindow()
        window.show()

        sys.exit(app.exec())

    except Exception as e:
        print(f"\n{t('cli.error', error=e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()