#
# steam_library_manager/ui/dialogs/smart_collection_dialog.py
# Builder dialog for creating and editing Smart Collections
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
    """Dialog for creating or editing a Smart Collection with grouped rules and live preview."""

    def __init__(
        self,
        parent: QWidget | None,
        game_manager: GameManager,
        smart_manager: SmartCollectionManager,
        collection_to_edit: SmartCollection | None = None,
    ) -> None:
        super().__init__(parent)
        self._game_manager = game_manager
        self._smart_manager = smart_manager
        self._edit_collection = collection_to_edit
        self._result: SmartCollection | None = None
        self._group_widgets: list[RuleGroupWidget] = []

        self._create_ui()

        if collection_to_edit:
            self._populate_from_collection(collection_to_edit)

    def _create_ui(self) -> None:
        title_key = (
            "ui.smart_collections.builder_title_edit"
            if self._edit_collection
            else "ui.smart_collections.builder_title_create"
        )
        self.setWindowTitle(t(title_key))
        self.setMinimumSize(700, 700)
        self.resize(800, 900)

        main_layout = QVBoxLayout(self)

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

        groups_group = QGroupBox(t("ui.smart_collections.groups_label"))
        groups_layout = QVBoxLayout(groups_group)
        groups_layout.setContentsMargins(5, 5, 5, 5)
        groups_layout.setSpacing(4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(350)
        self._groups_container = QWidget()
        self._groups_layout = QVBoxLayout(self._groups_container)
        self._groups_layout.setContentsMargins(4, 4, 4, 4)
        self._groups_layout.addStretch()
        scroll.setWidget(self._groups_container)
        groups_layout.addWidget(scroll)

        btn_row = QHBoxLayout()
        add_group_btn = QPushButton(t("ui.smart_collections.add_group"))
        add_group_btn.clicked.connect(lambda: self._add_group_widget())
        btn_row.addWidget(add_group_btn)

        templates_btn = QPushButton(t("ui.smart_collections.templates_button"))
        templates_btn.clicked.connect(lambda: self._show_templates_menu(templates_btn))
        btn_row.addWidget(templates_btn)

        btn_row.addStretch()
        groups_layout.addLayout(btn_row)

        main_layout.addWidget(groups_group)

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

        self._auto_sync_cb = QCheckBox(t("ui.smart_collections.auto_sync"))
        self._auto_sync_cb.setChecked(True)
        main_layout.addWidget(self._auto_sync_cb)

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

        self._add_group_widget()
        self._update_between_groups_visibility()

    def _add_group_widget(self, group: SmartCollectionRuleGroup | None = None) -> None:
        index = len(self._group_widgets) + 1
        gw = RuleGroupWidget(self, index=index, group=group)
        gw.removed.connect(self._remove_group_widget)
        gw.changed.connect(lambda: None)
        self._group_widgets.append(gw)
        self._groups_layout.insertWidget(self._groups_layout.count() - 1, gw)
        self._update_between_groups_visibility()

    def _remove_group_widget(self, group_widget: RuleGroupWidget) -> None:
        if group_widget in self._group_widgets:
            self._group_widgets.remove(group_widget)
            self._groups_layout.removeWidget(group_widget)
            group_widget.hide()
            group_widget.deleteLater()
            for i, gw in enumerate(self._group_widgets):
                gw.set_index(i + 1)
            self._update_between_groups_visibility()

    def _update_between_groups_visibility(self) -> None:
        has_multiple = len(self._group_widgets) > 1
        self._between_groups_label.setVisible(has_multiple)
        self._or_radio.setVisible(has_multiple)
        self._and_radio.setVisible(has_multiple)

    def _show_templates_menu(self, button: QPushButton) -> None:
        menu = QMenu(self)

        category_order = ["quality", "completion", "time", "platform", "examples"]

        for cat_key in category_order:
            templates = TEMPLATE_CATEGORIES.get(cat_key, [])
            if not templates:
                continue

            cat_label = t(f"ui.smart_collections.template_category.{cat_key}")
            submenu = menu.addMenu(cat_label)

            for tmpl in templates:
                tmpl_label = t(f"ui.smart_collections.template.{tmpl.key}")
                action = submenu.addAction(tmpl_label)
                action.triggered.connect(lambda _checked, tpl=tmpl: self._apply_template(tpl))

        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))

    def _apply_template(self, template: SmartCollectionTemplate) -> None:
        from steam_library_manager.ui.widgets.ui_helper import UIHelper

        sc = template.collection

        tmpl_name = t(f"ui.smart_collections.template.{template.key}")
        tmpl_desc = t(f"ui.smart_collections.template.{template.key}.description", fallback="")
        self._name_input.setText(tmpl_name)
        self._desc_input.setText(tmpl_desc)

        if sc.logic == LogicOperator.AND:
            self._and_radio.setChecked(True)
        else:
            self._or_radio.setChecked(True)

        for gw in list(self._group_widgets):
            self._remove_group_widget(gw)

        for group in sc.groups:
            self._add_group_widget(copy.deepcopy(group))

        UIHelper.show_info(self, t("ui.smart_collections.template_applied"))

    def _on_preview(self) -> None:
        collection = self._build_collection()
        if not collection:
            return

        matching = self._smart_manager.evaluator.evaluate_batch(
            self._game_manager.get_real_games(),
            collection,
        )

        self._match_count_label.setText(t("ui.smart_collections.matching_count", count=len(matching)))

        self._preview_list.clear()
        for game in sorted(matching, key=lambda g: g.sort_name.lower())[:100]:
            self._preview_list.addItem(game.name)

    def _build_collection(self) -> SmartCollection | None:
        """Collect all UI state into a SmartCollection, or None on failure."""
        groups: list[SmartCollectionRuleGroup] = []
        for gw in self._group_widgets:
            group = gw.get_group()
            if group:
                groups.append(group)

        logic = LogicOperator.AND if self._and_radio.isChecked() else LogicOperator.OR

        collection = SmartCollection(
            name=self._name_input.text().strip(),
            description=self._desc_input.text().strip(),
            logic=logic,
            rules=[],
            groups=groups,
            auto_sync=self._auto_sync_cb.isChecked(),
        )

        if self._edit_collection:
            collection.collection_id = self._edit_collection.collection_id
            collection.created_at = self._edit_collection.created_at

        return collection

    def _on_save(self) -> None:
        from steam_library_manager.ui.widgets.ui_helper import UIHelper

        name = self._name_input.text().strip()
        if not name:
            UIHelper.show_warning(self, t("ui.smart_collections.no_name"))
            return

        has_rules = False
        for gw in self._group_widgets:
            group = gw.get_group()
            if group and group.rules:
                has_rules = True
                break

        if not has_rules:
            UIHelper.show_warning(self, t("ui.smart_collections.min_one_group"))
            return

        if not self._edit_collection:
            existing = self._smart_manager.get_by_name(name)
            if existing:
                UIHelper.show_warning(self, t("ui.smart_collections.name_exists"))
                return

        self._result = self._build_collection()
        self.accept()

    def get_result(self) -> SmartCollection | None:
        return self._result

    def _populate_from_collection(self, collection: SmartCollection) -> None:
        """Pre-fill the dialog from an existing collection (grouped or legacy)."""
        self._name_input.setText(collection.name)
        self._desc_input.setText(collection.description)

        if collection.logic == LogicOperator.AND:
            self._and_radio.setChecked(True)
        else:
            self._or_radio.setChecked(True)

        self._auto_sync_cb.setChecked(collection.auto_sync)

        for gw in list(self._group_widgets):
            self._remove_group_widget(gw)

        if collection.groups:
            for group in collection.groups:
                self._add_group_widget(group)
        elif collection.rules:
            # Legacy v1: wrap flat rules into a single group
            legacy_group = SmartCollectionRuleGroup(
                logic=collection.logic,
                rules=tuple(collection.rules),
            )
            self._add_group_widget(legacy_group)
        else:
            self._add_group_widget()

        self._update_between_groups_visibility()
