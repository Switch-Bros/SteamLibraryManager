"""
Steam Running Warning Dialog.

This dialog is shown when the user tries to save changes while Steam is running.
Provides options to:
- Cancel the save operation
- Close Steam and save (kills Steam process)
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from src.utils.i18n import t
from src.config import config


class SteamRunningDialog(QDialog):
    """Warning dialog shown when Steam is running during save operation.
    
    Provides two options:
    - Cancel: Return to app without saving
    - Close Steam & Save: Kill Steam process and proceed with save
    
    Return codes:
        CANCELLED: User cancelled the operation
        CLOSE_AND_SAVE: User chose to close Steam and save
    """
    
    # Return codes
    CANCELLED = 0
    CLOSE_AND_SAVE = 1
    
    def __init__(self, parent=None):
        """Initialize the Steam running warning dialog.
        
        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the UI layout."""
        self.setWindowTitle(t('ui.steam_running.title'))
        self.setMinimumWidth(450)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Warning icon + message
        header_layout = QHBoxLayout()
        
        # Warning icon
        icon_label = QLabel("⚠️")
        icon_label.setStyleSheet("font-size: 48px;")
        header_layout.addWidget(icon_label)
        
        # Warning message
        message_layout = QVBoxLayout()
        message_layout.setSpacing(10)
        
        title = QLabel(t('ui.steam_running.warning_title'))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        message_layout.addWidget(title)
        
        explanation = QLabel(t('ui.steam_running.explanation'))
        explanation.setWordWrap(True)
        explanation.setStyleSheet("color: #888;")
        message_layout.addWidget(explanation)
        
        header_layout.addLayout(message_layout, 1)
        layout.addLayout(header_layout)
        
        # Info box
        info_box = QLabel(t('ui.steam_running.info'))
        info_box.setWordWrap(True)
        info_box.setStyleSheet("""
            QLabel {
                background-color: #2a475e;
                padding: 15px;
                border-radius: 5px;
                color: #c7d5e0;
            }
        """)
        layout.addWidget(info_box)
        
        # Buttons
        layout.addStretch()
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.btn_cancel = QPushButton(t('common.cancel'))
        self.btn_cancel.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.btn_cancel)
        
        self.btn_close_steam = QPushButton(t('ui.steam_running.close_and_save'))
        self.btn_close_steam.setDefault(True)
        self.btn_close_steam.setStyleSheet("""
            QPushButton {
                background-color: #c75450;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #d66460;
            }
        """)
        self.btn_close_steam.clicked.connect(self._on_close_steam)
        button_layout.addWidget(self.btn_close_steam)
        
        layout.addLayout(button_layout)
    
    def _on_cancel(self):
        """Handle cancel button click."""
        self.done(self.CANCELLED)
    
    def _on_close_steam(self):
        """Handle close Steam button click."""
        from src.core.steam_account_scanner import kill_steam_process
        
        # Confirm action
        reply = QMessageBox.question(
            self,
            t('ui.steam_running.confirm_title'),
            t('ui.steam_running.confirm_message'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Try to kill Steam
            success = kill_steam_process()
            
            if success:
                # Steam closed successfully
                QMessageBox.information(
                    self,
                    t('common.success'),
                    t('ui.steam_running.steam_closed')
                )
                self.done(self.CLOSE_AND_SAVE)
            else:
                # Failed to close Steam
                QMessageBox.critical(
                    self,
                    t('common.error'),
                    t('ui.steam_running.close_failed')
                )
