"""
Metadata editing dialogs for Steam Library Manager.

This module provides dialogs for editing game metadata, including single-game
editing, bulk editing for multiple games, and restoration of original values.
All dialogs feature visual indicators for modified fields.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
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
from src.utils.date_utils import parse_date_to_timestamp, format_timestamp_to_date
from src.utils.i18n import t


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


class BulkMetadataEditDialog(BaseDialog):
    """Dialog for editing metadata of multiple games simultaneously.

    Allows users to apply the same metadata changes to multiple games at once.
    Supports setting developer, publisher, release date, and name modifications
    (prefix, suffix, text removal).

    Attributes:
        games_count: Number of games to be edited.
        game_names: List of names of games being edited.
        result_metadata: Dictionary containing the bulk edit settings after save.
    """

    def __init__(self, parent, games_count: int, game_names: list[str]):
        """Initializes the bulk metadata edit dialog.

        Args:
            parent: Parent widget for the dialog.
            games_count: Total number of games to be edited.
            game_names: List of game names for preview display.
        """
        self.games_count = games_count
        self.game_names = game_names
        self.result_metadata = None
        super().__init__(
            parent,
            title_text=t("ui.metadata_editor.bulk_title", count=games_count),
            min_width=600,
            buttons="custom",
        )

    @staticmethod
    def _add_bulk_field(layout, label_text: str, placeholder: str = ""):
        """Creates a checkbox-controlled input field for bulk editing.

        Args:
            layout: Parent layout to add the field row to.
            label_text: Text label for the checkbox.
            placeholder: Optional placeholder text for the input field.

        Returns:
            Tuple of (QCheckBox, QLineEdit) for the created field.
        """
        row_layout = QHBoxLayout()
        checkbox = QCheckBox(label_text)
        line_edit = QLineEdit()
        if placeholder:
            line_edit.setPlaceholderText(placeholder)
        line_edit.setEnabled(False)
        checkbox.toggled.connect(line_edit.setEnabled)
        row_layout.addWidget(checkbox)
        row_layout.addWidget(line_edit)
        layout.addLayout(row_layout)
        return checkbox, line_edit

    def _build_content(self, layout: QVBoxLayout) -> None:
        """Adds bulk edit fields, preview, warning, and action buttons.

        Args:
            layout: The main vertical layout.
        """
        # Emoji prefix assembled in code — keeps locale strings clean
        info = QLabel(f"{t('emoji.warning')} {t('ui.metadata_editor.bulk_info', count=self.games_count)}")
        info.setStyleSheet("color: orange; font-size: 11px;")
        layout.addWidget(info)

        preview_group = QGroupBox(t("ui.metadata_editor.bulk_preview", count=self.games_count))
        preview_layout = QVBoxLayout()
        preview_text = QTextEdit()
        preview_text.setReadOnly(True)
        preview_text.setMaximumHeight(120)

        names = self.game_names[:20]
        if len(self.game_names) > 20:
            names.append(t("ui.metadata_editor.bulk_more", count=len(self.game_names) - 20))
        preview_text.setPlainText("\n".join(names))

        preview_layout.addWidget(preview_text)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        fields_group = QGroupBox(t("ui.metadata_editor.fields_group"))
        f_layout = QVBoxLayout()

        self.cb_dev, self.edit_dev = self._add_bulk_field(
            f_layout, t("ui.metadata_editor.set_field", field=t("ui.game_details.developer"))
        )
        self.cb_pub, self.edit_pub = self._add_bulk_field(
            f_layout, t("ui.metadata_editor.set_field", field=t("ui.game_details.publisher"))
        )
        self.cb_date, self.edit_date = self._add_bulk_field(
            f_layout,
            t("ui.metadata_editor.set_field", field=t("ui.game_details.release_year")),
            t("ui.metadata_editor.date_help"),
        )
        self.cb_pre, self.edit_pre = self._add_bulk_field(f_layout, t("ui.metadata_editor.add_prefix"))
        self.cb_suf, self.edit_suf = self._add_bulk_field(f_layout, t("ui.metadata_editor.add_suffix"))
        self.cb_rem, self.edit_rem = self._add_bulk_field(f_layout, t("ui.metadata_editor.remove_text"))

        fields_group.setLayout(f_layout)
        layout.addWidget(fields_group)

        # --- Revert to original section ---
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        self.cb_revert = QCheckBox(t("ui.metadata_editor.bulk_revert_label"))
        self.cb_revert.toggled.connect(self._on_revert_toggled)
        layout.addWidget(self.cb_revert)

        revert_help = QLabel(t("ui.metadata_editor.bulk_revert_help"))
        revert_help.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px; margin-left: 24px;")
        revert_help.setWordWrap(True)
        layout.addWidget(revert_help)

        warn_lbl = QLabel(f"{t('emoji.warning')} {t('auto_categorize.warning_backup')}")
        warn_lbl.setStyleSheet("color: orange;")
        layout.addWidget(warn_lbl)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton(t("common.cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        apply_btn = QPushButton(t("ui.metadata_editor.apply_button", count=self.games_count))
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self._apply)
        btn_layout.addWidget(apply_btn)

        layout.addLayout(btn_layout)

    def _on_revert_toggled(self, checked: bool) -> None:
        """Disables all edit fields when revert is toggled.

        Revert and normal edit are mutually exclusive: when the revert
        checkbox is checked, all field checkboxes and their inputs are
        grayed out.

        Args:
            checked: Whether the revert checkbox is checked.
        """
        field_widgets = [
            (self.cb_dev, self.edit_dev),
            (self.cb_pub, self.edit_pub),
            (self.cb_date, self.edit_date),
            (self.cb_pre, self.edit_pre),
            (self.cb_suf, self.edit_suf),
            (self.cb_rem, self.edit_rem),
        ]
        for checkbox, line_edit in field_widgets:
            checkbox.setEnabled(not checked)
            line_edit.setEnabled(not checked and checkbox.isChecked())

    def _apply(self):
        """Validates selections and stores the bulk edit settings.

        Validates that at least one field or the revert checkbox is selected,
        shows a confirmation dialog, and stores the result metadata if confirmed.
        """
        checks = [self.cb_dev, self.cb_pub, self.cb_date, self.cb_pre, self.cb_suf, self.cb_rem]
        if not self.cb_revert.isChecked() and not any(c.isChecked() for c in checks):
            UIHelper.show_warning(self, t("ui.dialogs.no_selection"), title=t("ui.dialogs.no_changes"))
            return

        # Centralised helper — localised Yes/No buttons
        if not UIHelper.confirm(
            self, t("ui.dialogs.confirm_bulk", count=self.games_count), t("ui.dialogs.confirm_bulk_title")
        ):
            return

        # Revert mode: signal caller to restore original metadata
        if self.cb_revert.isChecked():
            self.result_metadata = {"__revert_to_original__": True}
            self.accept()
            return

        self.result_metadata = {}
        if self.cb_dev.isChecked():
            self.result_metadata["developer"] = self.edit_dev.text().strip()
        if self.cb_pub.isChecked():
            self.result_metadata["publisher"] = self.edit_pub.text().strip()
        if self.cb_date.isChecked():
            self.result_metadata["release_date"] = parse_date_to_timestamp(self.edit_date.text().strip())  # ← FIX!

        mods = {}
        if self.cb_pre.isChecked():
            mods["prefix"] = self.edit_pre.text()
        if self.cb_suf.isChecked():
            mods["suffix"] = self.edit_suf.text()
        if self.cb_rem.isChecked():
            mods["remove"] = self.edit_rem.text()
        if mods:
            self.result_metadata["name_modifications"] = mods

        self.accept()

    def get_metadata(self) -> dict | None:
        """Returns the bulk edit settings after dialog acceptance.

        Returns:
            Dictionary containing the bulk edit settings, or None if
            the dialog was cancelled or no fields were selected.
        """
        return self.result_metadata


class MetadataRestoreDialog(BaseDialog):
    """Dialog for restoring metadata modifications to original values.

    Displays information about the number of modified games and allows
    the user to confirm restoration of all changes.

    Attributes:
        modified_count: Number of games with metadata modifications.
        do_restore: Flag indicating whether restoration was confirmed.
    """

    def __init__(self, parent, modified_count: int):
        """Initializes the metadata restore dialog.

        Args:
            parent: Parent widget for the dialog.
            modified_count: Number of games with modifications to restore.
        """
        self.modified_count = modified_count
        self.do_restore = False
        super().__init__(parent, title_key="menu.edit.reset_metadata", buttons="custom")

    def _build_content(self, layout: QVBoxLayout) -> None:
        """Adds restore info, warning, and action buttons.

        Args:
            layout: The main vertical layout.
        """
        info_lbl = QLabel(t("ui.metadata_editor.restore_info", count=self.modified_count))
        info_lbl.setWordWrap(True)
        layout.addWidget(info_lbl)

        warn_lbl = QLabel(f"{t('emoji.warning')} {t('auto_categorize.warning_backup')}")
        warn_lbl.setStyleSheet("color: orange;")
        layout.addWidget(warn_lbl)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton(t("common.cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        restore_btn = QPushButton(t("ui.metadata_editor.restore_button", count=self.modified_count))
        restore_btn.setDefault(True)
        restore_btn.clicked.connect(self._restore)
        btn_layout.addWidget(restore_btn)

        layout.addLayout(btn_layout)

    def _restore(self):
        """Handles the restore button click.

        Sets the restore flag and accepts the dialog.
        """
        self.do_restore = True
        self.accept()

    def should_restore(self) -> bool:
        """Returns whether restoration was confirmed by the user.

        Returns:
            True if the user clicked the restore button, False otherwise.
        """
        return self.do_restore
