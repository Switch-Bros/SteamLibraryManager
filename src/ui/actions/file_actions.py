# src/ui/actions/file_actions.py

"""
Action handler for File menu operations.

Extracts the following methods from MainWindow:
  - refresh_data()                  (reload all game data)
  - force_save()                    (explicit save trigger)
  - remove_duplicate_collections()  (cleanup duplicate categories)
  - show_vdf_merger()               (open VDF merge dialog)

All actions connect back to MainWindow for state access and UI updates.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

from src.ui.widgets.ui_helper import UIHelper
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow


class FileActions:
    """Handles all File menu actions.

    Owns no persistent state beyond a reference to MainWindow. Each action
    method delegates to the appropriate service or manager and triggers the
    standard save/populate/update cycle when data changes.

    Attributes:
        mw: Back-reference to the owning MainWindow instance.
    """

    def __init__(self, main_window: "MainWindow") -> None:
        """Initializes the FileActions handler.

        Args:
            main_window: The MainWindow instance that owns these actions.
        """
        self.mw: "MainWindow" = main_window

    # ------------------------------------------------------------------
    # Public API - File Actions
    # ------------------------------------------------------------------

    def refresh_data(self) -> None:
        """Reloads all game data from scratch.

        Triggers the full game loading pipeline via MainWindow._load_data().
        This includes:
          - Steam API fetch
          - Local file parsing (manifests, VDF, appinfo)
          - Service initialization
          - UI population (tree, details, stats)
        """
        # noinspection PyProtectedMember
        self.mw._load_data()  # This is the only place we call the protected method

    def force_save(self) -> None:
        """Forces an immediate save of all collections and metadata.

        Writes current state to:
          - VDF files (localconfig.vdf)
          - Cloud storage (remotecache.vdf)
          - Metadata overrides (JSON)

        Checks if Steam is running before saving. If Steam is running,
        shows a warning dialog with option to close Steam automatically.

        Shows a success message on completion.
        """
        from src.core.steam_account_scanner import is_steam_running
        from src.ui.dialogs.steam_running_dialog import SteamRunningDialog

        # Check if Steam is running
        if is_steam_running():
            # Show warning dialog
            dialog = SteamRunningDialog(self.mw)
            result = dialog.exec()

            if result == SteamRunningDialog.CLOSE_AND_SAVE:
                # Steam was closed, proceed with save
                self.mw.save_collections()
                UIHelper.show_success(self.mw, t("ui.menu.file.save_success"))
            # else: User cancelled, do nothing
        else:
            # Steam not running, safe to save
            self.mw.save_collections()
            UIHelper.show_success(self.mw, t("ui.menu.file.save_success"))

    def remove_duplicate_collections(self) -> None:
        """Removes duplicate collections from cloud storage.

        Duplicates are identified by identical names. The first occurrence
        is kept, subsequent ones are removed. After cleanup, the full
        save/populate/update cycle runs to sync the UI.

        Shows a message indicating how many duplicates were removed.
        """
        if not self.mw.cloud_storage_parser:
            UIHelper.show_error(self.mw, t("ui.errors.service_unavailable"))
            return

        # Remove duplicates using the cloud_storage_parser method
        removed = self.mw.cloud_storage_parser.remove_duplicate_collections()

        if removed > 0:
            # Persist & update UI
            self.mw.save_collections()
            self.mw.populate_categories()
            self.mw.update_statistics()

            UIHelper.show_success(self.mw, t("ui.menu.file.duplicates_removed", count=removed))
        else:
            UIHelper.show_success(self.mw, t("ui.menu.file.no_duplicates_found"))

    def exit_application(self) -> None:
        """Closes the main window after user confirmation.

        Always asks for confirmation before closing, then triggers closeEvent
        which handles unsaved changes if present.
        """
        if UIHelper.confirm(self.mw, t("common.confirm_exit"), t("ui.main_window.title")):
            self.mw.close()
