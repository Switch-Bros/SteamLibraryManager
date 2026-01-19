#!/usr/bin/env python3
"""
Auto-Restore Script
Stellt Metadaten-Änderungen automatisch wieder her wenn Steam sie überschreibt
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.appinfo_manager import AppInfoManager
from src.config import config


def main():
    """Main auto-restore function"""
    print("=" * 60)
    print("🔄  Steam Library Manager - Auto-Restore")
    print("=" * 60)
    
    if not config.STEAM_PATH:
        print("❌ Steam path not found")
        return 1
    
    # Create manager
    manager = AppInfoManager(config.STEAM_PATH)
    
    # Check if we have modifications
    mod_count = manager.get_modification_count()
    
    if mod_count == 0:
        print("✓ No modifications to restore")
        return 0
    
    print(f"\n📝 Found {mod_count} tracked modifications")
    print("🔄 Restoring changes...")
    
    # Load appinfo
    data = manager.load_appinfo()
    
    if not data:
        print("❌ Failed to load appinfo.vdf")
        return 1
    
    # Restore modifications
    restored = manager.restore_modifications(data)
    
    if restored > 0:
        # Save back
        print("\n💾 Saving changes...")
        if manager.save_appinfo(data, create_backup=True):
            print(f"✅ Successfully restored {restored} modifications!")
            print(f"   Backup created in: {manager.backup_dir}")
            return 0
        else:
            print("❌ Failed to save changes")
            return 1
    else:
        print("⚠️  No changes were restored")
        return 0


if __name__ == "__main__":
    sys.exit(main())
