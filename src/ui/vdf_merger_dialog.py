# src/ui/vdf_merger_dialog.py

"""
Dialog for merging Steam VDF configuration files.

Allows users to transfer game categories between Windows (sharedconfig.vdf)
and Linux (localconfig.vdf) with various merge strategies.
"""
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QComboBox, QCheckBox, QGroupBox, QTextEdit,
    QProgressBar, QMessageBox
)
from PyQt6.QtCore import QThread, pyqtSignal

from src.config import config
from src.ui.components.ui_helper import UIHelper
from src.utils.i18n import t
from src.utils.steam_config_merger import SteamConfigMerger, MergeStrategy


class MergeWorker(QThread):
    """Background thread for merge operations."""
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(bool, str, list)

    def __init__(self, merger: SteamConfigMerger, source: Path, target: Path,
                 strategy: MergeStrategy, backup: bool, dry_run: bool):
        super().__init__()
        self.merger = merger
        self.source = source
        self.target = target
        self.strategy = strategy
        self.backup = backup
        self.dry_run = dry_run

    def run(self):
        success, message, changes = self.merger.merge_tags(
            source_path=self.source,
            target_path=self.target,
            strategy=self.strategy,
            create_backup=self.backup,
            dry_run=self.dry_run,
            progress_callback=lambda cur, total, app: self.progress.emit(cur, total, app)
        )
        self.finished.emit(success, message, changes)


class VdfMergerDialog(QDialog):
    """Dialog for merging Steam VDF configuration files."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t('ui.vdf_merger.title'))
        self.setMinimumWidth(550)
        self.setMinimumHeight(500)

        self.source_path: Optional[Path] = None
        self.target_path: Optional[Path] = None
        self.worker: Optional[MergeWorker] = None

        self._setup_ui()
        self._set_default_target()

    def _setup_ui(self):
        """Creates the dialog UI."""
        layout = QVBoxLayout(self)

        # Info Label
        info_label = QLabel(t('ui.vdf_merger.info'))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Source File Group
        source_group = QGroupBox(t('ui.vdf_merger.source_group'))
        # noinspection DuplicatedCode
        source_layout = QHBoxLayout(source_group)
        self.source_label = QLabel(t('ui.vdf_merger.no_file_selected'))
        self.source_label.setStyleSheet("color: gray;")
        source_layout.addWidget(self.source_label, 1)
        source_btn = QPushButton(t('ui.vdf_merger.browse'))
        source_btn.clicked.connect(self._browse_source)
        source_layout.addWidget(source_btn)
        layout.addWidget(source_group)

        # Target File Group
        target_group = QGroupBox(t('ui.vdf_merger.target_group'))
        # noinspection DuplicatedCode
        target_layout = QHBoxLayout(target_group)
        self.target_label = QLabel(t('ui.vdf_merger.no_file_selected'))
        self.target_label.setStyleSheet("color: gray;")
        target_layout.addWidget(self.target_label, 1)
        target_btn = QPushButton(t('ui.vdf_merger.browse'))
        target_btn.clicked.connect(self._browse_target)
        target_layout.addWidget(target_btn)
        layout.addWidget(target_group)

        # Options Group
        options_group = QGroupBox(t('ui.vdf_merger.options_group'))
        options_layout = QVBoxLayout(options_group)

        # Strategy
        strategy_layout = QHBoxLayout()
        strategy_layout.addWidget(QLabel(t('ui.vdf_merger.strategy_label')))
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItem(t('ui.vdf_merger.strategy_overwrite'), MergeStrategy.OVERWRITE)
        self.strategy_combo.addItem(t('ui.vdf_merger.strategy_merge'), MergeStrategy.MERGE)
        self.strategy_combo.addItem(t('ui.vdf_merger.strategy_skip'), MergeStrategy.SKIP_EXISTING)
        strategy_layout.addWidget(self.strategy_combo, 1)
        options_layout.addLayout(strategy_layout)

        # Checkboxes
        self.backup_check = QCheckBox(t('ui.vdf_merger.create_backup'))
        self.backup_check.setChecked(True)
        options_layout.addWidget(self.backup_check)

        self.dry_run_check = QCheckBox(t('ui.vdf_merger.dry_run'))
        self.dry_run_check.setToolTip(t('ui.vdf_merger.dry_run_tooltip'))
        options_layout.addWidget(self.dry_run_check)

        layout.addWidget(options_group)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Results
        results_group = QGroupBox(t('ui.vdf_merger.results_group'))
        results_layout = QVBoxLayout(results_group)
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(150)
        self.results_text.setPlaceholderText(t('ui.vdf_merger.results_placeholder'))
        results_layout.addWidget(self.results_text)
        layout.addWidget(results_group)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.merge_btn = QPushButton(t('ui.vdf_merger.btn_merge'))
        self.merge_btn.clicked.connect(self._start_merge)
        self.merge_btn.setEnabled(False)
        btn_layout.addWidget(self.merge_btn)

        close_btn = QPushButton(t('common.close'))
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _set_default_target(self):
        """Sets the default target to the current localconfig.vdf."""
        if config.STEAM_PATH:
            short_id, _ = config.get_detected_user()
            if short_id:
                default_target = config.STEAM_PATH / 'userdata' / short_id / 'config' / 'localconfig.vdf'
                if default_target.exists():
                    self.target_path = default_target
                    self.target_label.setText(str(default_target))
                    self.target_label.setStyleSheet("")
                    self._update_merge_button()

    def _browse_source(self):
        """Opens file dialog for source file selection."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t('ui.vdf_merger.select_source'),
            str(Path.home()),
            "VDF Files (*.vdf);;All Files (*)"
        )
        if file_path:
            self.source_path = Path(file_path)
            self.source_label.setText(file_path)
            self.source_label.setStyleSheet("")
            self._update_merge_button()

    def _browse_target(self):
        """Opens file dialog for target file selection."""
        start_dir = str(config.STEAM_PATH) if config.STEAM_PATH else str(Path.home())
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t('ui.vdf_merger.select_target'),
            start_dir,
            "VDF Files (*.vdf);;All Files (*)"
        )
        if file_path:
            self.target_path = Path(file_path)
            self.target_label.setText(file_path)
            self.target_label.setStyleSheet("")
            self._update_merge_button()

    def _update_merge_button(self):
        """Enables merge button when both files are selected."""
        self.merge_btn.setEnabled(self.source_path is not None and self.target_path is not None)

    def _start_merge(self):
        """Starts the merge operation."""
        if not self.source_path or not self.target_path:
            return

        # Confirm if not dry-run (localised buttons via UIHelper)
        if not self.dry_run_check.isChecked():
            if not UIHelper.confirm(self,
                                    t('ui.vdf_merger.confirm_message'),
                                    t('ui.vdf_merger.confirm_title')):
                return

        self.results_text.clear()
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.merge_btn.setEnabled(False)

        strategy = self.strategy_combo.currentData()
        merger = SteamConfigMerger()

        self.worker = MergeWorker(
            merger=merger,
            source=self.source_path,
            target=self.target_path,
            strategy=strategy,
            backup=self.backup_check.isChecked(),
            dry_run=self.dry_run_check.isChecked()
        )
        # noinspection PyUnresolvedReferences
        self.worker.progress.connect(self._on_progress)
        # noinspection PyUnresolvedReferences
        self.worker.finished.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, current: int, total: int, app_id: str):
        """Updates progress bar."""
        # noinspection PyUnusedLocal
        _ = app_id  # Unused but required by signal signature
        if total > 0:
            self.progress_bar.setMaximum(total)
            self.progress_bar.setValue(current)

    def _on_finished(self, success: bool, message: str, changes: list):
        """Handles merge completion."""
        self.progress_bar.setVisible(False)
        self.merge_btn.setEnabled(True)

        # Show results — status prefix and bullet via i18n
        status_prefix: str = t('emoji.success') if success else t('emoji.error')
        result_text = f"{status_prefix} {message}\n"
        if changes:
            bullet: str = t('emoji.bullet')
            result_text += f"\n{t('ui.vdf_merger.changes_header')}:\n"
            for change in changes[:50]:  # Limit display
                result_text += f"  {bullet} {change}\n"
            if len(changes) > 50:
                result_text += f"  ... {t('ui.vdf_merger.more_changes', count=len(changes) - 50)}\n"

        self.results_text.setText(result_text)

        # Show message box
        if success:
            QMessageBox.information(self, t('common.success'), message)
        else:
            QMessageBox.warning(self, t('common.error'), message)
