#
# steam_library_manager/ui/dialogs/rule_row_widget.py
# Widget for a single smart collection filter rule row
#
# Copyright © 2025-2026 SwitchBros
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
_FIELD_I18N = {f: "ui.smart_collections.field.%s" % f.value for f in FilterField}

# Maps Operator to i18n key suffix
_OP_I18N = {o: "ui.smart_collections.operator.%s" % o.value for o in Operator}

# Maps FilterField to hint i18n key (for placeholder text)
_HINT_I18N = {
    f: "ui.smart_collections.hint.%s" % f.value
    for f in FilterField
    if f not in (FilterField.INSTALLED, FilterField.HIDDEN, FilterField.ACHIEVEMENT_PERFECT)
}


class NoScrollComboBox(QComboBox):
    """QComboBox that ignores wheel events when not focused."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):  # noqa: N802
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class RuleRowWidget(QWidget):
    """Single rule row for the Smart Collection Builder.

    Emits ``removed`` when the user clicks delete, and ``changed`` when
    any field value changes.
    """

    removed = pyqtSignal(object)
    changed = pyqtSignal()

    def __init__(self, parent=None, rule=None):
        super().__init__(parent)
        self._init_rule = rule
        self._create_ui()
        if rule:
            self._fill_from_rule(rule)

    def _create_ui(self):
        # Build the row layout with all controls
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)

        # NOT checkbox
        self._negated_cb = QCheckBox(t("ui.smart_collections.rule_negated"))
        self._negated_cb.setFixedWidth(60)
        self._negated_cb.stateChanged.connect(lambda _: self.changed.emit())
        lay.addWidget(self._negated_cb)

        # Field dropdown (grouped by category)
        self._field_combo = NoScrollComboBox()
        self._field_combo.setMinimumWidth(140)
        self._fill_fields()
        self._field_combo.currentIndexChanged.connect(self._on_field_changed)
        lay.addWidget(self._field_combo)

        # Operator dropdown
        self._operator_combo = NoScrollComboBox()
        self._operator_combo.setMinimumWidth(100)
        self._operator_combo.currentIndexChanged.connect(lambda _: self.changed.emit())
        lay.addWidget(self._operator_combo)

        # Value input
        self._value_input = QLineEdit()
        self._value_input.textChanged.connect(lambda _: self.changed.emit())
        lay.addWidget(self._value_input, stretch=1)

        # Value Max input (for BETWEEN only)
        self._value_max_input = QLineEdit()
        self._value_max_input.setPlaceholderText(t("ui.smart_collections.hint.between_max"))
        self._value_max_input.setFixedWidth(80)
        self._value_max_input.textChanged.connect(lambda _: self.changed.emit())
        self._value_max_input.setVisible(False)
        lay.addWidget(self._value_max_input)

        # Delete button
        del_btn = QPushButton("\U0001f5d1")
        del_btn.setFixedWidth(32)
        del_btn.setToolTip(t("common.delete"))
        del_btn.clicked.connect(lambda: self.removed.emit(self))
        lay.addWidget(del_btn)

        # Initialize operators for the default field
        self._on_field_changed()

    def _fill_fields(self):
        # Populate the field dropdown grouped by category
        cat_labels = {
            "text_list": "Text (List)",
            "text_single": "Text",
            "numeric": "Numeric",
            "enum": "Enum",
            "boolean": "Boolean",
        }
        for cat_key, fields in FIELD_CATEGORIES.items():
            # Separator-like header (disabled item)
            self._field_combo.addItem("--- %s ---" % cat_labels.get(cat_key, cat_key), None)
            idx = self._field_combo.count() - 1
            mdl = self._field_combo.model()
            if isinstance(mdl, QStandardItemModel):
                item = mdl.item(idx)
                if item:
                    item.setEnabled(False)

            for fld in fields:
                self._field_combo.addItem(t(_FIELD_I18N[fld]), fld.value)

    def _on_field_changed(self):
        # Update operator dropdown, value visibility, and autocomplete
        fld = self._get_field()
        if not fld:
            return

        # Update operators
        self._operator_combo.blockSignals(True)
        self._operator_combo.clear()
        for op in VALID_OPERATORS.get(fld, []):
            self._operator_combo.addItem(t(_OP_I18N[op]), op.value)
        self._operator_combo.blockSignals(False)

        # Toggle value visibility for boolean fields
        is_bool = fld in (FilterField.INSTALLED, FilterField.HIDDEN, FilterField.ACHIEVEMENT_PERFECT)
        self._value_input.setVisible(not is_bool)
        self._value_max_input.setVisible(False)

        # Set field-specific placeholder hint
        hint_key = _HINT_I18N.get(fld)
        if hint_key:
            self._value_input.setPlaceholderText(t(hint_key))
        else:
            self._value_input.setPlaceholderText("")

        # Set autocomplete for Tag/Genre fields
        self._setup_completer(fld)

        # Show value_max for BETWEEN
        self._sync_between()
        self._operator_combo.currentIndexChanged.connect(lambda _: self._sync_between())

        self.changed.emit()

    def _setup_completer(self, fld):
        # Set or remove autocomplete on the value input based on field type
        if fld not in (FilterField.TAG, FilterField.GENRE):
            self._value_input.setCompleter(None)
            return

        suggestions = self._get_suggestions(fld)

        if suggestions:
            comp = QCompleter(suggestions, self)
            comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            comp.setFilterMode(Qt.MatchFlag.MatchContains)
            self._value_input.setCompleter(comp)
        else:
            self._value_input.setCompleter(None)

    def _get_suggestions(self, fld):
        # Walk up to find the main window's tag_resolver for suggestions
        w = self.parent()
        while w is not None:
            resolver = getattr(w, "tag_resolver", None)
            if resolver:
                lang = self._get_tag_lang()
                if fld == FilterField.GENRE:
                    return resolver.get_genre_names(lang)
                return resolver.get_all_tag_names(lang)
            w = getattr(w, "parent", lambda: None)()
        return []

    @staticmethod
    def _get_tag_lang():
        return config.TAGS_LANGUAGE

    def _resolve_id(self, tag_name):
        # Resolve a tag name to its numeric TagID
        w = self.parent()
        while w is not None:
            resolver = getattr(w, "tag_resolver", None)
            if resolver:
                db = getattr(resolver, "database", None)
                if db:
                    return db.get_tag_id_by_name(tag_name, self._get_tag_lang())
                return None
            w = getattr(w, "parent", lambda: None)()
        return None

    def _resolve_name(self, tag_id):
        # Resolve a numeric TagID to its localized name
        w = self.parent()
        while w is not None:
            resolver = getattr(w, "tag_resolver", None)
            if resolver:
                return resolver.resolve_tag_id(tag_id, self._get_tag_lang())
            w = getattr(w, "parent", lambda: None)()
        return None

    def _sync_between(self):
        # Show or hide the max value input based on operator
        op = self._get_op()
        self._value_max_input.setVisible(op == Operator.BETWEEN)

    def _get_field(self):
        # Return currently selected FilterField or None
        data = self._field_combo.currentData()
        if not data:
            return None
        try:
            return FilterField(data)
        except ValueError:
            return None

    def _get_op(self):
        # Return currently selected Operator or None
        data = self._operator_combo.currentData()
        if not data:
            return None
        try:
            return Operator(data)
        except ValueError:
            return None

    def _fill_from_rule(self, rule):
        # Fill UI controls from an existing rule
        self._negated_cb.setChecked(rule.negated)

        # Find and select the field
        for i in range(self._field_combo.count()):
            if self._field_combo.itemData(i) == rule.field.value:
                self._field_combo.setCurrentIndex(i)
                break

        # Find and select the operator
        for i in range(self._operator_combo.count()):
            if self._operator_combo.itemData(i) == rule.operator.value:
                self._operator_combo.setCurrentIndex(i)
                break

        # For TAG rules with tag_id, resolve to current language name
        val = rule.value
        if rule.field == FilterField.TAG and rule.tag_id is not None:
            resolved = self._resolve_name(rule.tag_id)
            if resolved:
                val = resolved

        self._value_input.setText(val)
        self._value_max_input.setText(rule.value_max)

    def get_rule(self):
        # Return current rule from UI state, or None if invalid
        fld = self._get_field()
        op = self._get_op()
        if not fld or not op:
            return None

        val = self._value_input.text().strip()
        tag_id = None

        # Resolve tag_id for TAG + EQUALS (language-independent matching)
        if fld == FilterField.TAG and op == Operator.EQUALS and val:
            tag_id = self._resolve_id(val)

        return SmartCollectionRule(
            field=fld,
            operator=op,
            value=val,
            value_max=self._value_max_input.text().strip(),
            negated=self._negated_cb.isChecked(),
            tag_id=tag_id,
        )
