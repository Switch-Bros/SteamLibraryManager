#
# steam_library_manager/ui/actions/file_actions.py
# File menu handlers
#
# Copyright 2025 SwitchBros
# MIT License
#

from __future__ import annotations
from pathlib import Path

from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t

__all__ = ["FileActions"]


class FileActions:
    """File menu - save, export, import, exit.

    Handles all the boring but important stuff: saving collections
    to cloud storage, exporting to CSV/JSON/VDF, importing backups,
    and the "are you sure you want to quit" dialog.
    """

    def __init__(self, win):
        self.win = win

    def refresh_data(self):
        # restart service
        self.win.bootstrap_service.start()

    def force_save(self):
        from steam_library_manager.core.steam_account_scanner import is_steam_running
        from steam_library_manager.ui.dialogs.steam_running_dialog import SteamRunningDialog

        if is_steam_running():
            dlg = SteamRunningDialog(self.win)
            res = dlg.exec()
            if res == SteamRunningDialog.CLOSE_AND_SAVE:
                self.win.save_collections()
                UIHelper.show_success(self.win, t("ui.save.success"))
        else:
            self.win.save_collections()
            UIHelper.show_success(self.win, t("ui.save.success"))

    def remove_duplicate_collections(self):
        self.win.category_handler.show_merge_duplicates_dialog()

    def export_collections_text(self):
        from PyQt6.QtWidgets import QFileDialog
        from steam_library_manager.utils.vdf_exporter import VDFTextExporter

        p = self.win.cloud_storage_parser
        if not p:
            UIHelper.show_warning(self.win, t("ui.main_window.cloud_storage_only"))
            return

        colls = p.collections
        if not colls:
            UIHelper.show_info(self.win, t("ui.main_window.no_duplicates"))
            return

        fp, _ = QFileDialog.getSaveFileName(
            self.win,
            t("menu.file.export.collections_text"),
            "collections_export.vdf",
            "VDF Files (*.vdf);;All Files (*)",
        )
        if not fp:
            return

        try:
            VDFTextExporter.export_collections(colls, Path(fp))
            UIHelper.show_success(self.win, t("ui.save.success"))
        except OSError as exc:
            UIHelper.show_warning(self.win, str(exc))

    def export_csv_simple(self):
        from steam_library_manager.utils.csv_exporter import CSVExporter

        self._do_export(
            "ui.export.csv_save_title", "games_simple.csv", "ui.export.csv_filter", CSVExporter.export_simple
        )

    def export_csv_full(self):
        from steam_library_manager.utils.csv_exporter import CSVExporter

        self._do_export("ui.export.csv_save_title", "games_full.csv", "ui.export.csv_filter", CSVExporter.export_full)

    def export_json(self):
        from steam_library_manager.utils.json_exporter import JSONExporter

        self._do_export("ui.export.json_save_title", "games_export.json", "ui.export.json_filter", JSONExporter.export)

    def _do_export(self, title_key, default_name, filter_key, fn):
        from PyQt6.QtWidgets import QFileDialog

        games = self._get_games()
        if not games:
            return

        fp, _ = QFileDialog.getSaveFileName(self.win, t(title_key), default_name, t(filter_key))
        if not fp:
            return

        try:
            fn(games, Path(fp))
            UIHelper.show_success(self.win, t("ui.export.success", path=fp))
        except OSError as exc:
            UIHelper.show_warning(self.win, t("ui.export.error", error=str(exc)))

    def export_db_backup(self):
        from steam_library_manager.core.backup_manager import BackupManager
        from steam_library_manager.config import config

        db = config.DATA_DIR / "metadata.db"
        if not db.exists():
            UIHelper.show_warning(self.win, t("ui.export.no_games"))
            return

        mgr = BackupManager(config.DATA_DIR / "backups")
        result = mgr.create_backup(db)
        if result:
            UIHelper.show_success(self.win, t("ui.export.success", path=str(result)))
        else:
            UIHelper.show_warning(self.win, t("ui.export.error", error="Backup failed"))

    def export_smart_collections(self):
        from PyQt6.QtWidgets import QFileDialog
        from steam_library_manager.utils.smart_collection_exporter import SmartCollectionExporter

        mgr = self.win.smart_collection_manager
        if not mgr:
            UIHelper.show_warning(self.win, t("ui.export.no_games"))
            return

        colls = mgr.get_all()
        if not colls:
            UIHelper.show_info(self.win, t("ui.smart_collections.export_empty"))
            return

        fp, _ = QFileDialog.getSaveFileName(
            self.win,
            t("ui.smart_collections.export_title"),
            "smart_collections.json",
            t("ui.export.json_filter"),
        )
        if not fp:
            return

        try:
            SmartCollectionExporter.export(colls, Path(fp))
            UIHelper.show_success(self.win, t("ui.smart_collections.export_success", count=len(colls), path=fp))
        except OSError as exc:
            UIHelper.show_warning(self.win, t("ui.export.error", error=str(exc)))

    def import_collections_vdf(self):
        from PyQt6.QtWidgets import QFileDialog
        from steam_library_manager.utils.vdf_importer import VDFImporter

        fp, _ = QFileDialog.getOpenFileName(
            self.win,
            t("ui.import_dlg.vdf_title"),
            "",
            t("ui.import_dlg.vdf_filter"),
        )
        if not fp:
            return

        try:
            colls = VDFImporter.import_collections(Path(fp))
        except (FileNotFoundError, ValueError) as exc:
            UIHelper.show_warning(self.win, t("ui.import_dlg.vdf_error", error=str(exc)))
            return

        if not colls:
            UIHelper.show_info(self.win, t("ui.import_dlg.vdf_no_collections"))
            return

        parser = self.win.cloud_storage_parser
        if not parser:
            UIHelper.show_warning(self.win, t("ui.main_window.cloud_storage_only"))
            return

        cnt = 0
        for c in colls:
            parser.create_empty_collection(c.name)
            for aid in c.app_ids:
                parser.add_app_category(str(aid), c.name)
            cnt += 1

        self.win.populate_categories()
        UIHelper.show_success(self.win, t("ui.import_dlg.vdf_success", count=cnt))

    def import_smart_collections(self):
        from PyQt6.QtWidgets import QFileDialog
        from steam_library_manager.utils.smart_collection_importer import SmartCollectionImporter

        mgr = self.win.smart_collection_manager
        if not mgr:
            UIHelper.show_warning(self.win, t("ui.export.no_games"))
            return

        fp, _ = QFileDialog.getOpenFileName(
            self.win,
            t("ui.smart_collections.import_title"),
            "",
            t("ui.export.json_filter"),
        )
        if not fp:
            return

        try:
            colls = SmartCollectionImporter.import_collections(Path(fp))
        except (FileNotFoundError, ValueError) as exc:
            UIHelper.show_warning(self.win, t("ui.smart_collections.import_error", error=str(exc)))
            return

        if not colls:
            UIHelper.show_info(self.win, t("ui.smart_collections.import_empty"))
            return

        imp = 0
        skip = 0
        for sc in colls:
            if mgr.get_by_name(sc.name):
                skip += 1
                continue
            mgr.create(sc)
            imp += 1

        self.win.populate_categories()

        if skip > 0:
            UIHelper.show_success(
                self.win, t("ui.smart_collections.import_success_skipped", imported=imp, skipped=skip)
            )
        else:
            UIHelper.show_success(self.win, t("ui.smart_collections.import_success", count=imp))

    def import_db_backup(self):
        from PyQt6.QtWidgets import QFileDialog
        from steam_library_manager.core.backup_manager import BackupManager
        from steam_library_manager.config import config

        fp, _ = QFileDialog.getOpenFileName(
            self.win,
            t("common.import"),
            str(config.DATA_DIR / "backups"),
            "Database Files (*.db);;All Files (*)",
        )
        if not fp:
            return

        db = config.DATA_DIR / "metadata.db"
        mgr = BackupManager(config.DATA_DIR / "backups")
        ok = mgr.restore_backup(Path(fp), db)
        if ok:
            UIHelper.show_success(self.win, t("ui.save.success"))
            self.refresh_data()
        else:
            UIHelper.show_warning(self.win, t("ui.export.error", error="Restore failed"))

    def _get_games(self):
        if not self.win.game_manager:
            UIHelper.show_warning(self.win, t("ui.export.no_games"))
            return []
        games = self.win.game_manager.get_real_games()
        if not games:
            UIHelper.show_warning(self.win, t("ui.export.no_games"))
            return []
        return games

    def ask_save_on_exit(self, coll_ch, meta_ch):
        from PyQt6.QtWidgets import QMessageBox

        fnames = []
        if coll_ch:
            fnames.append("cloud-storage-namespace-1.json")
        if meta_ch:
            fnames.append("appinfo.vdf")

        msg = QMessageBox(self.win)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(t("ui.unsaved_changes.title"))
        msg.setText(t("ui.unsaved_changes.message", filenames=", ".join(fnames)))

        save_btn = msg.addButton(t("ui.exit.save_and_exit"), QMessageBox.ButtonRole.AcceptRole)
        disc_btn = msg.addButton(t("ui.exit.discard_and_exit"), QMessageBox.ButtonRole.DestructiveRole)
        msg.addButton(t("common.cancel"), QMessageBox.ButtonRole.RejectRole)
        msg.setDefaultButton(save_btn)

        msg.exec()

        clicked = msg.clickedButton()
        if clicked == save_btn:
            return "save"
        elif clicked == disc_btn:
            return "discard"
        return "cancel"

    def exit_application(self):
        self.win.close()
