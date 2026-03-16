#
# steam_library_manager/ui/dialogs/rule_row_widget.py
# Single filter-rule row for the Smart Collection Builder dialog
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from steam_library_manager.config import config

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QStandardItemModel
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QCompleter,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QWidget,
)

from steam_library_manager.services.smart_collections.models import (
    FIELD_CATEGORIES,
    VALID_OPERATORS,
    FilterField,
    Operator,
    SmartCollectionRule,
)
from steam_library_manager.utils.i18n import t

if TYPE_CHECKING:
    pass

__all__ = ["NoScrollComboBox", "RuleRowWidget"]

logger = logging.getLogger("steamlibmgr.rule_row_widget")

# Maps FilterField to i18n key suffix
_FIELD_I18N: dict[FilterField, str] = {f: f"ui.smart_collections.field.{f.value}" for f in FilterField}

# Maps Operator to i18n key suffix
_OPERATOR_I18N: dict[Operator, str] = {o: f"ui.smart_collections.operator.{o.value}" for o in Operator}

# Maps FilterField to hint i18n key (for placeholder text)
_FIELD_HINT_I18N: dict[FilterField, str] = {
    f: f"ui.smart_collections.hint.{f.value}"
    for f in FilterField
    if f not in (FilterField.INSTALLED, FilterField.HIDDEN, FilterField.ACHIEVEMENT_PERFECT)
}


class NoScrollComboBox(QComboBox):
    """QComboBox that ignores wheel events when not focused."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event) -> None:  # noqa: N802
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class RuleRowWidget(QWidget):
    """Single rule row for the Smart Collection Builder.

    Signals: ``removed`` (delete clicked), ``changed`` (any value changed).
    """

    removed = pyqtSignal(object)
    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None, rule: SmartCollectionRule | None = None) -> None:
        super().__init__(parent)
        self._initial_rule = rule
        self._create_ui()
        if rule:
            self._populate_from_rule(rule)

    def _create_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        self._negated_cb = QCheckBox(t("ui.smart_collections.rule_negated"))
        self._negated_cb.setFixedWidth(60)
        self._negated_cb.stateChanged.connect(lambda _: self.changed.emit())
        layout.addWidget(self._negated_cb)

        self._field_combo = NoScrollComboBox()
        self._field_combo.setMinimumWidth(140)
        self._populate_fields()
        self._field_combo.currentIndexChanged.connect(self._on_field_changed)
        layout.addWidget(self._field_combo)

        self._operator_combo = NoScrollComboBox()
        self._operator_combo.setMinimumWidth(100)
        self._operator_combo.currentIndexChanged.connect(lambda _: self.changed.emit())
        layout.addWidget(self._operator_combo)

        self._value_input = QLineEdit()
        self._value_input.textChanged.connect(lambda _: self.changed.emit())
        layout.addWidget(self._value_input, stretch=1)

        self._value_max_input = QLineEdit()
        self._value_max_input.setPlaceholderText(t("ui.smart_collections.hint.between_max"))
        self._value_max_input.setFixedWidth(80)
        self._value_max_input.textChanged.connect(lambda _: self.changed.emit())
        self._value_max_input.setVisible(False)
        layout.addWidget(self._value_max_input)

        delete_btn = QPushButton("\U0001f5d1")
        delete_btn.setFixedWidth(32)
        delete_btn.setToolTip(t("common.delete"))
        delete_btn.clicked.connect(lambda: self.removed.emit(self))
        layout.addWidget(delete_btn)

        self._on_field_changed()

    def _populate_fields(self) -> None:
        category_labels = {
            "text_list": "Text (List)",
            "text_single": "Text",
            "numeric": "Numeric",
            "enum": "Enum",
            "boolean": "Boolean",
        }
        for cat_key, fields in FIELD_CATEGORIES.items():
            self._field_combo.addItem(f"--- {category_labels.get(cat_key, cat_key)} ---", None)
            idx = self._field_combo.count() - 1
            model = self._field_combo.model()
            if isinstance(model, QStandardItemModel):
                item = model.item(idx)
                if item:
                    item.setEnabled(False)

            for field in fields:
                self._field_combo.addItem(t(_FIELD_I18N[field]), field.value)

    def _on_field_changed(self) -> None:
        field = self._get_selected_field()
        if not field:
            return

        self._operator_combo.blockSignals(True)
        self._operator_combo.clear()
        for op in VALID_OPERATORS.get(field, []):
            self._operator_combo.addItem(t(_OPERATOR_I18N[op]), op.value)
        self._operator_combo.blockSignals(False)

        is_bool = field in (FilterField.INSTALLED, FilterField.HIDDEN, FilterField.ACHIEVEMENT_PERFECT)
        self._value_input.setVisible(not is_bool)
        self._value_max_input.setVisible(False)

        hint_key = _FIELD_HINT_I18N.get(field)
        if hint_key:
            self._value_input.setPlaceholderText(t(hint_key))
        else:
            self._value_input.setPlaceholderText("")

        self._update_autocomplete(field)
        self._update_between_visibility()
        self._operator_combo.currentIndexChanged.connect(lambda _: self._update_between_visibility())

        self.changed.emit()

    def _update_autocomplete(self, field: FilterField) -> None:
        if field not in (FilterField.TAG, FilterField.GENRE):
            self._value_input.setCompleter(None)
            return

        suggestions = self._get_tag_suggestions(field)

        if suggestions:
            completer = QCompleter(suggestions, self)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            self._value_input.setCompleter(completer)
        else:
            self._value_input.setCompleter(None)

    def _get_tag_suggestions(self, field: FilterField) -> list[str]:
        """Walk widget tree to get tag/genre names from tag_resolver."""
        widget = self.parent()
        while widget is not None:
            resolver = getattr(widget, "tag_resolver", None)
            if resolver:
                if field == FilterField.GENRE:
                    return resolver.get_genre_names(self._get_tag_language())
                return resolver.get_all_tag_names(self._get_tag_language())
            widget = getattr(widget, "parent", lambda: None)()
        return []

    @staticmethod
    def _get_tag_language() -> str:
        return config.TAGS_LANGUAGE

    def _resolve_tag_id(self, tag_name: str) -> int | None:
        widget = self.parent()
        while widget is not None:
            resolver = getattr(widget, "tag_resolver", None)
            if resolver:
                db = getattr(resolver, "database", None)
                if db:
                    return db.get_tag_id_by_name(tag_name, self._get_tag_language())
                return None
            widget = getattr(widget, "parent", lambda: None)()
        return None

    def _resolve_tag_name(self, tag_id: int) -> str | None:
        widget = self.parent()
        while widget is not None:
            resolver = getattr(widget, "tag_resolver", None)
            if resolver:
                return resolver.resolve_tag_id(tag_id, self._get_tag_language())
            widget = getattr(widget, "parent", lambda: None)()
        return None

    def _update_between_visibility(self) -> None:
        op = self._get_selected_operator()
        self._value_max_input.setVisible(op == Operator.BETWEEN)

    def _get_selected_field(self) -> FilterField | None:
        data = self._field_combo.currentData()
        if not data:
            return None
        try:
            return FilterField(data)
        except ValueError:
            return None

    def _get_selected_operator(self) -> Operator | None:
        data = self._operator_combo.currentData()
        if not data:
            return None
        try:
            return Operator(data)
        except ValueError:
            return None

    def _populate_from_rule(self, rule: SmartCollectionRule) -> None:
        self._negated_cb.setChecked(rule.negated)

        for i in range(self._field_combo.count()):
            if self._field_combo.itemData(i) == rule.field.value:
                self._field_combo.setCurrentIndex(i)
                break

        for i in range(self._operator_combo.count()):
            if self._operator_combo.itemData(i) == rule.operator.value:
                self._operator_combo.setCurrentIndex(i)
                break

        display_value = rule.value
        if rule.field == FilterField.TAG and rule.tag_id is not None:
            resolved = self._resolve_tag_name(rule.tag_id)
            if resolved:
                display_value = resolved

        self._value_input.setText(display_value)
        self._value_max_input.setText(rule.value_max)

    def get_rule(self) -> SmartCollectionRule | None:
        """Build a SmartCollectionRule from the current UI state."""
        field = self._get_selected_field()
        operator = self._get_selected_operator()
        if not field or not operator:
            return None

        value = self._value_input.text().strip()
        tag_id = None

        if field == FilterField.TAG and operator == Operator.EQUALS and value:
            tag_id = self._resolve_tag_id(value)

        return SmartCollectionRule(
            field=field,
            operator=operator,
            value=value,
            value_max=self._value_max_input.text().strip(),
            negated=self._negated_cb.isChecked(),
            tag_id=tag_id,
        )
