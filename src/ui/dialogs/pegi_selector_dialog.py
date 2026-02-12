"""
PEGI Rating Selector Dialog.

This dialog allows users to manually select a PEGI rating for a game
by clicking on one of the available PEGI icons.
"""
from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGridLayout, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon
from pathlib import Path
from src.utils.i18n import t

class PEGIIconButton(QPushButton):
    """A clickable button displaying a PEGI icon."""

    def __init__(self, rating: str, icon_path: Path, parent=None):
        super().__init__(parent)
        self.rating = rating
        self.setFixedSize(140, 140)
        self.setStyleSheet("""
            QPushButton {
                border: 2px solid #3d4450;
                background-color: #1b2838;
                border-radius: 4px;
            }
            QPushButton:hover {
                border: 2px solid #FDE100;
                background-color: #2a3f5f;
            }
            QPushButton:pressed {
                background-color: #1a2332;
            }
        """)

        # Load and display icon
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            scaled_pixmap = pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)
            self.setIcon(QIcon(scaled_pixmap))
            self.setIconSize(scaled_pixmap.size())
        else:
            self.setText(f"PEGI\n{rating}")

class PEGISelectorDialog(QDialog):
    """Dialog for selecting a PEGI rating."""

    rating_selected = pyqtSignal(str)  # Emits the selected rating (e.g., "18")

    def __init__(self, current_rating: str = "", parent=None):
        super().__init__(parent)
        self.current_rating = current_rating
        self.selected_rating = ""
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle(t('ui.pegi_selector.title'))
        self.setModal(True)
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Title
        title = QLabel(t('ui.pegi_selector.instruction'))
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #c7d5e0;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # PEGI icons grid
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(15)

        # Available PEGI ratings
        pegi_ratings = ['3', '7', '12', '16', '18']
        icons_dir = Path("resources/icons")

        row, col = 0, 0
        for rating in pegi_ratings:
            icon_path = icons_dir / f"PEGI{rating}.png"
            btn = PEGIIconButton(rating, icon_path, self)
            btn.clicked.connect(lambda checked, r=rating: self._on_rating_clicked(r))

            # Highlight current rating
            if rating == self.current_rating:
                btn.setStyleSheet(btn.styleSheet() + """
                    QPushButton {
                        border: 3px solid #FDE100;
                    }
                """)

            grid.addWidget(btn, row, col)
            col += 1
            if col >= 3:  # 3 columns
                col = 0
                row += 1

        layout.addWidget(grid_widget)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # Remove rating button
        self.btn_remove = QPushButton(t('ui.pegi_selector.remove'))
        self.btn_remove.setStyleSheet("""
            QPushButton {
                background-color: #c23030;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d04040;
            }
        """)
        self.btn_remove.clicked.connect(self._on_remove_clicked)
        button_layout.addWidget(self.btn_remove)

        # Cancel button
        self.btn_cancel = QPushButton(t('common.cancel'))
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #3d4450;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4d5460;
            }
        """)
        self.btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(self.btn_cancel)

        layout.addLayout(button_layout)

    def _on_rating_clicked(self, rating: str):
        """Handle rating button click."""
        self.selected_rating = rating
        self.rating_selected.emit(rating)
        self.accept()

    def _on_remove_clicked(self):
        """Handle remove rating button click."""
        self.selected_rating = ""  # Empty string means remove override
        self.rating_selected.emit("")
        self.accept()

    def get_selected_rating(self) -> str:
        """Returns the selected rating or empty string if removed."""
        return self.selected_rating
