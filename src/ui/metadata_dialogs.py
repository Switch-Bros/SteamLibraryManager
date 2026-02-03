"""
Metadata editing dialogs for Steam Library Manager.

This module provides dialogs for editing game metadata, including single-game
editing, bulk editing for multiple games, and restoration of original values.
All dialogs feature visual indicators for modified fields and VDF write options.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QTextEdit, QGroupBox,
    QCheckBox, QMessageBox
)
from PyQt6.QtGui import QFont
from typing import Optional, Dict, List
from src.ui.components.ui_helper import UIHelper
from src.utils.i18n import t
from src.utils.date_utils import parse_date_to_timestamp, format_timestamp_to_date


class MetadataEditDialog(QDialog):
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

    def __init__(self, parent, game_name: str, current_metadata: Dict,
                 original_metadata: Optional[Dict] = None):
        """Initializes the metadata edit dialog.

        Args:
            parent: Parent widget for the dialog.
            game_name: Name of the game to display in the title.
            current_metadata: Dictionary with current metadata values.
            original_metadata: Optional dictionary with original values for
                comparison and revert functionality.
        """
        super().__init__(parent)
        self.game_name = game_name
        self.current_metadata = current_metadata
        self.original_metadata = original_metadata or {}
        self.result_metadata = None

        self.setWindowTitle(t('ui.metadata_editor.editing_title', game=game_name))
        self.setMinimumWidth(600)
        self.setModal(True)

        self._create_ui()
        self._populate_fields()

    def _create_ui(self):
        """Creates the dialog user interface.

        Sets up the form layout with input fields, VDF options group,
        original values display, and action buttons.
        """
        layout = QVBoxLayout(self)

        # Title
        title = QLabel(t('ui.metadata_editor.editing_title', game=self.game_name))
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        # Info
        info = QLabel(t('ui.metadata_editor.info_tracking'))
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
        form.addRow(t('ui.metadata_editor.game_name_label'), self.name_edit)
        form.addRow(t('ui.metadata_editor.sort_as_label'), self.sort_as_edit)

        # Sort Help
        sort_help = QLabel(t('ui.metadata_editor.sort_as_help'))
        sort_help.setStyleSheet("color: gray; font-size: 9px;")
        form.addRow("", sort_help)

        form.addRow(t('ui.game_details.developer') + ":", self.developer_edit)
        form.addRow(t('ui.game_details.publisher') + ":", self.publisher_edit)
        form.addRow(t('ui.game_details.release_year') + ":", self.release_date_edit)

        # Date Help
        date_help = QLabel(t('ui.metadata_editor.date_help'))
        date_help.setStyleSheet("color: gray; font-size: 9px;")
        form.addRow("", date_help)

        layout.addLayout(form)

        # VDF Write Option
        vdf_group = QGroupBox(t('ui.metadata_editor.vdf_section'))
        vdf_layout = QVBoxLayout()

        self.write_to_vdf_cb = QCheckBox(t('ui.metadata_editor.write_to_vdf'))
        self.write_to_vdf_cb.setToolTip(t('ui.metadata_editor.write_to_vdf_tooltip'))
        self.write_to_vdf_cb.setChecked(True)

        vdf_layout.addWidget(self.write_to_vdf_cb)

        # Info Text
        vdf_info = QLabel(t('ui.metadata_editor.vdf_info'))
        vdf_info.setWordWrap(True)
        vdf_info.setStyleSheet("color: #888; font-size: 9px; padding: 5px;")
        vdf_layout.addWidget(vdf_info)

        vdf_group.setLayout(vdf_layout)
        layout.addWidget(vdf_group)

        # Original Values Group
        original_group = QGroupBox(t('ui.metadata_editor.original_values_group'))
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
        revert_btn = QPushButton(t('ui.metadata_editor.revert_to_original'))
        revert_btn.setStyleSheet("background-color: #6c757d; color: white;")
        revert_btn.clicked.connect(self._revert_to_original)
        btn_layout.addWidget(revert_btn)

        cancel_btn = QPushButton(t('ui.dialogs.cancel'))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton(t('ui.settings.save'))
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _populate_fields(self):
        """Populates form fields with current metadata values.

        Fills all input fields with values from current_metadata and applies
        visual highlighting to fields that differ from original values.
        Also displays original values in the read-only text area.
        """
        m = self.current_metadata

        # Populate fields
        self.name_edit.setText(m.get('name', ''))
        self.sort_as_edit.setText(m.get('sort_as', ''))
        self.developer_edit.setText(m.get('developer', ''))
        self.publisher_edit.setText(m.get('publisher', ''))
        # Convert raw timestamp → DD.MM.YYYY before displaying
        self.release_date_edit.setText(format_timestamp_to_date(m.get('release_date', '')))

        # Visual indicator for modified fields
        if self.original_metadata:
            self._highlight_modified_fields()

        # Show original values (dates formatted for display)
        na = t('ui.game_details.value_unknown')
        if self.original_metadata:
            # Show REAL originals
            lines = [
                f"{t('ui.game_details.name')}: {self.original_metadata.get('name', na)}",
                f"{t('ui.game_details.developer')}: {self.original_metadata.get('developer', na)}",
                f"{t('ui.game_details.publisher')}: {self.original_metadata.get('publisher', na)}",
                f"{t('ui.game_details.release_year')}: {format_timestamp_to_date(self.original_metadata.get('release_date', '')) or na}"
            ]
        else:
            # Fallback: Show current values
            lines = [
                f"{t('ui.game_details.name')}: {m.get('name', na)}",
                f"{t('ui.game_details.developer')}: {m.get('developer', na)}",
                f"{t('ui.game_details.publisher')}: {m.get('publisher', na)}",
                f"{t('ui.game_details.release_year')}: {format_timestamp_to_date(m.get('release_date', '')) or na}"
            ]

        self.original_text.setPlainText('\n'.join(lines))

    def _highlight_modified_fields(self):
        """Highlights fields that differ from original values.

        Applies a yellow background style and tooltip to fields where the
        current value differs from the original value.
        """
        modified_style = "background-color: #FFF3CD; border: 2px solid #FFA500;"

        m = self.current_metadata
        o = self.original_metadata

        # Name
        if m.get('name', '') != o.get('name', ''):
            self.name_edit.setStyleSheet(modified_style)
            self.name_edit.setToolTip(t('ui.metadata_editor.modified_tooltip',
                                        original=o.get('name', t('ui.game_details.value_unknown'))))

        # Developer
        if m.get('developer', '') != o.get('developer', ''):
            self.developer_edit.setStyleSheet(modified_style)
            self.developer_edit.setToolTip(t('ui.metadata_editor.modified_tooltip',
                                             original=o.get('developer', t('ui.game_details.value_unknown'))))

        # Publisher
        if m.get('publisher', '') != o.get('publisher', ''):
            self.publisher_edit.setStyleSheet(modified_style)
            self.publisher_edit.setToolTip(t('ui.metadata_editor.modified_tooltip',
                                             original=o.get('publisher', t('ui.game_details.value_unknown'))))

        # Release Date
        if str(m.get('release_date', '')) != str(o.get('release_date', '')):
            self.release_date_edit.setStyleSheet(modified_style)
            self.release_date_edit.setToolTip(t('ui.metadata_editor.modified_tooltip',
                                                original=o.get('release_date', t('ui.game_details.value_unknown'))))

    def _revert_to_original(self):
        """Restores all fields to their original values.

        Shows an information dialog if no original values exist, or a
        confirmation dialog before reverting. Clears all modified styling
        after successful revert.
        """
        if not self.original_metadata:
            QMessageBox.information(
                self,
                t('ui.metadata_editor.revert_title'),
                t('ui.metadata_editor.revert_no_original')
            )
            return

            # Confirm via centralised helper (localised Yes/No buttons)
        if not UIHelper.confirm(self,
                                t('ui.metadata_editor.revert_confirm'),
                                t('ui.metadata_editor.revert_title')):
            return  # User clicked "No" → abort

            # --- Revert all fields to their original values ---
        self.name_edit.setText(self.original_metadata.get('name', ''))
        self.developer_edit.setText(self.original_metadata.get('developer', ''))
        self.publisher_edit.setText(self.original_metadata.get('publisher', ''))
        # Format timestamp back to localised date on revert
        self.release_date_edit.setText(format_timestamp_to_date(self.original_metadata.get('release_date', '')))

        # Clear modified styles
        for widget in (self.name_edit, self.developer_edit,
                       self.publisher_edit, self.release_date_edit):
            widget.setStyleSheet("")
            widget.setToolTip("")

    def _save(self):
        """Validates and saves the edited metadata.

        Validates that the name field is not empty, shows a VDF write warning
        dialog on first use, and stores the result metadata if validation passes.
        """
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, t('ui.dialogs.error'), t('ui.metadata_editor.error_empty_name'))
            return

        # Warning dialog if VDF-Write enabled
        if self.write_to_vdf_cb.isChecked():
            # Show warning only once per session
            if not hasattr(self.parent(), '_vdf_warning_shown'):
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle(t('ui.metadata_editor.vdf_warning_title'))
                msg.setText(t('ui.metadata_editor.vdf_warning_text'))
                msg.setInformativeText(t('ui.metadata_editor.vdf_warning_details'))

                # Manual buttons — bypasses broken Qt StandardButton translation on Linux
                yes_btn = msg.addButton(t('common.yes'), QMessageBox.ButtonRole.YesRole)
                msg.addButton(t('common.no'), QMessageBox.ButtonRole.NoRole)
                msg.setDefaultButton(yes_btn)

                msg.exec()
                if msg.clickedButton() != yes_btn:
                    return  # User clicked "No" → abort save

                self.parent()._vdf_warning_shown = True

        self.result_metadata = {
            'name': name,
            'sort_as': self.sort_as_edit.text().strip() or name,
            'developer': self.developer_edit.text().strip(),
            'publisher': self.publisher_edit.text().strip(),
            'release_date': parse_date_to_timestamp(self.release_date_edit.text().strip()),  # ← FIX!
            'write_to_vdf': self.write_to_vdf_cb.isChecked()
        }
        self.accept()

    def get_metadata(self) -> Optional[Dict]:
        """Returns the edited metadata after dialog acceptance.

        Returns:
            Dictionary containing the edited metadata values, or None if
            the dialog was cancelled or validation failed.
        """
        return self.result_metadata


class BulkMetadataEditDialog(QDialog):
    """Dialog for editing metadata of multiple games simultaneously.

    Allows users to apply the same metadata changes to multiple games at once.
    Supports setting developer, publisher, release date, and name modifications
    (prefix, suffix, text removal).

    Attributes:
        games_count: Number of games to be edited.
        game_names: List of names of games being edited.
        result_metadata: Dictionary containing the bulk edit settings after save.
    """

    def __init__(self, parent, games_count: int, game_names: List[str]):
        """Initializes the bulk metadata edit dialog.

        Args:
            parent: Parent widget for the dialog.
            games_count: Total number of games to be edited.
            game_names: List of game names for preview display.
        """
        super().__init__(parent)
        self.games_count = games_count
        self.game_names = game_names
        self.result_metadata = None

        self.setWindowTitle(t('ui.metadata_editor.bulk_title', count=games_count))
        self.setMinimumWidth(600)
        self.setModal(True)
        self._create_ui()

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

    def _create_ui(self):
        """Creates the bulk edit dialog user interface.

        Sets up the layout with title, game preview list, editable fields
        with checkboxes, warning label, and action buttons.
        """
        layout = QVBoxLayout(self)
        title = QLabel(t('ui.metadata_editor.bulk_title', count=self.games_count))
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        # Emoji prefix assembled in code — keeps locale strings clean
        info = QLabel(f"{t('emoji.warning')} {t('ui.metadata_editor.bulk_info', count=self.games_count)}")
        info.setStyleSheet("color: orange; font-size: 11px;")
        layout.addWidget(info)

        preview_group = QGroupBox(t('ui.metadata_editor.bulk_preview', count=self.games_count))
        preview_layout = QVBoxLayout()
        preview_text = QTextEdit()
        preview_text.setReadOnly(True)
        preview_text.setMaximumHeight(120)

        names = self.game_names[:20]
        if len(self.game_names) > 20:
            names.append(t('ui.metadata_editor.bulk_more', count=len(self.game_names) - 20))
        preview_text.setPlainText('\n'.join(names))

        preview_layout.addWidget(preview_text)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        fields_group = QGroupBox(t('ui.metadata_editor.fields_group'))
        f_layout = QVBoxLayout()

        self.cb_dev, self.edit_dev = self._add_bulk_field(f_layout, t('ui.metadata_editor.set_field',
                                                                      field=t('ui.game_details.developer')))
        self.cb_pub, self.edit_pub = self._add_bulk_field(f_layout, t('ui.metadata_editor.set_field',
                                                                      field=t('ui.game_details.publisher')))
        self.cb_date, self.edit_date = self._add_bulk_field(f_layout, t('ui.metadata_editor.set_field',
                                                                        field=t('ui.game_details.release_year')),
                                                            t('ui.metadata_editor.date_help'))
        self.cb_pre, self.edit_pre = self._add_bulk_field(f_layout, t('ui.metadata_editor.add_prefix'))
        self.cb_suf, self.edit_suf = self._add_bulk_field(f_layout, t('ui.metadata_editor.add_suffix'))
        self.cb_rem, self.edit_rem = self._add_bulk_field(f_layout, t('ui.metadata_editor.remove_text'))

        fields_group.setLayout(f_layout)
        layout.addWidget(fields_group)

        warn_lbl = QLabel(f"{t('emoji.warning')} {t('ui.auto_categorize.warning_backup')}")
        warn_lbl.setStyleSheet("color: orange;")
        layout.addWidget(warn_lbl)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        for text, callback, is_def in [
            (t('ui.dialogs.cancel'), self.reject, False),
            (t('ui.metadata_editor.apply_button', count=self.games_count), self._apply, True)
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(callback)
            if is_def:
                btn.setDefault(True)
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)

    def _apply(self):
        """Validates selections and stores the bulk edit settings.

        Validates that at least one field is selected for editing, shows a
        confirmation dialog, and stores the result metadata if confirmed.
        """
        checks = [self.cb_dev, self.cb_pub, self.cb_date, self.cb_pre, self.cb_suf, self.cb_rem]
        if not any(c.isChecked() for c in checks):
            QMessageBox.warning(self, t('ui.dialogs.no_changes'), t('ui.dialogs.no_selection'))
            return

        # Centralised helper — localised Yes/No buttons
        if not UIHelper.confirm(self,
                                t('ui.dialogs.confirm_bulk', count=self.games_count),
                                t('ui.dialogs.confirm_bulk_title')):
            return

        self.result_metadata = {}
        if self.cb_dev.isChecked(): self.result_metadata['developer'] = self.edit_dev.text().strip()
        if self.cb_pub.isChecked(): self.result_metadata['publisher'] = self.edit_pub.text().strip()
        if self.cb_date.isChecked():
            self.result_metadata['release_date'] = parse_date_to_timestamp(self.edit_date.text().strip())  # ← FIX!

        mods = {}
        if self.cb_pre.isChecked(): mods['prefix'] = self.edit_pre.text()
        if self.cb_suf.isChecked(): mods['suffix'] = self.edit_suf.text()
        if self.cb_rem.isChecked(): mods['remove'] = self.edit_rem.text()
        if mods: self.result_metadata['name_modifications'] = mods

        self.accept()

    def get_metadata(self) -> Optional[Dict]:
        """Returns the bulk edit settings after dialog acceptance.

        Returns:
            Dictionary containing the bulk edit settings, or None if
            the dialog was cancelled or no fields were selected.
        """
        return self.result_metadata


class MetadataRestoreDialog(QDialog):
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
        super().__init__(parent)
        self.modified_count = modified_count
        self.do_restore = False
        self.setWindowTitle(t('ui.menu.restore'))
        self.setMinimumWidth(500)
        self.setModal(True)
        self._create_ui()

    def _create_ui(self):
        """Creates the restore dialog user interface.

        Sets up the layout with title, information label, warning label,
        and action buttons.
        """
        layout = QVBoxLayout(self)
        title = QLabel(t('ui.menu.restore'))
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title)

        info_lbl = QLabel(t('ui.metadata_editor.restore_info', count=self.modified_count))
        info_lbl.setWordWrap(True)
        layout.addWidget(info_lbl)

        warn_lbl = QLabel(f"{t('emoji.warning')} {t('ui.auto_categorize.warning_backup')}")
        warn_lbl.setStyleSheet("color: orange;")
        layout.addWidget(warn_lbl)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        for text, callback, is_def in [
            (t('ui.dialogs.cancel'), self.reject, False),
            (t('ui.metadata_editor.restore_button', count=self.modified_count), self._restore, True)
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(callback)
            if is_def:
                btn.setDefault(True)
            btn_layout.addWidget(btn)

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