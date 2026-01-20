#!/usr/bin/env python3
"""
Steam Library Manager - Main Entry Point (PyQt6 Version)
Speichern als: src/main.py
"""
import sys
from pathlib import Path

# Add project root to path (works from anywhere)
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication
from src.config import config
from src.utils.i18n import init_i18n, t
from src.ui.main_window import MainWindow


def main():
    # 1. Sprache initialisieren
    init_i18n(config.DEFAULT_LOCALE)

    # 2. Start-Logs
    print("=" * 60)
    print(t('cli.banner'))
    print("=" * 60)

    print(t('cli.initializing'))

    if config.STEAM_PATH:
        print(t('cli.steam_found', path=config.STEAM_PATH))

        # FIX: Nutze die neue intelligente Erkennung statt der alten Funktion
        short_id, long_id = config.get_detected_user()
        if short_id:
            # Wir haben einen User gefunden
            print(t('cli.users_found', count=1))

            # Falls noch keine ID in der Config steht, nehmen wir die erkannte
            if not config.STEAM_USER_ID and long_id:
                config.STEAM_USER_ID = long_id
    else:
        print(t('cli.steam_not_found'))

    print(f"\n{t('cli.starting')}\n")

    try:
        app = QApplication(sys.argv)
        app.setApplicationName("Steam Library Manager")

        # Qt automatically detects and applies system theme
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