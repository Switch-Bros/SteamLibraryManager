"""Single-game metadata editing dialog.

Provides a form interface for editing game metadata fields (name, sort_as,
developer, publisher, release date) with live highlighting of modified fields
and revert-to-original functionality.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from src.ui.theme import Theme
from src.ui.widgets.base_dialog import BaseDialog
from src.ui.widgets.ui_helper import UIHelper
from src.utils.date_utils import format_timestamp_to_date, parse_date_to_timestamp
from src.utils.i18n import t

__all__ = ["MetadataEditDialog"]


class MetadataEditDialog(BaseDialog):
    """Dialog for editing metadata of a single game.

    Provides a form interface for editing game metadata fields such as name,
    developer, publisher, and release date. Features visual highlighting of
    modified fields and optional VDF write functionality.

    Attributes:
        game_name: The name of the game being edited.
        current_metadata: Dictionary containing current metadata values.
        original_metadata: Dictionary containing original unmodified values.
        result_metadata: Dictionary containing edited values after save.
    """

    def __init__(self, parent, game_name: str, current_metadata: dict, original_metadata: dict | None = None):
        """Initializes the metadata edit dialog.

        Args:
            parent: Parent widget for the dialog.
            game_name: Name of the game to display in the title.
            current_metadata: Dictionary with current metadata values.
            original_metadata: Optional dictionary with original values for
                comparison and revert functionality.
        """
        self.game_name = game_name
        self.current_metadata = current_metadata
        self.original_metadata = original_metadata or {}
        self.result_metadata = None
        super().__init__(
            parent,
            title_text=t("ui.metadata_editor.editing_title", game=game_name),
            min_width=600,
            buttons="custom",
        )
        self._populate_fields()

    def _build_content(self, layout: QVBoxLayout) -> None:
        """Adds form fields, original values group, and action buttons.

        Args:
            layout: The main vertical layout.
        """
        # Info
        info = QLabel(t("ui.metadata_editor.info_tracking"))
        info.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info)

        # Form Fields
        form = QFormLayout()

        # Input fields
        self.name_edit = QLineEdit()
        self.sort_as_edit = QLineEdit()
        self.developer_edit = QLineEdit()
        self.publisher_edit = QLineEdit()
        self.release_date_edit = QLineEdit()

        # Build form
        form.addRow(t("ui.metadata_editor.game_name_label"), self.name_edit)
        form.addRow(t("ui.metadata_editor.sort_as_label"), self.sort_as_edit)

        # Sort Help
        sort_help = QLabel(t("ui.metadata_editor.sort_as_help"))
        sort_help.setStyleSheet("color: gray; font-size: 9px;")
        form.addRow("", sort_help)

        form.addRow(t("ui.game_details.developer") + ":", self.developer_edit)
        form.addRow(t("ui.game_details.publisher") + ":", self.publisher_edit)
        form.addRow(t("ui.game_details.release_year") + ":", self.release_date_edit)

        # Date Help
        date_help = QLabel(t("ui.metadata_editor.date_help"))
        date_help.setStyleSheet("color: gray; font-size: 9px;")
        form.addRow("", date_help)

        layout.addLayout(form)

        # Original Values Group
        original_group = QGroupBox(t("ui.metadata_editor.original_values_group"))
        original_layout = QVBoxLayout()
        self.original_text = QTextEdit()
        self.original_text.setReadOnly(True)
        self.original_text.setMaximumHeight(100)
        original_layout.addWidget(self.original_text)
        original_group.setLayout(original_layout)
        layout.addWidget(original_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        # Revert to Original Button
        revert_btn = QPushButton(t("ui.metadata_editor.revert_to_original"))
        revert_btn.setStyleSheet("background-color: #6c757d; color: white;")
        revert_btn.clicked.connect(self._revert_to_original)
        btn_layout.addWidget(revert_btn)

        cancel_btn = QPushButton(t("common.cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton(t("common.save"))
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _populate_fields(self):
        """Populates form fields with current metadata values.

        Fills all input fields with values from current_metadata, stores
        formatted original values for live comparison, connects textChanged
        signals, and applies initial highlighting.
        Also displays original values in the read-only text area.
        """
        m = self.current_metadata
        o = self.original_metadata

        # Store formatted original values for live comparison
        self._original_display: dict[str, str] = {
            "name": str(o.get("name", "")),
            "developer": str(o.get("developer", "")),
            "publisher": str(o.get("publisher", "")),
            "release_date": format_timestamp_to_date(o.get("release_date", "")),
        }

        # Populate fields
        self.name_edit.setText(m.get("name", ""))
        self.sort_as_edit.setText(m.get("sort_as", ""))
        self.developer_edit.setText(m.get("developer", ""))
        self.publisher_edit.setText(m.get("publisher", ""))
        # Convert raw timestamp → DD.MM.YYYY before displaying
        self.release_date_edit.setText(format_timestamp_to_date(m.get("release_date", "")))

        # Connect textChanged for live highlighting
        self.name_edit.textChanged.connect(self._update_highlighting)
        self.developer_edit.textChanged.connect(self._update_highlighting)
        self.publisher_edit.textChanged.connect(self._update_highlighting)
        self.release_date_edit.textChanged.connect(self._update_highlighting)

        # Initial highlighting
        self._update_highlighting()

        # Show original values (dates formatted for display)
        na = t("ui.game_details.value_unknown")
        rel_display = self._original_display["release_date"] or na
        lines = [
            f"{t('ui.game_details.name')}: {o.get('name', na)}",
            f"{t('ui.game_details.developer')}: {o.get('developer', na)}",
            f"{t('ui.game_details.publisher')}: {o.get('publisher', na)}",
            f"{t('ui.game_details.release_year')}: {rel_display}",
        ]

        self.original_text.setPlainText("\n".join(lines))

    def _update_highlighting(self):
        """Re-evaluates highlighting for all editable fields.

        Compares each field's current text against the stored original
        display value. Applies modified styling if different, clears it
        if identical.
        """
        modified_style = Theme.modified_field()
        na = t("ui.game_details.value_unknown")

        fields = [
            (self.name_edit, "name"),
            (self.developer_edit, "developer"),
            (self.publisher_edit, "publisher"),
            (self.release_date_edit, "release_date"),
        ]

        for widget, key in fields:
            original_val = self._original_display.get(key, "")
            if widget.text().strip() != original_val.strip():
                widget.setStyleSheet(modified_style)
                widget.setToolTip(t("ui.metadata_editor.modified_tooltip", original=original_val or na))
            else:
                widget.setStyleSheet("")
                widget.setToolTip("")

    def _revert_to_original(self):
        """Restores all fields to their original values.

        Shows an information dialog if no original values exist, or a
        confirmation dialog before reverting. Highlighting is cleared
        automatically via the textChanged → _update_highlighting chain.
        """
        if not self.original_metadata:
            UIHelper.show_info(
                self, t("ui.metadata_editor.revert_no_original"), title=t("ui.metadata_editor.revert_title")
            )
            return

        if not UIHelper.confirm(self, t("ui.metadata_editor.revert_confirm"), t("ui.metadata_editor.revert_title")):
            return

        # Revert all fields — textChanged triggers _update_highlighting
        self.name_edit.setText(self._original_display["name"])
        self.developer_edit.setText(self._original_display["developer"])
        self.publisher_edit.setText(self._original_display["publisher"])
        self.release_date_edit.setText(self._original_display["release_date"])

    def _save(self):
        """Validates and saves the edited metadata.

        Validates that the name field is not empty and stores the result
        metadata.  VDF writing happens on app exit, not per-edit.
        """
        name = self.name_edit.text().strip()
        if not name:
            UIHelper.show_warning(self, t("ui.metadata_editor.error_empty_name"))
            return

        self.result_metadata = {
            "name": name,
            "sort_as": self.sort_as_edit.text().strip() or name,
            "developer": self.developer_edit.text().strip(),
            "publisher": self.publisher_edit.text().strip(),
            "release_date": parse_date_to_timestamp(self.release_date_edit.text().strip()),
        }
        self.accept()

    def get_metadata(self) -> dict | None:
        """Returns the edited metadata after dialog acceptance.

        Returns:
            Dictionary containing the edited metadata values, or None if
            the dialog was cancelled or validation failed.
        """
        return self.result_metadata
