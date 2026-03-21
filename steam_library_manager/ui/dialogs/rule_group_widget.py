#
# steam_library_manager/ui/dialogs/rule_group_widget.py
# Widget representing a group of smart collection filter rules
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
# TODO: keyboard shortcuts for rule management?
#

from __future__ import annotations

import logging

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from steam_library_manager.services.smart_collections.models import (
    LogicOperator,
    SmartCollectionRule,
    SmartCollectionRuleGroup,
)
from steam_library_manager.ui.dialogs.rule_row_widget import NoScrollComboBox, RuleRowWidget
from steam_library_manager.utils.i18n import t

__all__ = ["RuleGroupWidget"]

logger = logging.getLogger("steamlibmgr.rule_group_widget")


class RuleGroupWidget(QGroupBox):
    """Rule group with logic operator and child rule rows."""

    removed = pyqtSignal(object)
    changed = pyqtSignal()

    def __init__(
        self,
        parent: QWidget | None = None,
        index: int = 1,
        group: SmartCollectionRuleGroup | None = None,
    ) -> None:
        super().__init__(parent)
        self._rule_rows = []
        self._index = index
        self._create_ui()

        if group:
            self._populate_from_group(group)
        else:
            self._add_rule_row()

    def set_index(self, index: int) -> None:
        self._index = index
        self.setTitle(t("ui.smart_collections.group_header", index=index))

    def _create_ui(self) -> None:
        # build group layout
        self.setTitle(t("ui.smart_collections.group_header", index=self._index))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        # Header row: logic dropdown + remove button
        hdr = QHBoxLayout()

        self._logic_combo = NoScrollComboBox()
        self._logic_combo.addItem("AND", LogicOperator.AND.value)
        self._logic_combo.addItem("OR", LogicOperator.OR.value)
        self._logic_combo.currentIndexChanged.connect(lambda _: self.changed.emit())
        hdr.addWidget(self._logic_combo)

        hdr.addStretch()

        remove_btn = QPushButton(t("ui.smart_collections.remove_group"))
        remove_btn.clicked.connect(lambda: self.removed.emit(self))
        hdr.addWidget(remove_btn)

        layout.addLayout(hdr)

        # Rules container
        self._rules_container = QWidget()
        self._rules_layout = QVBoxLayout(self._rules_container)
        self._rules_layout.setContentsMargins(4, 4, 4, 4)
        self._rules_layout.addStretch()
        layout.addWidget(self._rules_container)

        # Add rule button
        add_rule_btn = QPushButton(t("ui.smart_collections.add_rule"))
        add_rule_btn.clicked.connect(lambda: self._add_rule_row())
        layout.addWidget(add_rule_btn)

    def _add_rule_row(self, rule: SmartCollectionRule | None = None) -> None:
        row = RuleRowWidget(self, rule)
        row.removed.connect(self._remove_rule_row)
        row.changed.connect(lambda: self.changed.emit())
        self._rule_rows.append(row)
        # Insert before the stretch
        self._rules_layout.insertWidget(self._rules_layout.count() - 1, row)

    def _remove_rule_row(self, row: RuleRowWidget) -> None:
        if row in self._rule_rows:
            self._rule_rows.remove(row)
            self._rules_layout.removeWidget(row)
            row.hide()
            row.deleteLater()
            self.changed.emit()

    def get_group(self) -> SmartCollectionRuleGroup | None:
        # collect rules into group model
        rules = []
        for row in self._rule_rows:
            rule = row.get_rule()
            if rule:
                rules.append(rule)

        if not rules:
            return None

        logic_data = self._logic_combo.currentData()
        logic = LogicOperator(logic_data) if logic_data else LogicOperator.AND

        return SmartCollectionRuleGroup(
            logic=logic,
            rules=tuple(rules),
        )

    def _populate_from_group(self, group: SmartCollectionRuleGroup) -> None:
        # prefill from existing group
        for i in range(self._logic_combo.count()):
            if self._logic_combo.itemData(i) == group.logic.value:
                self._logic_combo.setCurrentIndex(i)
                break

        for rule in group.rules:
            self._add_rule_row(rule)
