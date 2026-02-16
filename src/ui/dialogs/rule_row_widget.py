# src/ui/dialogs/rule_row_widget.py

"""Single rule row widget for the Smart Collection Builder dialog.

Each row contains: [NOT checkbox] [Field dropdown] [Operator dropdown]
[Value input] [Value Max input (BETWEEN only)] [Delete button].
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

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

from src.services.smart_collections.models import (
    FIELD_CATEGORIES,
    VALID_OPERATORS,
    FilterField,
    Operator,
    SmartCollectionRule,
)
from src.utils.i18n import t

if TYPE_CHECKING:
    pass

__all__ = ["RuleRowWidget"]

logger = logging.getLogger("steamlibmgr.rule_row_widget")

# Maps FilterField to i18n key suffix
_FIELD_I18N: dict[FilterField, str] = {f: f"ui.smart_collections.field.{f.value}" for f in FilterField}

# Maps Operator to i18n key suffix
_OPERATOR_I18N: dict[Operator, str] = {o: f"ui.smart_collections.operator.{o.value}" for o in Operator}


class RuleRowWidget(QWidget):
    """Single rule row for the Smart Collection Builder.

    Emits ``removed`` when the user clicks delete, and ``changed`` when
    any field value changes.

    Attributes:
        removed: Signal emitted with this widget when delete is clicked.
        changed: Signal emitted when any rule parameter changes.
    """

    removed = pyqtSignal(object)
    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None, rule: SmartCollectionRule | None = None) -> None:
        """Initializes the rule row widget.

        Args:
            parent: Parent widget.
            rule: Optional pre-existing rule to populate fields from.
        """
        super().__init__(parent)
        self._initial_rule = rule
        self._create_ui()
        if rule:
            self._populate_from_rule(rule)

    def _create_ui(self) -> None:
        """Builds the row layout with all controls."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        # NOT checkbox
        self._negated_cb = QCheckBox(t("ui.smart_collections.rule_negated"))
        self._negated_cb.setFixedWidth(60)
        self._negated_cb.stateChanged.connect(lambda _: self.changed.emit())
        layout.addWidget(self._negated_cb)

        # Field dropdown (grouped by category)
        self._field_combo = QComboBox()
        self._field_combo.setMinimumWidth(140)
        self._populate_fields()
        self._field_combo.currentIndexChanged.connect(self._on_field_changed)
        layout.addWidget(self._field_combo)

        # Operator dropdown
        self._operator_combo = QComboBox()
        self._operator_combo.setMinimumWidth(100)
        self._operator_combo.currentIndexChanged.connect(lambda _: self.changed.emit())
        layout.addWidget(self._operator_combo)

        # Value input
        self._value_input = QLineEdit()
        self._value_input.setPlaceholderText("Value")
        self._value_input.textChanged.connect(lambda _: self.changed.emit())
        layout.addWidget(self._value_input, stretch=1)

        # Value Max input (for BETWEEN only)
        self._value_max_input = QLineEdit()
        self._value_max_input.setPlaceholderText("Max")
        self._value_max_input.setFixedWidth(80)
        self._value_max_input.textChanged.connect(lambda _: self.changed.emit())
        self._value_max_input.setVisible(False)
        layout.addWidget(self._value_max_input)

        # Delete button
        delete_btn = QPushButton("\U0001f5d1")
        delete_btn.setFixedWidth(32)
        delete_btn.setToolTip(t("common.delete"))
        delete_btn.clicked.connect(lambda: self.removed.emit(self))
        layout.addWidget(delete_btn)

        # Initialize operators for the default field
        self._on_field_changed()

    def _populate_fields(self) -> None:
        """Populates the field dropdown grouped by category."""
        category_labels = {
            "text_list": "Text (List)",
            "text_single": "Text",
            "numeric": "Numeric",
            "enum": "Enum",
            "boolean": "Boolean",
        }
        for cat_key, fields in FIELD_CATEGORIES.items():
            # Add separator-like header (disabled item)
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
        """Updates operator dropdown, value visibility, and autocomplete based on selected field."""
        field = self._get_selected_field()
        if not field:
            return

        # Update operators
        self._operator_combo.blockSignals(True)
        self._operator_combo.clear()
        for op in VALID_OPERATORS.get(field, []):
            self._operator_combo.addItem(t(_OPERATOR_I18N[op]), op.value)
        self._operator_combo.blockSignals(False)

        # Toggle value visibility for boolean fields
        is_bool = field in (FilterField.INSTALLED, FilterField.HIDDEN, FilterField.ACHIEVEMENT_PERFECT)
        self._value_input.setVisible(not is_bool)
        self._value_max_input.setVisible(False)

        # Set autocomplete for Tag/Genre fields
        self._update_autocomplete(field)

        # Show value_max for BETWEEN
        self._update_between_visibility()
        self._operator_combo.currentIndexChanged.connect(lambda _: self._update_between_visibility())

        self.changed.emit()

    def _update_autocomplete(self, field: FilterField) -> None:
        """Sets or removes autocomplete on the value input based on field type.

        For TAG and GENRE fields, loads all known tag/genre names from the
        tag_resolver and attaches a QCompleter for instant suggestions.

        Args:
            field: The currently selected filter field.
        """
        if field not in (FilterField.TAG, FilterField.GENRE):
            self._value_input.setCompleter(None)
            self._value_input.setPlaceholderText("Value")
            return

        # Get tag names from the tag_resolver on the main window
        suggestions = self._get_tag_suggestions(field)

        if suggestions:
            completer = QCompleter(suggestions, self)
            completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            completer.setFilterMode(Qt.MatchFlag.MatchContains)
            self._value_input.setCompleter(completer)
            self._value_input.setPlaceholderText(
                t("ui.smart_collections.field.tag")
                if field == FilterField.TAG
                else t("ui.smart_collections.field.genre")
            )
        else:
            self._value_input.setCompleter(None)
            self._value_input.setPlaceholderText("Value")

    def _get_tag_suggestions(self, field: FilterField) -> list[str]:
        """Retrieves autocomplete suggestions for tag/genre fields.

        Walks up the widget tree to find the main window's tag_resolver.

        Args:
            field: TAG or GENRE filter field.

        Returns:
            Sorted list of tag/genre names, or empty list if unavailable.
        """
        # Walk up to find the main window with tag_resolver
        widget = self.parent()
        while widget is not None:
            resolver = getattr(widget, "tag_resolver", None)
            if resolver:
                if field == FilterField.GENRE:
                    return resolver.get_genre_names(self._get_app_language(widget))
                return resolver.get_all_tag_names(self._get_app_language(widget))
            widget = getattr(widget, "parent", lambda: None)()
        return []

    @staticmethod
    def _get_app_language(widget: QWidget) -> str:
        """Extracts the app language from a main window widget.

        Args:
            widget: A widget that may have an _i18n attribute.

        Returns:
            Language code string, defaults to 'en'.
        """
        i18n = getattr(widget, "_i18n", None)
        if i18n and hasattr(i18n, "locale"):
            return i18n.locale
        return "en"

    def _update_between_visibility(self) -> None:
        """Shows or hides the max value input based on operator selection."""
        op = self._get_selected_operator()
        self._value_max_input.setVisible(op == Operator.BETWEEN)

    def _get_selected_field(self) -> FilterField | None:
        """Returns the currently selected FilterField or None."""
        data = self._field_combo.currentData()
        if not data:
            return None
        try:
            return FilterField(data)
        except ValueError:
            return None

    def _get_selected_operator(self) -> Operator | None:
        """Returns the currently selected Operator or None."""
        data = self._operator_combo.currentData()
        if not data:
            return None
        try:
            return Operator(data)
        except ValueError:
            return None

    def _populate_from_rule(self, rule: SmartCollectionRule) -> None:
        """Fills the UI controls from an existing rule.

        Args:
            rule: The rule to populate from.
        """
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

        self._value_input.setText(rule.value)
        self._value_max_input.setText(rule.value_max)

    def get_rule(self) -> SmartCollectionRule | None:
        """Returns the current rule from UI state.

        Returns:
            SmartCollectionRule or None if field/operator is invalid.
        """
        field = self._get_selected_field()
        operator = self._get_selected_operator()
        if not field or not operator:
            return None

        return SmartCollectionRule(
            field=field,
            operator=operator,
            value=self._value_input.text().strip(),
            value_max=self._value_max_input.text().strip(),
            negated=self._negated_cb.isChecked(),
        )
