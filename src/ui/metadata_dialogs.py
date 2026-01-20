"""
Metadata Edit Dialogs - Clean & i18n-ready
Speichern als: src/ui/metadata_dialogs.py
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QTextEdit, QGroupBox,
    QCheckBox, QMessageBox
)
from PyQt6.QtGui import QFont
from typing import Optional, Dict, List
from datetime import datetime
from src.utils.i18n import t


class MetadataEditDialog(QDialog):
    """Dialog für Einzel-Spiel Metadaten Bearbeitung"""

    def __init__(self, parent, game_name: str, current_metadata: Dict):
        super().__init__(parent)

        self.game_name = game_name
        self.current_metadata = current_metadata
        self.result_metadata = None

        self.setWindowTitle(t('ui.metadata_editor.editing_title', game=game_name))
        self.setMinimumWidth(600)
        self.setModal(True)

        self._create_ui()
        self._populate_fields()

    def _create_ui(self):
        """Create UI"""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel(t('ui.metadata_editor.editing_title', game=self.game_name))
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Info
        info = QLabel(t('ui.metadata_editor.info_tracking'))
        info.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info)

        # Form
        form = QFormLayout()

        self.name_edit = QLineEdit()
        form.addRow(t('ui.metadata_editor.game_name_label'), self.name_edit)

        self.sort_as_edit = QLineEdit()
        form.addRow(t('ui.metadata_editor.sort_as_label'), self.sort_as_edit)

        sort_help = QLabel(t('ui.metadata_editor.sort_as_help'))
        sort_help.setStyleSheet("color: gray; font-size: 9px;")
        form.addRow("", sort_help)

        self.developer_edit = QLineEdit()
        form.addRow(t('ui.game_details.developer') + ":", self.developer_edit)

        self.publisher_edit = QLineEdit()
        form.addRow(t('ui.game_details.publisher') + ":", self.publisher_edit)

        self.release_date_edit = QLineEdit()
        form.addRow(t('ui.game_details.release_year') + ":", self.release_date_edit)

        date_help = QLabel(t('ui.metadata_editor.date_help'))
        date_help.setStyleSheet("color: gray; font-size: 9px;")
        form.addRow("", date_help)

        layout.addLayout(form)

        # Original values display
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

        # FIX: i18n Key korrigiert (reset_defaults)
        reset_btn = QPushButton(t('ui.settings.reset_defaults'))
        reset_btn.clicked.connect(self._reset_to_original)
        btn_layout.addWidget(reset_btn)

        cancel_btn = QPushButton(t('ui.dialogs.cancel'))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton(t('ui.settings.save'))
        save_btn.clicked.connect(self._save)
        save_btn.setDefault(True)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _populate_fields(self):
        """Fill fields with current metadata"""
        self.name_edit.setText(self.current_metadata.get('name', ''))
        self.sort_as_edit.setText(self.current_metadata.get('sort_as', ''))
        self.developer_edit.setText(self.current_metadata.get('developer', ''))
        self.publisher_edit.setText(self.current_metadata.get('publisher', ''))

        release_date = self.current_metadata.get('release_date', '')
        # Simple convert to string if it's an int (timestamp)
        self.release_date_edit.setText(str(release_date))

        # Show original values
        # FIX: t() Aufrufe waren hier evtl. falsch, jetzt sichergestellt
        original_text = []
        original_text.append(f"{t('ui.game_details.name')}: {self.current_metadata.get('name', 'N/A')}")
        original_text.append(f"{t('ui.game_details.developer')}: {self.current_metadata.get('developer', 'N/A')}")
        original_text.append(f"{t('ui.game_details.publisher')}: {self.current_metadata.get('publisher', 'N/A')}")
        original_text.append(f"{t('ui.game_details.release_year')}: {self.current_metadata.get('release_date', 'N/A')}")

        self.original_text.setPlainText('\n'.join(original_text))

    def _reset_to_original(self):
        self._populate_fields()

    def _save(self):
        name = self.name_edit.text().strip()

        if not name:
            QMessageBox.warning(self, t('ui.dialogs.error'), t('ui.metadata_editor.error_empty_name'))
            return

        self.result_metadata = {
            'name': name,
            'sort_as': self.sort_as_edit.text().strip() or name,
            'developer': self.developer_edit.text().strip(),
            'publisher': self.publisher_edit.text().strip(),
            'release_date': self.release_date_edit.text().strip(),
        }

        self.accept()

    def get_metadata(self) -> Optional[Dict]:
        return self.result_metadata


class BulkMetadataEditDialog(QDialog):
    """Dialog für Bulk Metadaten Bearbeitung"""

    def __init__(self, parent, games_count: int, game_names: List[str]):
        super().__init__(parent)

        self.games_count = games_count
        self.game_names = game_names
        self.result_metadata = None

        self.setWindowTitle(t('ui.metadata_editor.bulk_title', count=games_count))
        self.setMinimumWidth(600)
        self.setModal(True)

        self._create_ui()

    def _create_ui(self):
        """Create UI"""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel(t('ui.metadata_editor.bulk_title', count=self.games_count))
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Info
        info = QLabel(t('ui.metadata_editor.bulk_info', count=self.games_count))
        info.setStyleSheet("color: orange; font-size: 11px;")
        layout.addWidget(info)

        # Selected games preview
        preview_group = QGroupBox(t('ui.metadata_editor.bulk_preview', count=self.games_count))
        preview_layout = QVBoxLayout()

        preview_text = QTextEdit()
        preview_text.setReadOnly(True)
        preview_text.setMaximumHeight(120)

        preview_names = self.game_names[:20]
        if len(self.game_names) > 20:
            preview_names.append(t('ui.metadata_editor.bulk_more', count=len(self.game_names) - 20))

        preview_text.setPlainText('\n'.join(preview_names))
        preview_layout.addWidget(preview_text)

        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # Checkboxes + Fields
        fields_group = QGroupBox(t('ui.metadata_editor.fields_group'))
        fields_layout = QVBoxLayout()

        # Developer
        dev_layout = QHBoxLayout()
        self.cb_developer = QCheckBox(t('ui.metadata_editor.set_field', field=t('ui.game_details.developer')))
        self.developer_edit = QLineEdit()
        self.developer_edit.setEnabled(False)
        self.cb_developer.toggled.connect(self.developer_edit.setEnabled)
        dev_layout.addWidget(self.cb_developer)
        dev_layout.addWidget(self.developer_edit)
        fields_layout.addLayout(dev_layout)

        # Publisher
        pub_layout = QHBoxLayout()
        self.cb_publisher = QCheckBox(t('ui.metadata_editor.set_field', field=t('ui.game_details.publisher')))
        self.publisher_edit = QLineEdit()
        self.publisher_edit.setEnabled(False)
        self.cb_publisher.toggled.connect(self.publisher_edit.setEnabled)
        pub_layout.addWidget(self.cb_publisher)
        pub_layout.addWidget(self.publisher_edit)
        fields_layout.addLayout(pub_layout)

        # Release Date
        date_layout = QHBoxLayout()
        self.cb_release_date = QCheckBox(t('ui.metadata_editor.set_field', field=t('ui.game_details.release_year')))
        self.release_date_edit = QLineEdit()
        self.release_date_edit.setPlaceholderText(t('ui.metadata_editor.date_help'))
        self.release_date_edit.setEnabled(False)
        self.cb_release_date.toggled.connect(self.release_date_edit.setEnabled)
        date_layout.addWidget(self.cb_release_date)
        date_layout.addWidget(self.release_date_edit)
        fields_layout.addLayout(date_layout)

        # Name prefix/suffix
        prefix_layout = QHBoxLayout()
        self.cb_name_prefix = QCheckBox(t('ui.metadata_editor.add_prefix'))
        self.name_prefix_edit = QLineEdit()
        self.name_prefix_edit.setEnabled(False)
        self.cb_name_prefix.toggled.connect(self.name_prefix_edit.setEnabled)
        prefix_layout.addWidget(self.cb_name_prefix)
        prefix_layout.addWidget(self.name_prefix_edit)
        fields_layout.addLayout(prefix_layout)

        suffix_layout = QHBoxLayout()
        self.cb_name_suffix = QCheckBox(t('ui.metadata_editor.add_suffix'))
        self.name_suffix_edit = QLineEdit()
        self.name_suffix_edit.setEnabled(False)
        self.cb_name_suffix.toggled.connect(self.name_suffix_edit.setEnabled)
        suffix_layout.addWidget(self.cb_name_suffix)
        suffix_layout.addWidget(self.name_suffix_edit)
        fields_layout.addLayout(suffix_layout)

        # Remove from name
        remove_layout = QHBoxLayout()
        self.cb_remove_text = QCheckBox(t('ui.metadata_editor.remove_text'))
        self.remove_text_edit = QLineEdit()
        self.remove_text_edit.setEnabled(False)
        self.cb_remove_text.toggled.connect(self.remove_text_edit.setEnabled)
        remove_layout.addWidget(self.cb_remove_text)
        remove_layout.addWidget(self.remove_text_edit)
        fields_layout.addLayout(remove_layout)

        fields_group.setLayout(fields_layout)
        layout.addWidget(fields_group)

        # Warning
        warning = QLabel(t('ui.auto_categorize.warning_backup'))
        warning.setStyleSheet("color: orange;")
        layout.addWidget(warning)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton(t('ui.dialogs.cancel'))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        apply_btn = QPushButton(t('ui.metadata_editor.apply_button', count=self.games_count))
        apply_btn.clicked.connect(self._apply)
        apply_btn.setDefault(True)
        btn_layout.addWidget(apply_btn)

        layout.addLayout(btn_layout)

    def _apply(self):
        """Apply changes"""
        # Check if at least one field is selected
        if not any([
            self.cb_developer.isChecked(),
            self.cb_publisher.isChecked(),
            self.cb_release_date.isChecked(),
            self.cb_name_prefix.isChecked(),
            self.cb_name_suffix.isChecked(),
            self.cb_remove_text.isChecked()
        ]):
            QMessageBox.warning(self, t('ui.dialogs.no_changes'), t('ui.dialogs.no_selection'))
            return

        # Confirm
        reply = QMessageBox.question(
            self,
            t('ui.dialogs.confirm_bulk_title'),
            t('ui.dialogs.confirm_bulk', count=self.games_count),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Build result
        self.result_metadata = {}

        if self.cb_developer.isChecked():
            self.result_metadata['developer'] = self.developer_edit.text().strip()

        if self.cb_publisher.isChecked():
            self.result_metadata['publisher'] = self.publisher_edit.text().strip()

        if self.cb_release_date.isChecked():
            self.result_metadata['release_date'] = self.release_date_edit.text().strip()

        name_mods = {}
        if self.cb_name_prefix.isChecked():
            name_mods['prefix'] = self.name_prefix_edit.text()

        if self.cb_name_suffix.isChecked():
            name_mods['suffix'] = self.name_suffix_edit.text()

        if self.cb_remove_text.isChecked():
            name_mods['remove'] = self.remove_text_edit.text()

        if name_mods:
            self.result_metadata['name_modifications'] = name_mods

        self.accept()

    def get_metadata(self) -> Optional[Dict]:
        return self.result_metadata


class MetadataRestoreDialog(QDialog):
    """Dialog zum Wiederherstellen von Änderungen"""

    def __init__(self, parent, modified_count: int):
        super().__init__(parent)

        self.modified_count = modified_count
        self.do_restore = False

        self.setWindowTitle(t('ui.menu.restore'))
        self.setMinimumWidth(500)
        self.setModal(True)

        self._create_ui()

    def _create_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel(t('ui.menu.restore'))
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        info = QLabel(t('ui.metadata_editor.restore_info', count=self.modified_count))
        info.setWordWrap(True)
        layout.addWidget(info)

        warning = QLabel(t('ui.auto_categorize.warning_backup'))
        warning.setStyleSheet("color: orange;")
        layout.addWidget(warning)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton(t('ui.dialogs.cancel'))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        restore_btn = QPushButton(t('ui.metadata_editor.restore_button', count=self.modified_count))
        restore_btn.clicked.connect(self._restore)
        restore_btn.setDefault(True)
        btn_layout.addWidget(restore_btn)

        layout.addLayout(btn_layout)

    def _restore(self):
        self.do_restore = True
        self.accept()

    def should_restore(self) -> bool:
        return self.do_restore