#
# steam_library_manager/ui/builders/toolbar_builder.py
# Builds and rebuilds the main toolbar (auth-state dependent)
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QToolBar, QWidget, QSizePolicy

from steam_library_manager.config import config
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t

if TYPE_CHECKING:
    from steam_library_manager.ui.main_window import MainWindow

__all__ = ["ToolbarBuilder"]


class ToolbarBuilder:
    """Constructs and rebuilds the main QToolBar."""

    def __init__(self, main_window: "MainWindow") -> None:
        self.main_window: "MainWindow" = main_window

    def build(self, toolbar: QToolBar) -> None:
        """Populates (or re-populates) a QToolBar with current actions."""
        toolbar.clear()
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        mw = self.main_window

        refresh_text = f"{t('emoji.refresh')} {t('menu.file.refresh')}"
        refresh_action = QAction(refresh_text, mw)
        refresh_action.setToolTip(t("menu.file.refresh"))
        refresh_action.triggered.connect(mw.file_actions.refresh_data)
        toolbar.addAction(refresh_action)

        save_text = f"{t('emoji.save')} {t('common.save')}"
        save_action = QAction(save_text, mw)
        save_action.setToolTip(t("common.save"))
        save_action.triggered.connect(mw.file_actions.force_save)
        toolbar.addAction(save_action)

        toolbar.addSeparator()

        auto_text = f"{t('emoji.blitz')} {t('menu.edit.auto_categorize')}"
        auto_cat_action = QAction(auto_text, mw)
        auto_cat_action.setToolTip(t("menu.edit.auto_categorize"))
        auto_cat_action.triggered.connect(mw.edit_actions.auto_categorize)
        toolbar.addAction(auto_cat_action)

        edit_text = f"{t('emoji.edit')} {t('menu.edit.metadata.bulk')}"
        bulk_edit_action = QAction(edit_text, mw)
        bulk_edit_action.setToolTip(t("menu.edit.metadata.bulk"))
        bulk_edit_action.triggered.connect(mw.metadata_actions.bulk_edit_metadata)
        toolbar.addAction(bulk_edit_action)

        toolbar.addSeparator()

        search_text = f"{t('emoji.search')} {t('menu.edit.find_missing_metadata')}"
        missing_meta_action = QAction(search_text, mw)
        missing_meta_action.setToolTip(t("menu.edit.find_missing_metadata"))
        missing_meta_action.triggered.connect(mw.tools_actions.find_missing_metadata)
        toolbar.addAction(missing_meta_action)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        toolbar.addWidget(spacer)

        settings_text = f"{t('emoji.settings')} {t('settings.title')}"
        settings_action = QAction(settings_text, mw)
        settings_action.setToolTip(t("settings.title"))
        settings_action.triggered.connect(mw.settings_actions.show_settings)
        toolbar.addAction(settings_action)

        toolbar.addSeparator()

        is_authenticated = mw.steam_username and config.STEAM_ACCESS_TOKEN
        if is_authenticated:
            self._add_logged_in_action(toolbar)
        else:
            self._add_login_action(toolbar)

    def _add_logged_in_action(self, toolbar: QToolBar) -> None:
        mw = self.main_window
        action_text = f"{t('emoji.user')} {mw.steam_username}"
        user_action = QAction(action_text, mw)

        tooltip_text = t("steam.login.logged_in_as", user=mw.steam_username)
        user_action.setToolTip(tooltip_text)

        user_action.triggered.connect(lambda: ToolbarBuilder._show_user_dialog(mw))

        toolbar.addAction(user_action)

    def _add_login_action(self, toolbar: QToolBar) -> None:
        mw = self.main_window
        action_text = f"{t('emoji.login')} {t('steam.login.button')}"
        login_action = QAction(action_text, mw)
        login_action.setToolTip(t("steam.login.button"))

        login_action.triggered.connect(mw.steam_actions.start_steam_login)
        toolbar.addAction(login_action)

    @staticmethod
    def _show_user_dialog(mw: "MainWindow") -> None:
        from PyQt6.QtWidgets import QMessageBox

        msg_box = QMessageBox(mw)
        msg_box.setWindowTitle(t("steam.login.steam_login_title"))
        msg_box.setText(t("steam.login.logged_in_as", user=mw.steam_username))
        msg_box.setIcon(QMessageBox.Icon.Information)

        msg_box.addButton(t("common.ok"), QMessageBox.ButtonRole.AcceptRole)
        logout_btn = msg_box.addButton(t("steam.login.logout"), QMessageBox.ButtonRole.DestructiveRole)

        msg_box.exec()

        if msg_box.clickedButton() == logout_btn:
            ToolbarBuilder._handle_logout(mw)

    @staticmethod
    def _handle_logout(mw: "MainWindow") -> None:
        from steam_library_manager.config import config
        from steam_library_manager.core.token_store import TokenStore

        mw.session = None
        mw.access_token = None
        mw.refresh_token = None
        mw.steam_username = None

        token_store = TokenStore()
        token_store.clear_tokens()

        config.STEAM_USER_ID = None
        config.STEAM_ACCESS_TOKEN = None
        config.save()

        mw.user_label.setText("")
        mw.refresh_toolbar()
        mw.set_status(t("steam.login.logged_out"))

        UIHelper.show_success(mw, t("steam.login.logged_out"), "Steam")
