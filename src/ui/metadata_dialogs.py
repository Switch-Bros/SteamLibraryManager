"""
Metadata Edit Dialogs - Einzel- und Bulk-Bearbeitung
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QTextEdit, QGroupBox,
    QCheckBox, QMessageBox, QProgressDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from typing import Optional, Dict, List
from datetime import datetime


class MetadataEditDialog(QDialog):
    """Dialog für Einzel-Spiel Metadaten Bearbeitung"""

    def __init__(self, parent, game_name: str, current_metadata: Dict):
        super().__init__(parent)

        self.game_name = game_name
        self.current_metadata = current_metadata
        self.result_metadata = None

        self.setWindowTitle(f"Edit Metadata - {game_name}")
        self.setMinimumWidth(600)
        self.setModal(True)

        self._create_ui()
        self._populate_fields()

    def _create_ui(self):
        """Create UI"""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel(f"Editing: {self.game_name}")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Info
        info = QLabel("Changes are local and may be overwritten by Steam.\n"
                      "Steam Library Manager will track and restore your changes.")
        info.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info)

        # Form
        form = QFormLayout()

        self.name_edit = QLineEdit()
        form.addRow("Game Name:", self.name_edit)

        self.sort_as_edit = QLineEdit()
        form.addRow("Sort As:", self.sort_as_edit)

        sort_help = QLabel("(Used for alphabetical sorting. Auto-filled if empty.)")
        sort_help.setStyleSheet("color: gray; font-size: 9px;")
        form.addRow("", sort_help)

        self.developer_edit = QLineEdit()
        form.addRow("Developer:", self.developer_edit)

        self.publisher_edit = QLineEdit()
        form.addRow("Publisher:", self.publisher_edit)

        self.release_date_edit = QLineEdit()
        form.addRow("Release Date:", self.release_date_edit)

        date_help = QLabel("(Format: YYYY-MM-DD or Unix timestamp)")
        date_help.setStyleSheet("color: gray; font-size: 9px;")
        form.addRow("", date_help)

        layout.addLayout(form)

        # Original values display
        original_group = QGroupBox("Original Values (for reference)")
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

        reset_btn = QPushButton("Reset to Original")
        reset_btn.clicked.connect(self._reset_to_original)
        btn_layout.addWidget(reset_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Changes")
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
        if isinstance(release_date, int):
            # Convert Unix timestamp to readable format
            try:
                dt = datetime.fromtimestamp(release_date)
                release_date = dt.strftime('%Y-%m-%d')
            except:
                pass
        self.release_date_edit.setText(str(release_date))

        # Show original values
        original_text = []
        original_text.append(f"Name: {self.current_metadata.get('name', 'N/A')}")
        original_text.append(f"Developer: {self.current_metadata.get('developer', 'N/A')}")
        original_text.append(f"Publisher: {self.current_metadata.get('publisher', 'N/A')}")
        original_text.append(f"Release Date: {self.current_metadata.get('release_date', 'N/A')}")

        self.original_text.setPlainText('\n'.join(original_text))

    def _reset_to_original(self):
        """Reset all fields to original values"""
        self._populate_fields()

    def _save(self):
        """Save changes"""
        name = self.name_edit.text().strip()

        if not name:
            QMessageBox.warning(self, "Invalid Input", "Game name cannot be empty!")
            return

        # Build result metadata
        self.result_metadata = {
            'name': name,
            'sort_as': self.sort_as_edit.text().strip() or name,  # Auto-fill if empty
            'developer': self.developer_edit.text().strip(),
            'publisher': self.publisher_edit.text().strip(),
            'release_date': self.release_date_edit.text().strip(),
        }

        self.accept()

    def get_metadata(self) -> Optional[Dict]:
        """Get the edited metadata (None if canceled)"""
        return self.result_metadata


class BulkMetadataEditDialog(QDialog):
    """Dialog für Bulk Metadaten Bearbeitung"""

    def __init__(self, parent, games_count: int, game_names: List[str]):
        super().__init__(parent)

        self.games_count = games_count
        self.game_names = game_names
        self.result_metadata = None

        self.setWindowTitle(f"Bulk Edit Metadata - {games_count} Games")
        self.setMinimumWidth(600)
        self.setModal(True)

        self._create_ui()

    def _create_ui(self):
        """Create UI"""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel(f"Bulk Editing {self.games_count} Games")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Info
        info = QLabel(f"Only filled fields will be applied to all {self.games_count} selected games.\n"
                      "Leave fields empty to keep original values.")
        info.setStyleSheet("color: orange; font-size: 11px;")
        layout.addWidget(info)

        # Selected games preview
        preview_group = QGroupBox(f"Selected Games ({self.games_count})")
        preview_layout = QVBoxLayout()

        preview_text = QTextEdit()
        preview_text.setReadOnly(True)
        preview_text.setMaximumHeight(120)

        # Show first 20 games
        preview_names = self.game_names[:20]
        if len(self.game_names) > 20:
            preview_names.append(f"... and {len(self.game_names) - 20} more games")

        preview_text.setPlainText('\n'.join(preview_names))
        preview_layout.addWidget(preview_text)

        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # Checkboxes + Fields
        fields_group = QGroupBox("Fields to Modify")
        fields_layout = QVBoxLayout()

        # Developer
        dev_layout = QHBoxLayout()
        self.cb_developer = QCheckBox("Set Developer:")
        self.developer_edit = QLineEdit()
        self.developer_edit.setEnabled(False)
        self.cb_developer.toggled.connect(self.developer_edit.setEnabled)
        dev_layout.addWidget(self.cb_developer)
        dev_layout.addWidget(self.developer_edit)
        fields_layout.addLayout(dev_layout)

        # Publisher
        pub_layout = QHBoxLayout()
        self.cb_publisher = QCheckBox("Set Publisher:")
        self.publisher_edit = QLineEdit()
        self.publisher_edit.setEnabled(False)
        self.cb_publisher.toggled.connect(self.publisher_edit.setEnabled)
        pub_layout.addWidget(self.cb_publisher)
        pub_layout.addWidget(self.publisher_edit)
        fields_layout.addLayout(pub_layout)

        # Release Date
        date_layout = QHBoxLayout()
        self.cb_release_date = QCheckBox("Set Release Date:")
        self.release_date_edit = QLineEdit()
        self.release_date_edit.setPlaceholderText("YYYY-MM-DD or Unix timestamp")
        self.release_date_edit.setEnabled(False)
        self.cb_release_date.toggled.connect(self.release_date_edit.setEnabled)
        date_layout.addWidget(self.cb_release_date)
        date_layout.addWidget(self.release_date_edit)
        fields_layout.addLayout(date_layout)

        # Name prefix/suffix
        prefix_layout = QHBoxLayout()
        self.cb_name_prefix = QCheckBox("Add Prefix to Name:")
        self.name_prefix_edit = QLineEdit()
        self.name_prefix_edit.setPlaceholderText("e.g., '[HD]' or '★'")
        self.name_prefix_edit.setEnabled(False)
        self.cb_name_prefix.toggled.connect(self.name_prefix_edit.setEnabled)
        prefix_layout.addWidget(self.cb_name_prefix)
        prefix_layout.addWidget(self.name_prefix_edit)
        fields_layout.addLayout(prefix_layout)

        suffix_layout = QHBoxLayout()
        self.cb_name_suffix = QCheckBox("Add Suffix to Name:")
        self.name_suffix_edit = QLineEdit()
        self.name_suffix_edit.setPlaceholderText("e.g., '(Remastered)' or '✓'")
        self.name_suffix_edit.setEnabled(False)
        self.cb_name_suffix.toggled.connect(self.name_suffix_edit.setEnabled)
        suffix_layout.addWidget(self.cb_name_suffix)
        suffix_layout.addWidget(self.name_suffix_edit)
        fields_layout.addLayout(suffix_layout)

        # Remove from name
        remove_layout = QHBoxLayout()
        self.cb_remove_text = QCheckBox("Remove Text from Name:")
        self.remove_text_edit = QLineEdit()
        self.remove_text_edit.setPlaceholderText("e.g., '®' or 'Edition'")
        self.remove_text_edit.setEnabled(False)
        self.cb_remove_text.toggled.connect(self.remove_text_edit.setEnabled)
        remove_layout.addWidget(self.cb_remove_text)
        remove_layout.addWidget(self.remove_text_edit)
        fields_layout.addLayout(remove_layout)

        fields_group.setLayout(fields_layout)
        layout.addWidget(fields_group)

        # Warning
        warning = QLabel("⚠️ Changes will be applied to ALL selected games!\n"
                         "A backup will be created automatically.")
        warning.setStyleSheet("color: orange;")
        layout.addWidget(warning)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        apply_btn = QPushButton(f"Apply to {self.games_count} Games")
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
            QMessageBox.warning(self, "No Changes",
                                "Please select at least one field to modify!")
            return

        # Confirm
        reply = QMessageBox.question(
            self,
            "Confirm Bulk Edit",
            f"This will modify {self.games_count} games.\n\n"
            "A backup will be created. Continue?",
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

        # Name modifications (special handling)
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
        """Get the bulk edit settings (None if canceled)"""
        return self.result_metadata


class MetadataRestoreDialog(QDialog):
    """Dialog zum Wiederherstellen von Änderungen"""

    def __init__(self, parent, modified_count: int):
        super().__init__(parent)

        self.modified_count = modified_count
        self.do_restore = False

        self.setWindowTitle("Restore Metadata Changes")
        self.setMinimumWidth(500)
        self.setModal(True)

        self._create_ui()

    def _create_ui(self):
        """Create UI"""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("🔄 Restore Metadata Changes")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Info
        info = QLabel(
            f"Steam Library Manager has tracked {self.modified_count} modified games.\n\n"
            "If Steam has overwritten your changes, you can restore them now.\n\n"
            "This will re-apply all your custom metadata (names, developers, etc.)"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Warning
        warning = QLabel("⚠️ A backup will be created before restoring.")
        warning.setStyleSheet("color: orange;")
        layout.addWidget(warning)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        restore_btn = QPushButton(f"Restore {self.modified_count} Changes")
        restore_btn.clicked.connect(self._restore)
        restore_btn.setDefault(True)
        btn_layout.addWidget(restore_btn)

        layout.addLayout(btn_layout)

    def _restore(self):
        """Confirm restore"""
        self.do_restore = True
        self.accept()

    def should_restore(self) -> bool:
        """Returns True if user wants to restore"""
        return self.do_restore