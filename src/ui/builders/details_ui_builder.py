# src/ui/builders/details_ui_builder.py

"""Builder for the game details panel UI.

Constructs all visual components (header, gallery, metadata grid,
HLTB row, achievement row, categories) and wires signals to the widget.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
    QPushButton,
    QLineEdit,
    QWidget,
    QScrollArea,
    QGroupBox,
)

from src.ui.theme import Theme
from src.ui.utils.font_helper import FontHelper
from src.ui.widgets.category_list import HorizontalCategoryList
from src.ui.widgets.clickable_image import ClickableImage
from src.ui.widgets.info_label import InfoLabel, build_detail_grid
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.ui.widgets.game_details_widget import GameDetailsWidget

__all__ = ["build_details_ui"]


def build_details_ui(w: GameDetailsWidget) -> None:
    """Creates all UI components on the GameDetailsWidget.

    Sets widget attributes (name_label, img_grid, lbl_proton, etc.) and
    connects signals to the widget's event handler methods.

    Args:
        w: The GameDetailsWidget instance to populate.
    """
    main_layout = QVBoxLayout(w)
    main_layout.setContentsMargins(15, 5, 15, 0)
    main_layout.setSpacing(0)

    # === HEADER (Title & Buttons) ===
    _build_header(w, main_layout)

    # === PRIVATE BADGE (next to name) ===
    w.lbl_private_badge = QLabel()
    w.lbl_private_badge.setTextFormat(Qt.TextFormat.RichText)
    w.lbl_private_badge.setStyleSheet(
        f"color: {Theme.TEXT_MUTED}; background: #3a2020; " "border-radius: 3px; padding: 2px 6px; font-size: 11px;"
    )
    w.lbl_private_badge.hide()
    main_layout.addWidget(w.lbl_private_badge)

    # === DESCRIPTION ===
    _build_description(w, main_layout)

    main_layout.addSpacing(10)

    line1 = QFrame()
    line1.setFrameShape(QFrame.Shape.HLine)
    line1.setFrameShadow(QFrame.Shadow.Sunken)
    main_layout.addWidget(line1)

    # === METADATA GRID ===
    _build_metadata_grid(w, main_layout)

    # === HLTB GRID ===
    _build_hltb_grid(w, main_layout)

    # === ACHIEVEMENT GRID ===
    _build_achievement_grid(w, main_layout)

    # === DLC SECTION ===
    _build_dlc_section(w, main_layout)

    line2 = QFrame()
    line2.setFrameShape(QFrame.Shape.HLine)
    line2.setFrameShadow(QFrame.Shadow.Sunken)
    line2.setContentsMargins(0, 0, 0, 0)
    main_layout.addWidget(line2)

    # === CATEGORIES ===
    cat_header = QLabel(t("ui.game_details.categories_label"))
    cat_header.setFont(FontHelper.get_font(10, FontHelper.BOLD))
    cat_header.setStyleSheet("padding-top: 5px; padding-bottom: 5px;")
    main_layout.addWidget(cat_header)

    w.category_list = HorizontalCategoryList()
    w.category_list.category_toggled.connect(w._on_category_toggle)
    main_layout.addWidget(w.category_list)


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def _build_description(w: GameDetailsWidget, main_layout: QVBoxLayout) -> None:
    """Builds the description section (max 3 lines, word-wrapped)."""
    w.lbl_description = QLabel()
    w.lbl_description.setWordWrap(True)
    w.lbl_description.setMaximumHeight(60)
    w.lbl_description.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 12px; padding: 4px 0;")
    w.lbl_description.setTextFormat(Qt.TextFormat.PlainText)
    w.lbl_description.hide()
    main_layout.addWidget(w.lbl_description)


def _build_dlc_section(w: GameDetailsWidget, main_layout: QVBoxLayout) -> None:
    """Builds the DLC section (group box with scrollable label list)."""
    w.dlc_group = QGroupBox(t("ui.detail.dlc_label"))
    w.dlc_group.setMaximumHeight(100)
    w.dlc_group.setStyleSheet("QGroupBox { font-weight: bold; padding-top: 14px; margin-top: 4px; }")

    dlc_layout = QVBoxLayout(w.dlc_group)
    dlc_layout.setContentsMargins(4, 4, 4, 4)
    dlc_layout.setSpacing(0)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("QScrollArea { border: none; }")

    w.dlc_content = QLabel()
    w.dlc_content.setWordWrap(True)
    w.dlc_content.setTextFormat(Qt.TextFormat.PlainText)
    w.dlc_content.setStyleSheet(f"color: {Theme.TEXT_MUTED}; font-size: 11px;")
    scroll.setWidget(w.dlc_content)

    dlc_layout.addWidget(scroll)
    w.dlc_group.hide()
    main_layout.addWidget(w.dlc_group)


def _build_header(w: GameDetailsWidget, main_layout: QVBoxLayout) -> None:
    """Builds the header section: name, PEGI image, buttons, gallery."""
    header_layout = QHBoxLayout()

    left_container = QVBoxLayout()
    w.name_label = QLabel(t("ui.game_details.select_placeholder"))
    w.name_label.setFont(FontHelper.get_font(22, FontHelper.BOLD))
    w.name_label.setWordWrap(True)
    w.name_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
    left_container.addWidget(w.name_label)
    left_container.addStretch()

    # PEGI Rating Box
    w.pegi_image = ClickableImage(w, 128, 128)
    w.pegi_image.set_default_image("resources/images/default_icons.png")
    w.pegi_image.clicked.connect(w._on_pegi_clicked)
    w.pegi_image.right_clicked.connect(w._on_pegi_right_click)
    w.pegi_image.setStyleSheet(f"border: 1px solid {Theme.PEGI_HOVER}; background-color: {Theme.BG_PRIMARY};")

    pegi_layout = QHBoxLayout()
    pegi_layout.addWidget(w.pegi_image)
    pegi_layout.addStretch()

    # Buttons
    button_layout = QVBoxLayout()
    button_layout.setSpacing(8)
    button_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

    w.btn_edit = QPushButton(t("ui.game_details.btn_edit"))
    w.btn_edit.clicked.connect(w._on_edit)
    w.btn_edit.setMinimumWidth(120)

    w.btn_store = QPushButton(t("ui.game_details.btn_store"))
    w.btn_store.clicked.connect(w._open_current_store)
    w.btn_store.setMinimumWidth(120)

    button_layout.addWidget(w.btn_edit)
    button_layout.addWidget(w.btn_store)

    buttons_pegi_layout = QVBoxLayout()
    buttons_pegi_layout.setSpacing(12)
    buttons_pegi_layout.addLayout(pegi_layout)
    buttons_pegi_layout.addLayout(button_layout)
    buttons_pegi_layout.addStretch()

    left_container.addLayout(buttons_pegi_layout)
    header_layout.addLayout(left_container, stretch=1)

    # Gallery
    _build_gallery(w, header_layout)

    main_layout.addLayout(header_layout)


def _build_gallery(w: GameDetailsWidget, header_layout: QHBoxLayout) -> None:
    """Builds the image gallery block (grid, hero, logo, icon)."""
    gallery_widget = QWidget()
    gallery_widget.setFixedSize(592, 356)
    gallery_widget.setStyleSheet("background-color: #1a1a1a; border-radius: 4px;")

    gallery_layout = QHBoxLayout(gallery_widget)
    gallery_layout.setContentsMargins(4, 4, 4, 4)
    gallery_layout.setSpacing(4)

    # Grid (Cover)
    w.img_grid = ClickableImage(w, 232, 348)
    w.img_grid.set_default_image("resources/images/default_grids.png")
    w.img_grid.clicked.connect(lambda: w._on_image_click("grids"))
    w.img_grid.right_clicked.connect(lambda: w._on_image_right_click("grids"))
    gallery_layout.addWidget(w.img_grid)

    # Right stack
    right_stack = QVBoxLayout()
    right_stack.setContentsMargins(0, 0, 0, 0)
    right_stack.setSpacing(4)

    # Logo + Icon
    top_row = QHBoxLayout()
    top_row.setContentsMargins(0, 0, 0, 0)
    top_row.setSpacing(4)

    w.img_logo = ClickableImage(w, 264, 184)
    w.img_logo.set_default_image("resources/images/default_logos.png")
    w.img_logo.clicked.connect(lambda: w._on_image_click("logos"))
    w.img_logo.right_clicked.connect(lambda: w._on_image_right_click("logos"))
    w.img_logo.setStyleSheet("background: transparent;")
    top_row.addWidget(w.img_logo)

    w.img_icon = ClickableImage(w, 80, 80)
    w.img_icon.set_default_image("resources/images/default_icons.png")
    w.img_icon.clicked.connect(lambda: w._on_image_click("icons"))
    w.img_icon.right_clicked.connect(lambda: w._on_image_right_click("icons"))
    w.img_icon.setStyleSheet("background: transparent;")

    icon_container = QVBoxLayout()
    icon_container.setContentsMargins(0, 0, 0, 0)
    icon_container.addWidget(w.img_icon)
    icon_container.addStretch()
    top_row.addLayout(icon_container)

    right_stack.addLayout(top_row)

    # Hero
    w.img_hero = ClickableImage(w, 348, 160)
    w.img_hero.set_default_image("resources/images/default_heroes.png")
    w.img_hero.clicked.connect(lambda: w._on_image_click("heroes"))
    w.img_hero.right_clicked.connect(lambda: w._on_image_right_click("heroes"))
    right_stack.addWidget(w.img_hero)

    gallery_layout.addLayout(right_stack)

    header_layout.addWidget(
        gallery_widget,
        alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
    )


def _build_metadata_grid(w: GameDetailsWidget, main_layout: QVBoxLayout) -> None:
    """Builds the metadata grid (basic info, ratings, developer/publisher)."""
    meta_widget = QWidget()
    meta_grid = QGridLayout(meta_widget)
    meta_grid.setContentsMargins(0, 5, 0, 5)
    meta_grid.setHorizontalSpacing(30)
    meta_grid.setVerticalSpacing(2)
    meta_grid.setColumnMinimumWidth(0, 180)
    meta_grid.setColumnMinimumWidth(1, 240)
    meta_grid.setColumnMinimumWidth(2, 420)
    meta_grid.setColumnStretch(3, 1)

    # Column 0: Basic Info
    meta_grid.addWidget(QLabel(f"<b>{t('ui.game_details.section_basic')}</b>"), 0, 0)
    w.lbl_appid = InfoLabel("ui.game_details.app_id")
    meta_grid.addWidget(w.lbl_appid, 1, 0)
    w.lbl_playtime = InfoLabel("ui.game_details.playtime")
    meta_grid.addWidget(w.lbl_playtime, 2, 0)
    w.lbl_updated = InfoLabel("ui.game_details.last_update", t("emoji.dash"))
    meta_grid.addWidget(w.lbl_updated, 3, 0)

    # Column 1: Ratings
    meta_grid.addWidget(QLabel(f"<b>{t('ui.game_details.section_ratings')}</b>"), 0, 1)
    w.lbl_proton = QLabel()
    w.lbl_proton.setTextFormat(Qt.TextFormat.RichText)
    w.lbl_proton.setStyleSheet("padding: 1px 0;")
    meta_grid.addWidget(w.lbl_proton, 1, 1)
    w.lbl_steam_deck = QLabel()
    w.lbl_steam_deck.setTextFormat(Qt.TextFormat.RichText)
    w.lbl_steam_deck.setStyleSheet("padding: 1px 0;")
    meta_grid.addWidget(w.lbl_steam_deck, 2, 1)
    w.lbl_reviews = InfoLabel("ui.game_details.reviews", t("emoji.dash"))
    meta_grid.addWidget(w.lbl_reviews, 3, 1)

    # Column 2: Metadata fields
    meta_grid.addWidget(QLabel(f"<b>{t('ui.game_details.section_metadata')}</b>"), 0, 2)
    w.edit_dev = _add_meta_field(meta_grid, "ui.game_details.developer", 1)
    w.edit_pub = _add_meta_field(meta_grid, "ui.game_details.publisher", 2)
    w.edit_rel = _add_meta_field(meta_grid, "ui.game_details.release_year", 3)

    main_layout.addWidget(meta_widget)


def _add_meta_field(grid: QGridLayout, label_key: str, row: int) -> QLineEdit:
    """Adds a label + read-only QLineEdit row to a metadata grid.

    Args:
        grid: The target grid layout.
        label_key: i18n key for the field label.
        row: Grid row index.

    Returns:
        The created QLineEdit widget.
    """
    layout = QHBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    lbl = QLabel(t(label_key) + ":")
    lbl.setStyleSheet("padding: 1px 0;")
    layout.addWidget(lbl)
    edit = QLineEdit()
    edit.setReadOnly(True)
    edit.setStyleSheet("background: transparent; border: none; font-weight: bold; padding: 1px 0;")
    layout.addWidget(edit)
    grid.addLayout(layout, row, 2)
    return edit


def _build_hltb_grid(w: GameDetailsWidget, main_layout: QVBoxLayout) -> None:
    """Builds the HLTB detail row as an independent QGridLayout."""
    hltb_widget, _hltb_grid, hltb_labels = build_detail_grid(
        title_key="ui.game_details.hltb",
        label_keys=[
            "ui.game_details.hltb_main",
            "ui.game_details.hltb_main_extras",
            "ui.game_details.hltb_completionist",
            "ui.game_details.hltb_all_styles",
        ],
        col_widths={0: 180, 1: 120, 2: 140, 3: 140, 4: 120},
    )
    w.lbl_hltb_main = hltb_labels[0]
    w.lbl_hltb_extras = hltb_labels[1]
    w.lbl_hltb_comp = hltb_labels[2]
    w.lbl_hltb_all = hltb_labels[3]
    main_layout.addWidget(hltb_widget)


def _build_achievement_grid(w: GameDetailsWidget, main_layout: QVBoxLayout) -> None:
    """Builds the Achievement detail row as an independent QGridLayout."""
    ach_widget, ach_grid, ach_labels = build_detail_grid(
        title_key="ui.game_details.achievements",
        label_keys=[
            "ui.game_details.achievement_total_label",
            "ui.game_details.achievement_progress",
        ],
        col_widths={0: 180, 1: 120, 2: 200},
    )
    w.lbl_achievement_total = ach_labels[0]
    w.lbl_achievement_progress = ach_labels[1]

    w.lbl_achievement_perfect = QLabel()
    w.lbl_achievement_perfect.setTextFormat(Qt.TextFormat.RichText)
    w.lbl_achievement_perfect.setStyleSheet("padding: 1px 0;")
    ach_grid.addWidget(w.lbl_achievement_perfect, 0, 3)

    main_layout.addWidget(ach_widget)
