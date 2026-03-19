#
# steam_library_manager/ui/builders/details_ui_builder.py
# Builds the game details panel UI components
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
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

from steam_library_manager.config import config
from steam_library_manager.ui.theme import Theme
from steam_library_manager.ui.utils.font_helper import FontHelper
from steam_library_manager.ui.widgets.category_list import HorizontalCategoryList
from steam_library_manager.ui.widgets.clickable_image import ClickableImage
from steam_library_manager.ui.widgets.info_label import InfoLabel, build_detail_grid
from steam_library_manager.utils.i18n import t

if TYPE_CHECKING:
    from steam_library_manager.ui.widgets.game_details_widget import GameDetailsWidget

__all__ = ["build_details_ui", "rescale_ui", "_calc_scale", "_detect_initial_scale"]

# responsive scaling
_FULL_SCALE = 1000  # panels >= this get scale 1.0
_SCALE_REF = 1700  # higher = more aggressive downscale

# design sizes at scale=1.0
_IMG_GRID = (232, 348)
_IMG_LOGO = (264, 184)
_IMG_ICON = (80, 80)
_IMG_HERO = (348, 160)
_IMG_PEGI = (128, 128)

_META_COLS = (190, 320, 440)  # min widths per column

_log = logging.getLogger("steamlibmgr.details_ui")


def _detect_initial_scale():
    # pick starting scale from primary monitor size
    from PyQt6.QtWidgets import QApplication

    scr = QApplication.primaryScreen()
    if scr:
        sz = scr.availableSize()
        long_edge = max(sz.width(), sz.height())
        _log.info("Screen detected: %dx%d (long_edge=%d)" % (sz.width(), sz.height(), long_edge))
        if long_edge <= 1280:
            return 0.55
        if long_edge <= 1600:
            return 0.75
    return 1.0


def _calc_scale(panel_width):
    # uniform scale factor from panel width
    if panel_width >= _FULL_SCALE:
        return 1.0
    return max(0.5, panel_width / _SCALE_REF)


def _scaled(sz, scale):
    return (round(sz[0] * scale), round(sz[1] * scale))


def rescale_ui(w: GameDetailsWidget, scale):
    # rescale all size-dependent widgets
    _log.info("Rescaling UI: scale=%.3f" % scale)

    # each image widget + its design-time dimensions
    img_pairs = [
        (w.img_grid, _IMG_GRID),
        (w.img_logo, _IMG_LOGO),
        (w.img_icon, _IMG_ICON),
        (w.img_hero, _IMG_HERO),
        (w.pegi_image, _IMG_PEGI),
    ]
    for img, design_sz in img_pairs:
        nw, nh = _scaled(design_sz, scale)
        img.setFixedSize(nw, nh)
        img.w = nw
        img.h = nh
        img.image_label.setGeometry(0, 0, nw, nh)
        if img._badges:
            img._badges.setFixedWidth(nw)
        # re-apply: try cache first, then default fallback
        if img.current_path and img.current_path in img._px_cache:
            img._apply_px(img._px_cache[img.current_path])
        elif hasattr(img, "default_image") and img.default_image:
            img._load_local(img.default_image)

    # gallery container
    if hasattr(w, "_gallery_widget"):
        cw, ch = _scaled(_IMG_GRID, scale)
        lw, lh = _scaled(_IMG_LOGO, scale)
        iw, _ = _scaled(_IMG_ICON, scale)
        _, hh = _scaled(_IMG_HERO, scale)
        sp = max(2, round(4 * scale))
        margin = sp
        right_w = lw + sp + iw
        right_h = lh + sp + hh
        gw = margin + cw + sp + right_w + margin
        gh = margin + max(ch, right_h) + margin
        w._gallery_widget.setFixedSize(gw, gh)

    # metadata grid column widths
    if hasattr(w, "_meta_grid"):
        for col, base_w in enumerate(_META_COLS):
            w._meta_grid.setColumnMinimumWidth(col, round(base_w * scale))


def build_details_ui(w: GameDetailsWidget):
    # main entry point - wires up every widget
    scale = _detect_initial_scale()
    w._ui_scale = scale
    _log.info("Building details UI at scale=%.3f" % scale)

    root = QVBoxLayout(w)
    root.setContentsMargins(15, 5, 15, 0)
    root.setSpacing(0)

    _build_header(w, root, scale)

    # private badge sits below the title
    w.lbl_private_badge = QLabel()
    w.lbl_private_badge.setTextFormat(Qt.TextFormat.RichText)
    w.lbl_private_badge.setStyleSheet(
        "color: %s; background: #3a2020; " "border-radius: 3px; padding: 2px 6px; font-size: 11px;" % Theme.TXT_MUTED
    )
    w.lbl_private_badge.hide()
    root.addWidget(w.lbl_private_badge)

    _build_description(w, root)
    root.addSpacing(10)

    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setFrameShadow(QFrame.Shadow.Sunken)
    root.addWidget(sep)

    _build_metadata_grid(w, root, scale)
    _build_hltb_grid(w, root)
    _build_achievement_grid(w, root)
    _build_dlc_section(w, root)

    sep2 = QFrame()
    sep2.setFrameShape(QFrame.Shape.HLine)
    sep2.setFrameShadow(QFrame.Shadow.Sunken)
    sep2.setContentsMargins(0, 0, 0, 0)
    root.addWidget(sep2)

    # categories
    cat_hdr = QLabel(t("ui.game_details.categories_label"))
    cat_hdr.setFont(FontHelper.get_font(10, FontHelper.BOLD))
    cat_hdr.setStyleSheet("padding-top: 5px; padding-bottom: 5px;")
    root.addWidget(cat_hdr)

    w.category_list = HorizontalCategoryList()
    w.category_list.category_toggled.connect(w.on_category_toggle)
    root.addWidget(w.category_list)


# -- section builders --


def _build_description(w, layout):
    # 3-line word-wrapped description, hidden until populated
    w.lbl_description = QLabel()
    w.lbl_description.setWordWrap(True)
    w.lbl_description.setMaximumHeight(60)
    w.lbl_description.setStyleSheet("color: %s; font-size: 12px; padding: 4px 0;" % Theme.TXT_MUTED)
    w.lbl_description.setTextFormat(Qt.TextFormat.PlainText)
    w.lbl_description.hide()
    layout.addWidget(w.lbl_description)


def _build_dlc_section(w, layout):
    # scrollable DLC list, collapsed by default
    w.dlc_group = QGroupBox(t("ui.detail.dlc_label"))
    w.dlc_group.setMaximumHeight(100)
    w.dlc_group.setStyleSheet("QGroupBox { font-weight: bold; padding-top: 14px; margin-top: 4px; }")

    dlc_lay = QVBoxLayout(w.dlc_group)
    dlc_lay.setContentsMargins(4, 4, 4, 4)
    dlc_lay.setSpacing(0)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet("QScrollArea { border: none; }")

    w.dlc_content = QLabel()
    w.dlc_content.setWordWrap(True)
    w.dlc_content.setTextFormat(Qt.TextFormat.PlainText)
    w.dlc_content.setStyleSheet("color: %s; font-size: 11px;" % Theme.TXT_MUTED)
    scroll.setWidget(w.dlc_content)

    dlc_lay.addWidget(scroll)
    w.dlc_group.hide()
    layout.addWidget(w.dlc_group)


def _build_header(w, layout, scale):
    # title row + pegi + buttons + gallery
    hdr = QHBoxLayout()

    left = QVBoxLayout()
    w.name_label = QLabel(t("ui.game_details.select_placeholder"))
    w.name_label.setFont(FontHelper.get_font(22, FontHelper.BOLD))
    w.name_label.setWordWrap(True)
    w.name_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
    left.addWidget(w.name_label)
    left.addStretch()

    # pegi rating - always square
    pw, ph = _scaled(_IMG_PEGI, scale)
    w.pegi_image = ClickableImage(w, pw, ph)
    w.pegi_image.set_default_image(str(config.RESOURCES_DIR / "images" / "default_icons.webp"))
    w.pegi_image.clicked.connect(w.on_pegi_clicked)
    w.pegi_image.right_clicked.connect(w.on_pegi_right_click)
    w.pegi_image.setStyleSheet("border: 1px solid %s; background-color: %s;" % (Theme.PEGI_HVR, Theme.BG_PRI))

    pegi_row = QHBoxLayout()
    pegi_row.addWidget(w.pegi_image)
    pegi_row.addStretch()

    btn_col = QVBoxLayout()
    btn_col.setSpacing(8)
    btn_col.setAlignment(Qt.AlignmentFlag.AlignLeft)

    w.btn_edit = QPushButton(t("ui.game_details.btn_edit"))
    w.btn_edit.clicked.connect(w.on_edit)
    w.btn_edit.setMinimumWidth(120)

    w.btn_store = QPushButton(t("ui.game_details.btn_store"))
    w.btn_store.clicked.connect(w.open_current_store)
    w.btn_store.setMinimumWidth(120)

    btn_col.addWidget(w.btn_edit)
    btn_col.addWidget(w.btn_store)

    right_side = QVBoxLayout()
    right_side.setSpacing(12)
    right_side.addLayout(pegi_row)
    right_side.addLayout(btn_col)
    right_side.addStretch()

    left.addLayout(right_side)
    hdr.addLayout(left, stretch=1)

    _build_gallery(w, hdr, scale)
    layout.addLayout(hdr)


def _build_gallery(w, hdr_layout, scale):
    # image gallery block: cover, logo, icon, hero
    cw, ch = _scaled(_IMG_GRID, scale)
    lw, lh = _scaled(_IMG_LOGO, scale)
    iw, ih = _scaled(_IMG_ICON, scale)
    hw, hh = _scaled(_IMG_HERO, scale)

    sp = max(2, round(4 * scale))
    margin = max(2, round(4 * scale))

    # total gallery dimensions from content
    rw = lw + sp + iw
    rh = lh + sp + hh
    gal_w = margin + cw + sp + rw + margin
    gal_h = margin + max(ch, rh) + margin

    gal = QWidget()
    gal.setFixedSize(gal_w, gal_h)
    w._gallery_widget = gal
    gal.setStyleSheet("background-color: #1a1a1a; border-radius: 4px;")

    gal_lay = QHBoxLayout(gal)
    gal_lay.setContentsMargins(margin, margin, margin, margin)
    gal_lay.setSpacing(sp)

    # cover (2:3 aspect)
    w.img_grid = ClickableImage(w, cw, ch)
    w.img_grid.set_default_image(str(config.RESOURCES_DIR / "images" / "default_grids.webp"))
    w.img_grid.clicked.connect(lambda: w.on_image_click("grids"))
    w.img_grid.right_clicked.connect(lambda: w.on_image_right_click("grids"))
    gal_lay.addWidget(w.img_grid)

    right_stack = QVBoxLayout()
    right_stack.setContentsMargins(0, 0, 0, 0)
    right_stack.setSpacing(sp)

    top = QHBoxLayout()
    top.setContentsMargins(0, 0, 0, 0)
    top.setSpacing(sp)

    w.img_logo = ClickableImage(w, lw, lh)
    w.img_logo.set_default_image(str(config.RESOURCES_DIR / "images" / "default_logos.webp"))
    w.img_logo.clicked.connect(lambda: w.on_image_click("logos"))
    w.img_logo.right_clicked.connect(lambda: w.on_image_right_click("logos"))
    w.img_logo.setStyleSheet("background: transparent;")
    top.addWidget(w.img_logo)

    w.img_icon = ClickableImage(w, iw, ih)
    w.img_icon.set_default_image(str(config.RESOURCES_DIR / "images" / "default_icons.webp"))
    w.img_icon.clicked.connect(lambda: w.on_image_click("icons"))
    w.img_icon.right_clicked.connect(lambda: w.on_image_right_click("icons"))
    w.img_icon.setStyleSheet("background: transparent;")

    icon_box = QVBoxLayout()
    icon_box.setContentsMargins(0, 0, 0, 0)
    icon_box.addWidget(w.img_icon)
    icon_box.addStretch()
    top.addLayout(icon_box)

    right_stack.addLayout(top)

    # hero banner
    w.img_hero = ClickableImage(w, hw, hh)
    w.img_hero.set_default_image(str(config.RESOURCES_DIR / "images" / "default_heroes.webp"))
    w.img_hero.clicked.connect(lambda: w.on_image_click("heroes"))
    w.img_hero.right_clicked.connect(lambda: w.on_image_right_click("heroes"))
    right_stack.addWidget(w.img_hero)

    gal_lay.addLayout(right_stack)

    hdr_layout.addWidget(
        gal,
        alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
    )


def _build_metadata_grid(w, layout, scale):
    # 3-column grid: basic info | ratings | metadata fields
    meta_w = QWidget()
    grid = QGridLayout(meta_w)
    w._meta_grid = grid
    grid.setContentsMargins(0, 5, 0, 5)
    grid.setHorizontalSpacing(20)
    grid.setVerticalSpacing(2)

    for col, base in enumerate(_META_COLS):
        grid.setColumnMinimumWidth(col, round(base * scale))
    grid.setColumnStretch(2, 1)

    # col 0 - basics
    grid.addWidget(QLabel("<b>%s</b>" % t("ui.game_details.section_basic")), 0, 0)
    w.lbl_appid = InfoLabel("ui.game_details.app_id")
    grid.addWidget(w.lbl_appid, 1, 0)
    w.lbl_playtime = InfoLabel("ui.game_details.playtime")
    grid.addWidget(w.lbl_playtime, 2, 0)
    w.lbl_updated = InfoLabel("ui.game_details.last_update", t("emoji.dash"))
    grid.addWidget(w.lbl_updated, 3, 0)

    # col 1 - ratings
    grid.addWidget(QLabel("<b>%s</b>" % t("ui.game_details.section_ratings")), 0, 1)

    w.lbl_proton = QLabel()
    w.lbl_proton.setTextFormat(Qt.TextFormat.RichText)
    w.lbl_proton.setStyleSheet("padding: 1px 0;")
    grid.addWidget(w.lbl_proton, 1, 1)

    w.lbl_steam_deck = QLabel()
    w.lbl_steam_deck.setTextFormat(Qt.TextFormat.RichText)
    w.lbl_steam_deck.setStyleSheet("padding: 1px 0;")
    grid.addWidget(w.lbl_steam_deck, 2, 1)

    w.lbl_reviews = InfoLabel("ui.game_details.reviews", t("emoji.dash"))
    grid.addWidget(w.lbl_reviews, 3, 1)
    w.lbl_curator_overlap = InfoLabel("ui.game_details.curator_overlap", t("emoji.dash"))
    grid.addWidget(w.lbl_curator_overlap, 4, 1)

    # col 2 - dev/pub/year
    grid.addWidget(QLabel("<b>%s</b>" % t("ui.game_details.section_metadata")), 0, 2)
    w.edit_dev = _add_meta_field(grid, "ui.game_details.developer", 1)
    w.edit_pub = _add_meta_field(grid, "ui.game_details.publisher", 2)
    w.edit_rel = _add_meta_field(grid, "ui.game_details.release_year", 3)

    layout.addWidget(meta_w)


def _add_meta_field(grid, label_key, row):
    # label + readonly line-edit pair
    lay = QHBoxLayout()
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(2)
    lbl = QLabel("%s:" % t(label_key))
    lbl.setStyleSheet("padding: 1px 0;")
    lay.addWidget(lbl)
    ed = QLineEdit()
    ed.setReadOnly(True)
    ed.setStyleSheet("background: transparent; border: none; font-weight: bold; padding: 1px 0;")
    lay.addWidget(ed)
    grid.addLayout(lay, row, 2)
    return ed


def _build_hltb_grid(w, layout):
    # HLTB times row
    hltb_w, _hltb_grid, labels = build_detail_grid(
        title_key="ui.game_details.hltb",
        label_keys=[
            "ui.game_details.hltb_main",
            "ui.game_details.hltb_main_extras",
            "ui.game_details.hltb_completionist",
            "ui.game_details.hltb_all_styles",
        ],
        col_widths={0: 180, 1: 120, 2: 140, 3: 140, 4: 120},
    )
    w.lbl_hltb_main = labels[0]
    w.lbl_hltb_extras = labels[1]
    w.lbl_hltb_comp = labels[2]
    w.lbl_hltb_all = labels[3]
    layout.addWidget(hltb_w)


def _build_achievement_grid(w, layout):
    # achievement stats + perfect game badge
    ach_w, ach_grid, labels = build_detail_grid(
        title_key="ui.game_details.achievements",
        label_keys=[
            "ui.game_details.achievement_total_label",
            "ui.game_details.achievement_progress",
        ],
        col_widths={0: 180, 1: 152, 2: 200},
    )
    w.lbl_achievement_total = labels[0]
    w.lbl_achievement_progress = labels[1]

    w.lbl_achievement_perfect = QLabel()
    w.lbl_achievement_perfect.setTextFormat(Qt.TextFormat.RichText)
    w.lbl_achievement_perfect.setStyleSheet("padding: 1px 0;")
    ach_grid.addWidget(w.lbl_achievement_perfect, 0, 3)

    layout.addWidget(ach_w)
