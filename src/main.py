#!/usr/bin/env python3
"""Steam Library Manager - Main Entry"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config
from src.utils.i18n import init_i18n
from src.ui.main_window import MainWindow

def main():
    print("=" * 60)
    print("🎮  Steam Library Manager v1.0")
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
    
    print("\n🚀 Starting application...\n")
    
    try:
        app = MainWindow()
        app.mainloop()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
