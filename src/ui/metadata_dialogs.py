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
        layout = QVBoxLayout(self)

        title = QLabel(t('ui.metadata_editor.editing_title', game=self.game_name))
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        info = QLabel(t('ui.metadata_editor.info_tracking'))
        info.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info)

        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.sort_as_edit = QLineEdit()
        self.developer_edit = QLineEdit()
        self.publisher_edit = QLineEdit()
        self.release_date_edit = QLineEdit()

        form.addRow(t('ui.game_details.release_year') + ":", self.release_date_edit)

        # NEU: Write to VDF Checkbox
        date_help = QLabel(t('ui.metadata_editor.date_help'))
        date_help.setStyleSheet("color: gray; font-size: 9px;")
        form.addRow("", date_help)

        layout.addLayout(form)

        # NEU: Write to VDF Option
        vdf_group = QGroupBox("Advanced Options")
        vdf_layout = QVBoxLayout()

        self.write_to_vdf_cb = QCheckBox(t('ui.metadata_editor.write_to_vdf'))
        self.write_to_vdf_cb.setToolTip(t('ui.metadata_editor.write_to_vdf_tooltip'))
        self.write_to_vdf_cb.setChecked(False)  # Default: NUR JSON

        vdf_layout.addWidget(self.write_to_vdf_cb)
        vdf_group.setLayout(vdf_layout)
        layout.addWidget(vdf_group)

        form.addRow(t('ui.metadata_editor.game_name_label'), self.name_edit)
        form.addRow(t('ui.metadata_editor.sort_as_label'), self.sort_as_edit)

        sort_help = QLabel(t('ui.metadata_editor.sort_as_help'))
        sort_help.setStyleSheet("color: gray; font-size: 9px;")
        form.addRow("", sort_help)

        form.addRow(t('ui.game_details.developer') + ":", self.developer_edit)
        form.addRow(t('ui.game_details.publisher') + ":", self.publisher_edit)
        form.addRow(t('ui.game_details.release_year') + ":", self.release_date_edit)

        layout.addLayout(form)

        original_group = QGroupBox(t('ui.metadata_editor.original_values_group'))
        original_layout = QVBoxLayout()
        self.original_text = QTextEdit()
        self.original_text.setReadOnly(True)
        self.original_text.setMaximumHeight(100)
        original_layout.addWidget(self.original_text)
        original_group.setLayout(original_layout)
        layout.addWidget(original_group)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        # FIX: Dynamische Button-Erstellung verhindert Duplikate
        for text, callback, is_default in [
            (t('ui.settings.reset_defaults'), self._reset_to_original, False),
            (t('ui.dialogs.cancel'), self.reject, False),
            (t('ui.settings.save'), self._save, True)
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(callback)
            if is_default:
                btn.setDefault(True)
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)

    def _populate_fields(self):
        m = self.current_metadata
        self.name_edit.setText(m.get('name', ''))
        self.sort_as_edit.setText(m.get('sort_as', ''))
        self.developer_edit.setText(m.get('developer', ''))
        self.publisher_edit.setText(m.get('publisher', ''))
        self.release_date_edit.setText(str(m.get('release_date', '')))

        na = 'N/A'
        lines = [
            f"{t('ui.game_details.name')}: {m.get('name', na)}",
            f"{t('ui.game_details.developer')}: {m.get('developer', na)}",
            f"{t('ui.game_details.publisher')}: {m.get('publisher', na)}",
            f"{t('ui.game_details.release_year')}: {m.get('release_date', na)}"
        ]
        self.original_text.setPlainText('\n'.join(lines))

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
            'write_to_vdf': self.write_to_vdf_cb.isChecked()  # NEU!
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

    @staticmethod
    def _add_bulk_field(layout, label_text, placeholder=""):
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
        layout = QVBoxLayout(self)
        title = QLabel(t('ui.metadata_editor.bulk_title', count=self.games_count))
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        info = QLabel(t('ui.metadata_editor.bulk_info', count=self.games_count))
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

        # Felderstellung mittels Hilfsmethode
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

        warn_lbl = QLabel(t('ui.auto_categorize.warning_backup'))
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
        checks = [self.cb_dev, self.cb_pub, self.cb_date, self.cb_pre, self.cb_suf, self.cb_rem]
        if not any(c.isChecked() for c in checks):
            QMessageBox.warning(self, t('ui.dialogs.no_changes'), t('ui.dialogs.no_selection'))
            return

        confirm = QMessageBox.question(self, t('ui.dialogs.confirm_bulk_title'),
                                       t('ui.dialogs.confirm_bulk', count=self.games_count),
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.result_metadata = {}
        if self.cb_dev.isChecked(): self.result_metadata['developer'] = self.edit_dev.text().strip()
        if self.cb_pub.isChecked(): self.result_metadata['publisher'] = self.edit_pub.text().strip()
        if self.cb_date.isChecked(): self.result_metadata['release_date'] = self.edit_date.text().strip()

        mods = {}
        if self.cb_pre.isChecked(): mods['prefix'] = self.edit_pre.text()
        if self.cb_suf.isChecked(): mods['suffix'] = self.edit_suf.text()
        if self.cb_rem.isChecked(): mods['remove'] = self.edit_rem.text()
        if mods: self.result_metadata['name_modifications'] = mods

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
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title)

        info_lbl = QLabel(t('ui.metadata_editor.restore_info', count=self.modified_count))
        info_lbl.setWordWrap(True)
        layout.addWidget(info_lbl)

        warn_lbl = QLabel(t('ui.auto_categorize.warning_backup'))
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
        self.do_restore = True
        self.accept()

    def should_restore(self) -> bool:
        return self.do_restore