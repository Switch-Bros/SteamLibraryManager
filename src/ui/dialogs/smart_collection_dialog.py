# src/ui/dialogs/smart_collection_dialog.py

"""Smart Collection Builder dialog for creating and editing Smart Collections.

Provides a UI for defining collection rules with live preview of matching games.
"""

from __future__ import annotations

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
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.services.smart_collections.models import (
    LogicOperator,
    SmartCollection,
    SmartCollectionRule,
)
from src.ui.dialogs.rule_row_widget import RuleRowWidget
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.core.game_manager import GameManager
    from src.services.smart_collections.smart_collection_manager import SmartCollectionManager

__all__ = ["SmartCollectionDialog"]

logger = logging.getLogger("steamlibmgr.smart_collection_dialog")


class SmartCollectionDialog(QDialog):
    """Dialog for creating or editing a Smart Collection with rules and live preview.

    Attributes:
        _game_manager: The game manager for evaluation preview.
        _smart_manager: The smart collection manager.
        _edit_collection: The existing collection being edited, if any.
        _result: The resulting SmartCollection after Save, or None.
    """

    def __init__(
        self,
        parent: QWidget | None,
        game_manager: GameManager,
        smart_manager: SmartCollectionManager,
        collection_to_edit: SmartCollection | None = None,
    ) -> None:
        """Initializes the Smart Collection Builder dialog.

        Args:
            parent: Parent widget.
            game_manager: For evaluating preview.
            smart_manager: For accessing the evaluator.
            collection_to_edit: Optional existing collection for editing mode.
        """
        super().__init__(parent)
        self._game_manager = game_manager
        self._smart_manager = smart_manager
        self._edit_collection = collection_to_edit
        self._result: SmartCollection | None = None
        self._rule_rows: list[RuleRowWidget] = []

        self._create_ui()

        if collection_to_edit:
            self._populate_from_collection(collection_to_edit)

    def _create_ui(self) -> None:
        """Builds the complete dialog UI."""
        self.setWindowTitle(t("ui.smart_collections.builder_title"))
        self.setMinimumSize(700, 600)
        self.resize(750, 650)

        main_layout = QVBoxLayout(self)

        # --- Name & Description ---
        info_group = QGroupBox(t("ui.smart_collections.name_label"))
        info_layout = QVBoxLayout(info_group)

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

        # Logic operator
        logic_row = QHBoxLayout()
        logic_row.addWidget(QLabel(t("ui.smart_collections.logic_label") + ":"))
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

        # --- Rules ---
        rules_group = QGroupBox(t("ui.smart_collections.rules_label"))
        rules_layout = QVBoxLayout(rules_group)

        # Scrollable rule rows
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(150)
        self._rules_container = QWidget()
        self._rules_layout = QVBoxLayout(self._rules_container)
        self._rules_layout.setContentsMargins(4, 4, 4, 4)
        self._rules_layout.addStretch()
        scroll.setWidget(self._rules_container)
        rules_layout.addWidget(scroll)

        # Add Rule button
        add_rule_btn = QPushButton(t("ui.smart_collections.add_rule"))
        add_rule_btn.clicked.connect(lambda: self._add_rule_row())
        rules_layout.addWidget(add_rule_btn)

        main_layout.addWidget(rules_group)

        # --- Preview ---
        preview_group = QGroupBox(t("ui.smart_collections.preview_label"))
        preview_layout = QVBoxLayout(preview_group)

        self._match_count_label = QLabel(t("ui.smart_collections.matching_count", count=0))
        preview_layout.addWidget(self._match_count_label)

        self._preview_list = QListWidget()
        self._preview_list.setMaximumHeight(200)
        preview_layout.addWidget(self._preview_list)

        main_layout.addWidget(preview_group)

        # --- Auto-Sync checkbox ---
        self._auto_sync_cb = QCheckBox(t("ui.smart_collections.auto_sync"))
        self._auto_sync_cb.setChecked(True)
        main_layout.addWidget(self._auto_sync_cb)

        # --- Buttons ---
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

        # Add one default rule row
        self._add_rule_row()

    def _add_rule_row(self, rule: SmartCollectionRule | None = None) -> None:
        """Adds a new rule row to the rules container.

        Args:
            rule: Optional existing rule to pre-fill.
        """
        row = RuleRowWidget(self, rule)
        row.removed.connect(self._remove_rule_row)
        row.changed.connect(lambda: None)  # Could auto-preview in future
        self._rule_rows.append(row)
        # Insert before the stretch
        self._rules_layout.insertWidget(self._rules_layout.count() - 1, row)

    def _remove_rule_row(self, row_widget: RuleRowWidget) -> None:
        """Removes a rule row from the container.

        Args:
            row_widget: The row widget to remove.
        """
        if row_widget in self._rule_rows:
            self._rule_rows.remove(row_widget)
            self._rules_layout.removeWidget(row_widget)
            row_widget.deleteLater()

    def _on_preview(self) -> None:
        """Evaluates current rules and shows matching games in preview list."""
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
        """Collects all UI state into a SmartCollection.

        Returns:
            SmartCollection or None if validation fails.
        """
        rules: list[SmartCollectionRule] = []
        for row in self._rule_rows:
            rule = row.get_rule()
            if rule:
                rules.append(rule)

        logic = LogicOperator.AND if self._and_radio.isChecked() else LogicOperator.OR

        collection = SmartCollection(
            name=self._name_input.text().strip(),
            description=self._desc_input.text().strip(),
            logic=logic,
            rules=rules,
            auto_sync=self._auto_sync_cb.isChecked(),
        )

        if self._edit_collection:
            collection.collection_id = self._edit_collection.collection_id
            collection.created_at = self._edit_collection.created_at

        return collection

    def _on_save(self) -> None:
        """Validates inputs and accepts the dialog."""
        from src.ui.widgets.ui_helper import UIHelper

        name = self._name_input.text().strip()
        if not name:
            UIHelper.show_warning(self, t("ui.smart_collections.no_name"))
            return

        rules: list[SmartCollectionRule] = []
        for row in self._rule_rows:
            rule = row.get_rule()
            if rule:
                rules.append(rule)

        if not rules:
            UIHelper.show_warning(self, t("ui.smart_collections.no_rules"))
            return

        # Check for duplicate name (only on create, not edit)
        if not self._edit_collection:
            existing = self._smart_manager.get_by_name(name)
            if existing:
                UIHelper.show_warning(self, t("ui.smart_collections.name_exists"))
                return

        self._result = self._build_collection()
        self.accept()

    def get_result(self) -> SmartCollection | None:
        """Returns the resulting SmartCollection after the dialog is accepted.

        Returns:
            SmartCollection or None if dialog was cancelled.
        """
        return self._result

    def _populate_from_collection(self, collection: SmartCollection) -> None:
        """Pre-fills the dialog from an existing collection.

        Args:
            collection: The collection to populate from.
        """
        self._name_input.setText(collection.name)
        self._desc_input.setText(collection.description)

        if collection.logic == LogicOperator.AND:
            self._and_radio.setChecked(True)
        else:
            self._or_radio.setChecked(True)

        self._auto_sync_cb.setChecked(collection.auto_sync)

        # Remove the default empty row
        for row in list(self._rule_rows):
            self._remove_rule_row(row)

        # Add rows for each existing rule
        for rule in collection.rules:
            self._add_rule_row(rule)
