# src/ui/dialogs/rule_group_widget.py

"""Rule Group widget for the Smart Collection Builder dialog.

Wraps multiple RuleRowWidget instances in a QGroupBox with a group-level
logic operator (AND/OR) and add/remove controls.
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.services.smart_collections.models import (
    LogicOperator,
    SmartCollectionRule,
    SmartCollectionRuleGroup,
)
from src.ui.dialogs.rule_row_widget import RuleRowWidget
from src.utils.i18n import t

__all__ = ["RuleGroupWidget"]

logger = logging.getLogger("steamlibmgr.rule_group_widget")


class RuleGroupWidget(QGroupBox):
    """A group of rule rows with its own logic operator.

    Attributes:
        removed: Signal emitted with this widget when the user removes the group.
        changed: Signal emitted when any rule or the logic operator changes.
    """

    removed = pyqtSignal(object)
    changed = pyqtSignal()

    def __init__(
        self,
        parent: QWidget | None = None,
        index: int = 1,
        group: SmartCollectionRuleGroup | None = None,
    ) -> None:
        """Initializes the rule group widget.

        Args:
            parent: Parent widget.
            index: The 1-based group index for the header label.
            group: Optional existing group to populate from.
        """
        super().__init__(parent)
        self._rule_rows: list[RuleRowWidget] = []
        self._index = index
        self._create_ui()

        if group:
            self._populate_from_group(group)
        else:
            self._add_rule_row()

    def set_index(self, index: int) -> None:
        """Updates the group header index label.

        Args:
            index: The new 1-based group index.
        """
        self._index = index
        self.setTitle(t("ui.smart_collections.group_header", index=index))

    def _create_ui(self) -> None:
        """Builds the group layout with header, rules, and controls."""
        self.setTitle(t("ui.smart_collections.group_header", index=self._index))

        layout = QVBoxLayout(self)

        # Header row: logic dropdown + remove button
        header_row = QHBoxLayout()

        self._logic_combo = QComboBox()
        self._logic_combo.addItem("AND", LogicOperator.AND.value)
        self._logic_combo.addItem("OR", LogicOperator.OR.value)
        self._logic_combo.currentIndexChanged.connect(lambda _: self.changed.emit())
        header_row.addWidget(self._logic_combo)

        header_row.addStretch()

        remove_btn = QPushButton(t("ui.smart_collections.remove_group"))
        remove_btn.clicked.connect(lambda: self.removed.emit(self))
        header_row.addWidget(remove_btn)

        layout.addLayout(header_row)

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
        """Adds a new rule row to this group.

        Args:
            rule: Optional existing rule to pre-fill.
        """
        row = RuleRowWidget(self, rule)
        row.removed.connect(self._remove_rule_row)
        row.changed.connect(lambda: self.changed.emit())
        self._rule_rows.append(row)
        # Insert before the stretch
        self._rules_layout.insertWidget(self._rules_layout.count() - 1, row)

    def _remove_rule_row(self, row_widget: RuleRowWidget) -> None:
        """Removes a rule row from this group.

        Args:
            row_widget: The row widget to remove.
        """
        if row_widget in self._rule_rows:
            self._rule_rows.remove(row_widget)
            self._rules_layout.removeWidget(row_widget)
            row_widget.deleteLater()
            self.changed.emit()

    def get_group(self) -> SmartCollectionRuleGroup | None:
        """Collects all rule rows into a SmartCollectionRuleGroup.

        Returns:
            A SmartCollectionRuleGroup, or None if no valid rules exist.
        """
        rules: list[SmartCollectionRule] = []
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
        """Pre-fills this widget from an existing group.

        Args:
            group: The group to populate from.
        """
        # Set logic dropdown
        for i in range(self._logic_combo.count()):
            if self._logic_combo.itemData(i) == group.logic.value:
                self._logic_combo.setCurrentIndex(i)
                break

        # Add rule rows
        for rule in group.rules:
            self._add_rule_row(rule)
