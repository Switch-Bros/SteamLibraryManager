#!/usr/bin/env python3
"""
Steam Library Manager - Main Entry Point (PyQt6 Version)
"""
import sys
import traceback
from pathlib import Path
from typing import Any

# Add project root directory to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Local imports
from src.utils import acf, appinfo
from src.config import config
from src.utils.i18n import init_i18n, t
from src.ui.main_window import MainWindow

# PyQt6 imports
from PyQt6.QtWidgets import QApplication, QMessageBox


def check_steam_running() -> bool:
    """
    Check if Steam is currently running using psutil.

    Returns:
        bool: True if Steam is running, False otherwise.
    """
    try:
        import psutil
        for proc in psutil.process_iter(['name']):
            try:
                proc_name = proc.info['name'].lower()
                # Check various Steam processes
                if proc_name in ['steam', 'steam.exe', 'steamwebhelper', 'steamwebhelper.exe']:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    except ImportError:
        # Log warning using i18n
        print(t('logs.main.psutil_missing'))
        return False
    except Exception as e:
        print(f"Error checking Steam processes: {e}")
        return False


def load_steam_file(file_path: Path) -> Any:
    """
    Load a Steam file based on its extension/name (.acf or .vdf).

    Args:
        file_path: Path to the file.

    Returns:
        Any: The parsed data (dict or AppInfo object) or None if loading failed.
    """
    if not file_path.exists():
        return None

    ext = file_path.suffix.lower()
    name = file_path.name.lower()

    try:
        # Check for text VDF formats
        if ext == '.acf' or name == 'localconfig.vdf':
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return acf.load(f)

        # Check for binary VDF (AppInfo)
        elif name == 'appinfo.vdf':
            with open(file_path, 'rb') as f:
                return appinfo.load(f)

    except Exception as e:
        print(t('logs.main.file_load_error', file=file_path.name, error=str(e)))
        return None

    return None


def main() -> None:
    """Main application execution flow."""
    # 1. Initialize language (BEFORE creating UI elements)
    init_i18n(config.UI_LANGUAGE)

    # 2. Create QApplication
    app = QApplication(sys.argv)
    # Keeping this hardcoded as requested (Brand Name)
    app.setApplicationName("Steam Library Manager")

    # 3. CRITICAL: Check if Steam is running!
    if check_steam_running():
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(t('ui.dialogs.steam_running_title'))
        msg.setText(t('ui.dialogs.steam_running_msg'))

        # Exit Button (using "Exit" from menu translations)
        exit_btn = msg.addButton(
            t('common.exit'),
            QMessageBox.ButtonRole.AcceptRole
        )
        exit_btn.setDefault(True)

        msg.exec()

        # Exit app with log
        print(f"\n{t('emoji.warning')} {t('logs.main.steam_running_exit')}")
        sys.exit(0)

    # 4. Check if user profile is configured
    if not config.STEAM_USER_ID:
        # First-time setup: Show profile selection dialog
        from src.ui.dialogs.profile_setup_dialog import ProfileSetupDialog
        
        print(t('logs.main.profile_setup_required'))
        
        dialog = ProfileSetupDialog(steam_path=config.STEAM_PATH)
        result = dialog.exec()
        
        if result == ProfileSetupDialog.DialogCode.Accepted:
            # User selected an account
            config.STEAM_USER_ID = str(dialog.selected_steam_id_64)
            config.save()
            
            print(t('logs.main.profile_configured', 
                   name=dialog.selected_display_name, 
                   id=dialog.selected_steam_id_64))
        else:
            # User cancelled setup
            print(f"\n{t('logs.main.setup_cancelled')}")
            sys.exit(0)
    
    # 5. Startup logs
    print("=" * 60)
    print(t('app.name'))
    print("=" * 60)

    print(t('logs.main.initializing'))

    if config.STEAM_PATH:
        print(t('logs.main.steam_found', path=config.STEAM_PATH))

        # User detection is handled in MainWindow._load_data()
        # STEAM_USER_ID is only set via explicit Steam login, not auto-detection
    else:
        print(t('logs.main.steam_not_found'))

    print(f"\n{t('common.loading')}\n")

    try:
        window = MainWindow()
        window.show()

        sys.exit(app.exec())

    except Exception as e:
        print(f"\n{t('common.error')}: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()