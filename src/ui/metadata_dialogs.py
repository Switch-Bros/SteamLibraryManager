"""
Metadata Edit Dialogs - Enhanced UX with Visual Indicators & Warnings (100% i18n)
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
    """Dialog für Einzel-Spiel Metadaten Bearbeitung mit Visual Feedback"""

    def __init__(self, parent, game_name: str, current_metadata: Dict, original_metadata: Optional[Dict] = None):
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

        # Input-Felder
        self.name_edit = QLineEdit()
        self.sort_as_edit = QLineEdit()
        self.developer_edit = QLineEdit()
        self.publisher_edit = QLineEdit()
        self.release_date_edit = QLineEdit()

        # Form aufbauen
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
        """Befülle Felder und markiere geänderte Werte"""
        m = self.current_metadata
        
        # Befülle Felder
        self.name_edit.setText(m.get('name', ''))
        self.sort_as_edit.setText(m.get('sort_as', ''))
        self.developer_edit.setText(m.get('developer', ''))
        self.publisher_edit.setText(m.get('publisher', ''))
        self.release_date_edit.setText(str(m.get('release_date', '')))

        # Visual Indicator für geänderte Felder
        if self.original_metadata:
            self._highlight_modified_fields()

        # Original Values anzeigen
        na = t('ui.game_details.value_unknown')
        if self.original_metadata:
            # Zeige ECHTE Originale
            lines = [
                f"{t('ui.game_details.name')}: {self.original_metadata.get('name', na)}",
                f"{t('ui.game_details.developer')}: {self.original_metadata.get('developer', na)}",
                f"{t('ui.game_details.publisher')}: {self.original_metadata.get('publisher', na)}",
                f"{t('ui.game_details.release_year')}: {self.original_metadata.get('release_date', na)}"
            ]
        else:
            # Fallback: Zeige aktuelle Werte
            lines = [
                f"{t('ui.game_details.name')}: {m.get('name', na)}",
                f"{t('ui.game_details.developer')}: {m.get('developer', na)}",
                f"{t('ui.game_details.publisher')}: {m.get('publisher', na)}",
                f"{t('ui.game_details.release_year')}: {m.get('release_date', na)}"
            ]
        
        self.original_text.setPlainText('\n'.join(lines))

    def _highlight_modified_fields(self):
        """Markiere geänderte Felder gelb"""
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
        """Stelle Original-Werte wieder her"""
        if not self.original_metadata:
            QMessageBox.information(
                self,
                t('ui.metadata_editor.revert_title'),
                t('ui.metadata_editor.revert_no_original')
            )
            return
        
        # Confirm
        reply = QMessageBox.question(
            self,
            t('ui.metadata_editor.revert_title'),
            t('ui.metadata_editor.revert_confirm'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Setze Original-Werte
            self.name_edit.setText(self.original_metadata.get('name', ''))
            self.developer_edit.setText(self.original_metadata.get('developer', ''))
            self.publisher_edit.setText(self.original_metadata.get('publisher', ''))
            self.release_date_edit.setText(str(self.original_metadata.get('release_date', '')))
            
            # Clear modified styles
            normal_style = ""
            self.name_edit.setStyleSheet(normal_style)
            self.developer_edit.setStyleSheet(normal_style)
            self.publisher_edit.setStyleSheet(normal_style)
            self.release_date_edit.setStyleSheet(normal_style)
            
            # Clear tooltips
            self.name_edit.setToolTip("")
            self.developer_edit.setToolTip("")
            self.publisher_edit.setToolTip("")
            self.release_date_edit.setToolTip("")

    def _save(self):
        """Speichere mit optionalem VDF-Warning"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, t('ui.dialogs.error'), t('ui.metadata_editor.error_empty_name'))
            return

        # Warning Dialog wenn VDF-Write aktiviert
        if self.write_to_vdf_cb.isChecked():
            # Zeige Warnung beim ersten Mal (pro Session)
            if not hasattr(self.parent(), '_vdf_warning_shown'):
                msg = QMessageBox(self)
                msg.setIcon(QMessageBox.Icon.Information)
                msg.setWindowTitle(t('ui.metadata_editor.vdf_warning_title'))
                
                msg.setText(t('ui.metadata_editor.vdf_warning_text'))
                msg.setInformativeText(t('ui.metadata_editor.vdf_warning_details'))
                
                msg.setStandardButtons(
                    QMessageBox.StandardButton.Yes | 
                    QMessageBox.StandardButton.No
                )
                msg.setDefaultButton(QMessageBox.StandardButton.Yes)
                
                if msg.exec() != QMessageBox.StandardButton.Yes:
                    return
                
                self.parent()._vdf_warning_shown = True

        self.result_metadata = {
            'name': name,
            'sort_as': self.sort_as_edit.text().strip() or name,
            'developer': self.developer_edit.text().strip(),
            'publisher': self.publisher_edit.text().strip(),
            'release_date': self.release_date_edit.text().strip(),
            'write_to_vdf': self.write_to_vdf_cb.isChecked()
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
