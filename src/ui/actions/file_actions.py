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

from src.ui.components.ui_helper import UIHelper
from src.ui.vdf_merger_dialog import VdfMergerDialog
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

    def __init__(self, main_window: 'MainWindow') -> None:
        """Initializes the FileActions handler.

        Args:
            main_window: The MainWindow instance that owns these actions.
        """
        self.mw: 'MainWindow' = main_window

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

        Shows a success message on completion.
        """
        self.mw.save_collections()
        UIHelper.show_success(self.mw, t('ui.menu.file.save_success'))

    def show_vdf_merger(self) -> None:
        """Opens the VDF merger dialog for cross-platform category migration.

        Allows users to transfer game categories from one Steam config file
        to another (e.g. Windows → Linux). The dialog handles file selection,
        merge strategy, backup creation, and progress reporting.
        """
        dialog = VdfMergerDialog(self.mw)
        dialog.exec()

    def remove_duplicate_collections(self) -> None:
        """Removes duplicate collections from both VDF and cloud storage.

        Duplicates are identified by identical names. The first occurrence
        is kept, subsequent ones are removed. After cleanup, the full
        save/populate/update cycle runs to sync the UI.

        Shows a message indicating how many duplicates were removed.
        """
        if not self.mw.vdf_parser or not self.mw.cloud_storage_parser:
            UIHelper.show_error(self.mw, t('ui.errors.service_unavailable'))
            return

        # VDF cleanup
        vdf_dupes = self._find_duplicates(self.mw.vdf_parser.get_all_categories())
        for cat in vdf_dupes:
            self.mw.vdf_parser.delete_category(cat)

        # Cloud storage cleanup
        cloud_dupes = self._find_duplicates(self.mw.cloud_storage_parser.get_all_categories())
        for col in cloud_dupes:
            self.mw.cloud_storage_parser.delete_category(col)

        # Persist & update UI - using public wrappers
        self.mw.save_collections()
        self.mw.populate_categories()  # PUBLIC wrapper!
        self.mw.update_statistics()    # PUBLIC wrapper!

        total_removed = len(vdf_dupes) + len(cloud_dupes)
        if total_removed > 0:
            UIHelper.show_success(
                self.mw,
                t('ui.menu.file.duplicates_removed', count=total_removed)
            )
        else:
            UIHelper.show_success(self.mw, t('ui.menu.file.no_duplicates_found'))

    def exit_application(self) -> None:
        """Closes the main window after user confirmation.

        Always asks for confirmation before closing, then triggers closeEvent
        which handles unsaved changes if present.
        """
        if UIHelper.confirm(
            self.mw,
            t('common.confirm_exit'),
            t('ui.main_window.title')
        ):
            self.mw.close()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_duplicates(names: list[str]) -> list[str]:
        """Finds duplicate names in a list, keeping only the first occurrence.

        Args:
            names: List of category/collection names to check.

        Returns:
            List of duplicate names to remove (all but first occurrence).
        """
        seen = set()
        duplicates = []
        for name in names:
            if name in seen:
                duplicates.append(name)
            else:
                seen.add(name)
        return duplicates