#
# steam_library_manager/ui/dialogs/about_dialog.py
# About dialog showing version, license, and contributor info
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#


from typing import NamedTuple

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
)

from steam_library_manager.config import config
from steam_library_manager.ui.utils.font_helper import FontHelper
from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.utils.i18n import get_language, t
from steam_library_manager.utils.open_url import open_url
from steam_library_manager.version import __app_name__, __version__, __release_date__, __author__, __license__

__all__ = ["AboutDialog"]

# Hardcoded project metadata (NOT i18n - intentional)
# These are curated by SwitchBros, not pulled from i18n files.

_GITHUB_URL = "https://github.com/Switch-Bros/SteamLibraryManager"


class AboutTexts(NamedTuple):
    """Curated About dialog texts - controlled by SwitchBros, not i18n."""

    description: str
    credits: str
    built_with: str


_ABOUT_EN = AboutTexts(
    description=(
        "The ultimate Steam library organizer for Linux.\n"
        "Manage thousands of games with smart collections,\n"
        "auto-categorization, and cloud sync."
    ),
    credits="Contributors will be listed here.",
    built_with="",  # set at runtime with emoji
)

_ABOUT_DE = AboutTexts(
    description=(
        "Der ultimative Steam-Bibliotheksmanager f\u00fcr Linux.\n"
        "Verwalte tausende Spiele mit smarten Kollektionen,\n"
        "Auto-Kategorisierung und Cloud-Sync."
    ),
    credits="Mitwirkende werden hier aufgef\u00fchrt.",
    built_with="",  # set at runtime with emoji
)


def _get_about_texts() -> AboutTexts:
    """Returns curated About texts - DE or EN (fallback)."""
    from steam_library_manager.utils.i18n import t

    # BVB 09 Dortmund colors - had to pick my club!
    hearts = "%s%s%s" % (t("emoji.yellow_heart"), t("emoji.black_heart"), t("emoji.yellow_heart"))

    base = _ABOUT_DE if get_language() == "de" else _ABOUT_EN
    prefix = "Erstellt mit" if get_language() == "de" else "Built with"
    return base._replace(built_with="%s Python, PyQt6 & %s" % (prefix, hearts))


# Colors
_BG_DARK = "#1b2838"
_TXT = "#c7d5e0"
_TXT_DIM = "#8f98a0"
_TXT_LINK = "#66c0f4"
_DIV = "#2a475e"
_BTN_BG = "#2a475e"
_BTN_BD = "#3d6c8e"


class _ClickableLabel(QLabel):
    """QLabel that emits clicked on mouse press."""

    clicked = pyqtSignal()

    def mousePressEvent(self, ev):
        self.clicked.emit()
        super().mousePressEvent(ev)


class AboutDialog(BaseDialog):
    """Two-column About dialog with dark Steam theme,
    showing version info, credits, and project links.
    """

    def __init__(self, parent=None):
        self._click_count = 0

        super().__init__(
            parent,
            title_text="%s - %s" % (t("menu.help.about"), __app_name__),
            min_width=650,
            show_title_label=False,
            buttons="none",
        )
        self.setFixedSize(650, 400)

    # -- UI --

    def _build_content(self, layout):
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(0)

        root = QHBoxLayout()
        root.setSpacing(0)

        # Left: logo
        root.addLayout(self._build_logo_col())

        # Vertical divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.VLine)
        div.setStyleSheet("color: %s;" % _DIV)
        div.setFixedWidth(1)
        root.addSpacing(20)
        root.addWidget(div)
        root.addSpacing(20)

        # Right: info
        root.addLayout(self._build_info_col(), stretch=1)

        layout.addLayout(root)

        # Global stylesheet
        self.setStyleSheet("""
            QDialog {
                background-color: %s;
            }
            QLabel {
                color: %s;
                background: transparent;
            }
            QPushButton {
                background-color: %s;
                color: %s;
                border: 1px solid %s;
                border-radius: 3px;
                padding: 8px 24px;
            }
            QPushButton:hover {
                background-color: %s;
            }
        """ % (_BG_DARK, _TXT, _BTN_BG, _TXT, _BTN_BD, _BTN_BD))

    def _build_logo_col(self):
        col = QVBoxLayout()
        col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_lbl = _ClickableLabel()
        logo_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        logo_lbl.setToolTip("SwitchBros")

        logo_path = config.RESOURCES_DIR / "images" / "default_icons.webp"
        if logo_path.exists():
            px = QPixmap(str(logo_path))
            logo_lbl.setPixmap(
                px.scaled(
                    200,
                    200,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            logo_lbl.setText(__app_name__)
            logo_lbl.setFont(FontHelper.get_font(16, FontHelper.BOLD))

        logo_lbl.clicked.connect(self._on_logo_clicked)
        col.addWidget(logo_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        return col

    def _build_info_col(self):
        col = QVBoxLayout()
        col.setSpacing(6)

        # App name
        name_lbl = QLabel(__app_name__)
        name_lbl.setFont(FontHelper.get_font(18, FontHelper.BOLD))
        name_lbl.setStyleSheet("color: white;")
        col.addWidget(name_lbl)

        # Version + release date
        ver_lbl = QLabel("Version %s  -  Release: %s" % (__version__, __release_date__))
        ver_lbl.setStyleSheet("color: %s; font-size: 12px;" % _TXT_DIM)
        col.addWidget(ver_lbl)

        col.addSpacing(8)

        # Description
        about = _get_about_texts()
        desc_lbl = QLabel(about.description)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("font-size: 13px;")
        col.addWidget(desc_lbl)

        col.addSpacing(4)
        col.addWidget(self._hline())

        # Credits
        cr_hdr = QLabel("Credits")
        cr_hdr.setFont(FontHelper.get_font(11, FontHelper.BOLD))
        col.addWidget(cr_hdr)

        cr_txt = QLabel(about.credits)
        cr_txt.setStyleSheet("color: %s; font-size: 12px;" % _TXT_DIM)
        cr_txt.setWordWrap(True)
        col.addWidget(cr_txt)

        col.addWidget(self._hline())

        # License + GitHub
        lic_lbl = QLabel("License: %s  |  Author: %s" % (__license__, __author__))
        lic_lbl.setStyleSheet("color: %s; font-size: 12px;" % _TXT_DIM)
        col.addWidget(lic_lbl)

        gh_lbl = QLabel('GitHub: <a href="%s" style="color: %s;">%s</a>' % (_GITHUB_URL, _TXT_LINK, _GITHUB_URL))
        gh_lbl.setTextFormat(Qt.TextFormat.RichText)
        gh_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        gh_lbl.linkActivated.connect(lambda url: open_url(url))
        gh_lbl.setStyleSheet("font-size: 12px;")
        col.addWidget(gh_lbl)

        col.addStretch()

        # Built-with tagline
        bw_lbl = QLabel(about.built_with)
        bw_lbl.setStyleSheet("color: %s; font-size: 11px;" % _TXT_DIM)
        bw_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        col.addWidget(bw_lbl)

        col.addSpacing(4)

        # Close button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton(t("common.close"))
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        col.addLayout(btn_row)

        return col

    # -- Helpers --

    @staticmethod
    def _hline():
        # Subtle horizontal separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: %s;" % _DIV)
        line.setFixedHeight(1)
        return line

    def _on_logo_clicked(self):
        self._click_count += 1

        if self._click_count == 3:
            open_url(_GITHUB_URL)

        elif self._click_count >= 5:
            from steam_library_manager.utils.enigma import load_easter_egg
            from steam_library_manager.ui.widgets.ui_helper import UIHelper

            egg = load_easter_egg("logo_tribute")
            if egg:
                UIHelper.show_info(
                    self,
                    egg.get("message", ""),
                    title=egg.get("title", ""),
                )
            self._click_count = 0
