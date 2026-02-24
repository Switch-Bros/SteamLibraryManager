"""PEGI Rating Selector Dialog.

This dialog allows users to manually select a PEGI rating for a game
by clicking on one of the available PEGI icons.
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout, QWidget

from src.ui.theme import Theme
from src.ui.widgets.base_dialog import BaseDialog
from src.utils.i18n import t


class PEGIIconButton(QPushButton):
    """A clickable button displaying a PEGI icon."""

    def __init__(self, rating: str, icon_path: Path, parent=None):
        """Initializes a PEGI icon button.

        Args:
            rating: The PEGI rating value (e.g. "3", "18").
            icon_path: Path to the PEGI icon image.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.rating = rating
        self.setFixedSize(140, 140)
        self.setStyleSheet(Theme.pegi_button())

        # Load and display icon
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            scaled_pixmap = pixmap.scaled(
                120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            self.setIcon(QIcon(scaled_pixmap))
            self.setIconSize(scaled_pixmap.size())
        else:
            self.setText(f"PEGI\n{rating}")


class PEGISelectorDialog(BaseDialog):
    """Dialog for selecting a PEGI rating."""

    rating_selected = pyqtSignal(str)  # Emits the selected rating (e.g., "18")

    def __init__(self, current_rating: str = "", parent=None):
        """Initializes the PEGI selector dialog.

        Args:
            current_rating: Currently assigned PEGI rating (highlighted in UI).
            parent: Parent widget.
        """
        self.current_rating = current_rating
        self.selected_rating = ""

        super().__init__(
            parent,
            title_key="ui.pegi_selector.title",
            min_width=500,
            show_title_label=False,
            buttons="custom",
        )

    def _build_content(self, layout: QVBoxLayout) -> None:
        """Builds the PEGI rating selection grid and buttons."""
        layout.setSpacing(20)

        # Instruction
        title = QLabel(t("ui.pegi_selector.instruction"))
        title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {Theme.TEXT_PRIMARY};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # PEGI icons grid
        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(15)

        pegi_ratings = ["3", "7", "12", "16", "18"]
        icons_dir = Path("resources/icons")

        row, col = 0, 0
        for rating in pegi_ratings:
            icon_path = icons_dir / f"PEGI{rating}.png"
            btn = PEGIIconButton(rating, icon_path, self)
            btn.clicked.connect(lambda _checked=False, r=rating: self._on_rating_clicked(r))

            # Highlight current rating
            if rating == self.current_rating:
                btn.setStyleSheet(btn.styleSheet() + f"""
                    QPushButton {{
                        border: 3px solid {Theme.PEGI_HOVER};
                    }}
                """)

            grid.addWidget(btn, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1

        layout.addWidget(grid_widget)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.btn_remove = QPushButton(t("ui.pegi_selector.remove"))
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

        self.btn_cancel = QPushButton(t("common.cancel"))
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
        self.selected_rating = ""
        self.rating_selected.emit("")
        self.accept()

    def get_selected_rating(self) -> str:
        """Returns the selected rating or empty string if removed."""
        return self.selected_rating
