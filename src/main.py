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
from src.utils.i18n import init_i18n
from src.ui.main_window import MainWindow


def main():
    print("=" * 60)
    print("🎮  Steam Library Manager v1.0 (PyQt6)")
    print("=" * 60)

    print("🌍 Initializing...")
    init_i18n(config.DEFAULT_LOCALE)

    if config.STEAM_PATH:
        print(f"✅ Steam found at: {config.STEAM_PATH}")
        user_ids = config.get_all_user_ids()
        if user_ids:
            print(f"👤 Found {len(user_ids)} Steam user(s)")
            if not config.STEAM_USER_ID and len(user_ids) == 1:
                config.STEAM_USER_ID = user_ids[0]
    else:
        print("⚠️  Steam not found")

    print("\n🚀 Starting application with PyQt6...\n")

    try:
        app = QApplication(sys.argv)
        app.setApplicationName("Steam Library Manager")

        # Qt automatically detects and applies system theme (KDE Breeze, GNOME Adwaita, etc.)
        print("✓ Using native Qt theme")

        window = MainWindow()
        window.show()

        sys.exit(app.exec())

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()