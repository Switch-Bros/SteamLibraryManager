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

        Triggers the full non-blocking loading pipeline via BootstrapService.
        This includes:
          - Steam path validation and parser init
          - Background session restore (token refresh)
          - Background game loading (manifests, VDF, appinfo)
          - Service initialization
          - UI population (tree, details, stats)
        """
        self.mw.bootstrap_service.start()

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
                UIHelper.show_success(self.mw, t("common.save_success"))
            # else: User cancelled, do nothing
        else:
            # Steam not running, safe to save
            self.mw.save_collections()
            UIHelper.show_success(self.mw, t("common.save_success"))

    def remove_duplicate_collections(self) -> None:
        """Opens the merge-duplicates dialog for cloud storage collections.

        Delegates to CategoryActionHandler.show_merge_duplicates_dialog()
        which detects duplicates, shows the selection UI, and performs
        the safe merge with game preservation.
        """
        self.mw.category_handler.show_merge_duplicates_dialog()

    def ask_save_on_exit(self, has_collection_changes: bool, has_metadata_changes: bool) -> str:
        """Shows a 3-button dialog when unsaved changes exist on exit.

        Args:
            has_collection_changes: Whether cloud storage collections were modified.
            has_metadata_changes: Whether appinfo.vdf metadata was modified.

        Returns:
            ``"save"``, ``"discard"``, or ``"cancel"``.
        """
        from PyQt6.QtWidgets import QMessageBox

        filenames: list[str] = []
        if has_collection_changes:
            filenames.append("cloud-storage-namespace-1.json")
        if has_metadata_changes:
            filenames.append("appinfo.vdf")

        msg = QMessageBox(self.mw)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(t("common.unsaved_changes_title"))
        msg.setText(t("common.unsaved_changes_msg", filenames=", ".join(filenames)))

        save_btn = msg.addButton(t("common.save_and_exit"), QMessageBox.ButtonRole.AcceptRole)
        discard_btn = msg.addButton(t("common.discard_and_exit"), QMessageBox.ButtonRole.DestructiveRole)
        msg.addButton(t("common.cancel"), QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(save_btn)

        msg.exec()

        clicked = msg.clickedButton()
        if clicked == save_btn:
            return "save"
        elif clicked == discard_btn:
            return "discard"
        return "cancel"

    def exit_application(self) -> None:
        """Closes the main window.

        Delegates to ``MainWindow.close()`` which triggers ``closeEvent()``
        for unsaved-changes handling and exit confirmation.
        """
        self.mw.close()
