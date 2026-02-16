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

    def export_collections_text(self) -> None:
        """Exports current collections as a human-readable VDF text file.

        Opens a file dialog, then writes all cloud storage collections
        to the selected path using VDFTextExporter.
        """
        from PyQt6.QtWidgets import QFileDialog

        from src.utils.vdf_exporter import VDFTextExporter

        parser = self.mw.cloud_storage_parser
        if not parser:
            UIHelper.show_warning(self.mw, t("ui.main_window.cloud_storage_only"))
            return

        collections = parser.collections
        if not collections:
            UIHelper.show_info(self.mw, t("ui.main_window.no_duplicates"))
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self.mw,
            t("menu.file.export.collections_text"),
            "collections_export.vdf",
            "VDF Files (*.vdf);;All Files (*)",
        )

        if not file_path:
            return

        from pathlib import Path

        try:
            VDFTextExporter.export_collections(collections, Path(file_path))
            UIHelper.show_success(self.mw, t("common.save_success"))
        except OSError as exc:
            UIHelper.show_warning(self.mw, str(exc))

    # ------------------------------------------------------------------
    # Export Actions
    # ------------------------------------------------------------------

    def export_csv_simple(self) -> None:
        """Exports the game list as a simple CSV file (Name, App ID, Playtime)."""
        from PyQt6.QtWidgets import QFileDialog

        from src.utils.csv_exporter import CSVExporter

        games = self._get_exportable_games()
        if not games:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self.mw,
            t("ui.export.csv_save_title"),
            "games_simple.csv",
            t("ui.export.csv_filter"),
        )
        if not file_path:
            return

        from pathlib import Path

        try:
            CSVExporter.export_simple(games, Path(file_path))
            UIHelper.show_success(self.mw, t("ui.export.success", path=file_path))
        except OSError as exc:
            UIHelper.show_warning(self.mw, t("ui.export.error", error=str(exc)))

    def export_csv_full(self) -> None:
        """Exports the game list as a full CSV file with all metadata."""
        from PyQt6.QtWidgets import QFileDialog

        from src.utils.csv_exporter import CSVExporter

        games = self._get_exportable_games()
        if not games:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self.mw,
            t("ui.export.csv_save_title"),
            "games_full.csv",
            t("ui.export.csv_filter"),
        )
        if not file_path:
            return

        from pathlib import Path

        try:
            CSVExporter.export_full(games, Path(file_path))
            UIHelper.show_success(self.mw, t("ui.export.success", path=file_path))
        except OSError as exc:
            UIHelper.show_warning(self.mw, t("ui.export.error", error=str(exc)))

    def export_json(self) -> None:
        """Exports the game list as a JSON file."""
        from PyQt6.QtWidgets import QFileDialog

        from src.utils.json_exporter import JSONExporter

        games = self._get_exportable_games()
        if not games:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self.mw,
            t("ui.export.json_save_title"),
            "games_export.json",
            t("ui.export.json_filter"),
        )
        if not file_path:
            return

        from pathlib import Path

        try:
            JSONExporter.export(games, Path(file_path))
            UIHelper.show_success(self.mw, t("ui.export.success", path=file_path))
        except OSError as exc:
            UIHelper.show_warning(self.mw, t("ui.export.error", error=str(exc)))

    def export_db_backup(self) -> None:
        """Creates a database backup using BackupManager."""
        from src.core.backup_manager import BackupManager
        from src.config import config

        db_path = config.DATA_DIR / "metadata.db"
        if not db_path.exists():
            UIHelper.show_warning(self.mw, t("ui.export.no_games"))
            return

        manager = BackupManager(config.DATA_DIR / "backups")
        result = manager.create_backup(db_path)
        if result:
            UIHelper.show_success(self.mw, t("ui.export.success", path=str(result)))
        else:
            UIHelper.show_warning(self.mw, t("ui.export.error", error="Backup failed"))

    # ------------------------------------------------------------------
    # Import Actions
    # ------------------------------------------------------------------

    def import_collections_vdf(self) -> None:
        """Imports collections from a VDF text file."""
        from PyQt6.QtWidgets import QFileDialog

        from src.utils.vdf_importer import VDFImporter

        file_path, _ = QFileDialog.getOpenFileName(
            self.mw,
            t("ui.import_dlg.vdf_title"),
            "",
            t("ui.import_dlg.vdf_filter"),
        )
        if not file_path:
            return

        from pathlib import Path

        try:
            collections = VDFImporter.import_collections(Path(file_path))
        except (FileNotFoundError, ValueError) as exc:
            UIHelper.show_warning(self.mw, t("ui.import_dlg.vdf_error", error=str(exc)))
            return

        if not collections:
            UIHelper.show_info(self.mw, t("ui.import_dlg.vdf_no_collections"))
            return

        parser = self.mw.cloud_storage_parser
        if not parser:
            UIHelper.show_warning(self.mw, t("ui.main_window.cloud_storage_only"))
            return

        count = 0
        for coll in collections:
            # Create collection and add each app ID
            parser.create_empty_collection(coll.name)
            for app_id in coll.app_ids:
                parser.add_app_category(str(app_id), coll.name)
            count += 1

        self.mw.populate_categories()
        UIHelper.show_success(self.mw, t("ui.import_dlg.vdf_success", count=count))

    def import_db_backup(self) -> None:
        """Imports a database backup."""
        from PyQt6.QtWidgets import QFileDialog

        from src.core.backup_manager import BackupManager
        from src.config import config

        file_path, _ = QFileDialog.getOpenFileName(
            self.mw,
            t("common.import"),
            str(config.DATA_DIR / "backups"),
            "Database Files (*.db);;All Files (*)",
        )
        if not file_path:
            return

        from pathlib import Path

        db_path = config.DATA_DIR / "metadata.db"
        manager = BackupManager(config.DATA_DIR / "backups")
        success = manager.restore_backup(Path(file_path), db_path)
        if success:
            UIHelper.show_success(self.mw, t("common.save_success"))
            self.refresh_data()
        else:
            UIHelper.show_warning(self.mw, t("ui.export.error", error="Restore failed"))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_exportable_games(self) -> list:
        """Returns the list of games for export, or shows a warning if empty.

        Returns:
            List of games, or empty list if no games available.
        """
        if not self.mw.game_manager:
            UIHelper.show_warning(self.mw, t("ui.export.no_games"))
            return []
        games = self.mw.game_manager.get_real_games()
        if not games:
            UIHelper.show_warning(self.mw, t("ui.export.no_games"))
            return []
        return games

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
