#
# steam_library_manager/ui/dialogs/smart_collection_dialog.py
# Dialog for creating and editing smart collections with rules
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMenu,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from steam_library_manager.services.smart_collections.models import (
    LogicOperator,
    SmartCollection,
    SmartCollectionRuleGroup,
)
from steam_library_manager.services.smart_collections.templates import (
    TEMPLATE_CATEGORIES,
    SmartCollectionTemplate,
)
from steam_library_manager.ui.dialogs.rule_group_widget import RuleGroupWidget
from steam_library_manager.utils.i18n import t

if TYPE_CHECKING:
    from steam_library_manager.core.game_manager import GameManager
    from steam_library_manager.services.smart_collections.smart_collection_manager import SmartCollectionManager

__all__ = ["SmartCollectionDialog"]

logger = logging.getLogger("steamlibmgr.smart_collection_dialog")


class SmartCollectionDialog(QDialog):
    """Dialog for creating/editing smart collections with grouped rules."""

    def __init__(
        self, parent, game_manager: GameManager, smart_manager: SmartCollectionManager, collection_to_edit=None
    ):
        # init dialog
        super().__init__(parent)
        self._game_manager = game_manager
        self._smart_manager = smart_manager
        self._edit_collection = collection_to_edit
        self._result = None
        self._group_widgets = []

        self._create_ui()

        if collection_to_edit:
            self._populate_from_collection(collection_to_edit)

    def _create_ui(self):
        # build the ui
        title_key = (
            "ui.smart_collections.builder_title_edit"
            if self._edit_collection
            else "ui.smart_collections.builder_title_create"
        )
        self.setWindowTitle(t(title_key))
        self.setMinimumSize(700, 700)
        self.resize(800, 900)

        main_layout = QVBoxLayout(self)

        # name & description section
        info_group = QGroupBox(t("ui.smart_collections.name_label"))
        info_layout = QVBoxLayout(info_group)
        info_layout.setContentsMargins(5, 5, 5, 5)
        info_layout.setSpacing(4)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel(t("ui.smart_collections.name_label") + ":"))
        self._name_input = QLineEdit()
        name_row.addWidget(self._name_input)
        info_layout.addLayout(name_row)

        desc_row = QHBoxLayout()
        desc_row.addWidget(QLabel(t("ui.smart_collections.description_label") + ":"))
        self._desc_input = QLineEdit()
        desc_row.addWidget(self._desc_input)
        info_layout.addLayout(desc_row)

        # logic operator between groups
        logic_row = QHBoxLayout()
        self._between_groups_label = QLabel(t("ui.smart_collections.between_groups_label") + ":")
        logic_row.addWidget(self._between_groups_label)
        self._logic_group = QButtonGroup(self)
        self._or_radio = QRadioButton("OR")
        self._and_radio = QRadioButton("AND")
        self._or_radio.setChecked(True)
        self._logic_group.addButton(self._or_radio)
        self._logic_group.addButton(self._and_radio)
        logic_row.addWidget(self._or_radio)
        logic_row.addWidget(self._and_radio)
        logic_row.addStretch()
        info_layout.addLayout(logic_row)

        main_layout.addWidget(info_group)

        # rule groups section
        groups_group = QGroupBox(t("ui.smart_collections.groups_label"))
        groups_layout = QVBoxLayout(groups_group)
        groups_layout.setContentsMargins(5, 5, 5, 5)
        groups_layout.setSpacing(4)

        # scrollable area for groups
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(350)
        self._groups_container = QWidget()
        self._groups_layout = QVBoxLayout(self._groups_container)
        self._groups_layout.setContentsMargins(4, 4, 4, 4)
        self._groups_layout.addStretch()
        scroll.setWidget(self._groups_container)
        groups_layout.addWidget(scroll)

        # add group and template buttons
        btn_row = QHBoxLayout()
        add_btn = QPushButton(t("ui.smart_collections.add_group"))
        add_btn.clicked.connect(lambda: self._add_group_widget())
        btn_row.addWidget(add_btn)

        tmpl_btn = QPushButton(t("ui.smart_collections.templates_button"))
        tmpl_btn.clicked.connect(lambda: self._show_templates_menu(tmpl_btn))
        btn_row.addWidget(tmpl_btn)

        btn_row.addStretch()
        groups_layout.addLayout(btn_row)

        main_layout.addWidget(groups_group)

        # preview section
        preview_group = QGroupBox(t("ui.smart_collections.preview_label"))
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(5, 5, 5, 5)
        preview_layout.setSpacing(4)

        self._match_count_label = QLabel(t("ui.smart_collections.matching_count", count=0))
        preview_layout.addWidget(self._match_count_label)

        self._preview_list = QListWidget()
        self._preview_list.setMaximumHeight(200)
        preview_layout.addWidget(self._preview_list)

        main_layout.addWidget(preview_group)

        # auto-sync checkbox
        self._auto_sync_cb = QCheckBox(t("ui.smart_collections.auto_sync"))
        self._auto_sync_cb.setChecked(True)
        main_layout.addWidget(self._auto_sync_cb)

        # buttons
        button_row = QHBoxLayout()
        button_row.addStretch()

        preview_btn = QPushButton(t("ui.smart_collections.preview_label"))
        preview_btn.clicked.connect(self._on_preview)
        button_row.addWidget(preview_btn)

        cancel_btn = QPushButton(t("common.cancel"))
        cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(cancel_btn)

        save_btn = QPushButton(t("ui.smart_collections.save_sync"))
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)
        button_row.addWidget(save_btn)

        main_layout.addLayout(button_row)

        # add default empty group
        self._add_group_widget()
        self._update_between_groups_visibility()

    def _add_group_widget(self, group=None):
        # add new rule group widget
        idx = len(self._group_widgets) + 1
        gw = RuleGroupWidget(self, index=idx, group=group)
        gw.removed.connect(self._remove_group_widget)
        gw.changed.connect(lambda: None)
        self._group_widgets.append(gw)
        # insert before stretch
        self._groups_layout.insertWidget(self._groups_layout.count() - 1, gw)
        self._update_between_groups_visibility()

    def _remove_group_widget(self, gw):
        # remove group widget and reindex
        if gw in self._group_widgets:
            self._group_widgets.remove(gw)
            self._groups_layout.removeWidget(gw)
            gw.hide()
            gw.deleteLater()
            # reindex remaining
            for i, w in enumerate(self._group_widgets):
                w.set_index(i + 1)
            self._update_between_groups_visibility()

    def _update_between_groups_visibility(self):
        # show/hide logic operator label
        multi = len(self._group_widgets) > 1
        self._between_groups_label.setVisible(multi)
        self._or_radio.setVisible(multi)
        self._and_radio.setVisible(multi)

    def _show_templates_menu(self, btn):
        # show templates dropdown
        menu = QMenu(self)

        # category order
        cats = ["quality", "completion", "time", "platform", "examples"]

        for cat in cats:
            templates = TEMPLATE_CATEGORIES.get(cat, [])
            if not templates:
                continue

            cat_label = t("ui.smart_collections.template_category.%s" % cat)
            submenu = menu.addMenu(cat_label)

            for tmpl in templates:
                tmpl_label = t("ui.smart_collections.template.%s" % tmpl.key)
                action = submenu.addAction(tmpl_label)
                # capture tmpl in closure
                action.triggered.connect(lambda _checked, tpl=tmpl: self._apply_template(tpl))

        menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _apply_template(self, tmpl: SmartCollectionTemplate):
        # apply template to dialog
        from steam_library_manager.ui.widgets.ui_helper import UIHelper

        sc = tmpl.collection

        # set name and desc from i18n
        name = t("ui.smart_collections.template.%s" % tmpl.key)
        desc = t("ui.smart_collections.template.%s.description" % tmpl.key, fallback="")
        self._name_input.setText(name)
        self._desc_input.setText(desc)

        # set logic operator
        if sc.logic == LogicOperator.AND:
            self._and_radio.setChecked(True)
        else:
            self._or_radio.setChecked(True)

        # clear existing
        for gw in list(self._group_widgets):
            self._remove_group_widget(gw)

        # add groups from template
        for g in sc.groups:
            self._add_group_widget(copy.deepcopy(g))

        UIHelper.show_info(self, t("ui.smart_collections.template_applied"))

    def _on_preview(self):
        # evaluate rules and show preview
        coll = self._build_collection()
        if not coll:
            return

        matching = self._smart_manager.evaluator.evaluate_batch(
            self._game_manager.get_real_games(),
            coll,
        )

        self._match_count_label.setText(t("ui.smart_collections.matching_count", count=len(matching)))

        self._preview_list.clear()
        for game in sorted(matching, key=lambda g: g.sort_name.lower())[:100]:
            self._preview_list.addItem(game.name)

    def _build_collection(self):
        # gather ui state into SmartCollection
        groups = []
        for gw in self._group_widgets:
            group = gw.get_group()
            if group:
                groups.append(group)

        logic = LogicOperator.AND if self._and_radio.isChecked() else LogicOperator.OR

        coll = SmartCollection(
            name=self._name_input.text().strip(),
            description=self._desc_input.text().strip(),
            logic=logic,
            rules=[],
            groups=groups,
            auto_sync=self._auto_sync_cb.isChecked(),
        )

        if self._edit_collection:
            coll.collection_id = self._edit_collection.collection_id
            coll.created_at = self._edit_collection.created_at

        return coll

    def _on_save(self):
        # validate and save
        from steam_library_manager.ui.widgets.ui_helper import UIHelper

        name = self._name_input.text().strip()
        if not name:
            UIHelper.show_warning(self, t("ui.smart_collections.no_name"))
            return

        # check at least one group has rules
        has_rules = False
        for gw in self._group_widgets:
            group = gw.get_group()
            if group and group.rules:
                has_rules = True
                break

        if not has_rules:
            UIHelper.show_warning(self, t("ui.smart_collections.min_one_group"))
            return

        # check duplicate name on create
        if not self._edit_collection:
            existing = self._smart_manager.get_by_name(name)
            if existing:
                UIHelper.show_warning(self, t("ui.smart_collections.name_exists"))
                return

        self._result = self._build_collection()
        self.accept()

    def get_result(self):
        # return result collection
        return self._result

    def _populate_from_collection(self, coll):
        # load existing collection into dialog
        self._name_input.setText(coll.name)
        self._desc_input.setText(coll.description)

        if coll.logic == LogicOperator.AND:
            self._and_radio.setChecked(True)
        else:
            self._or_radio.setChecked(True)

        self._auto_sync_cb.setChecked(coll.auto_sync)

        # remove default empty group
        for gw in list(self._group_widgets):
            self._remove_group_widget(gw)

        if coll.groups:
            # v2 format
            for g in coll.groups:
                self._add_group_widget(g)
        elif coll.rules:
            # legacy v1 format
            legacy = SmartCollectionRuleGroup(
                logic=coll.logic,
                rules=tuple(coll.rules),
            )
            self._add_group_widget(legacy)
        else:
            # no rules, add empty
            self._add_group_widget()

        self._update_between_groups_visibility()
