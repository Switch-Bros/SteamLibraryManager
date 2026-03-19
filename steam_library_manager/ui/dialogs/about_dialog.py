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

# hardcoded metadata - NOT i18n (curated by SwitchBros)
_GITHUB_URL = "https://github.com/Switch-Bros/SteamLibraryManager"


class AboutTexts(NamedTuple):
    # curated texts - controlled by SwitchBros, not i18n files
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
    built_with="",  # set at runtime
)

_ABOUT_DE = AboutTexts(
    description=(
        "Der ultimative Steam-Bibliotheksmanager für Linux.\n"
        "Verwalte tausende Spiele mit smarten Kollektionen,\n"
        "Auto-Kategorisierung und Cloud-Sync."
    ),
    credits="Mitwirkende werden hier aufgeführt.",
    built_with="",  # set at runtime
)


def _get_texts():
    # returns curated About texts - DE or EN (fallback)
    # BVB 09 Dortmund colors - had to pick my club!
    hearts = "%s%s%s" % (t("emoji.yellow_heart"), t("emoji.black_heart"), t("emoji.yellow_heart"))

    base = _ABOUT_DE if get_language() == "de" else _ABOUT_EN
    prefix = "Erstellt mit" if get_language() == "de" else "Built with"
    return base._replace(built_with="%s Python, PyQt6 & %s" % (prefix, hearts))


# Colors - Steam dark theme
_BG = "#1b2838"
_TXT = "#c7d5e0"
_DIM = "#8f98a0"
_LINK = "#66c0f4"
_SEP = "#2a475e"
_BTN_BG = "#2a475e"
_BTN_BD = "#3d6c8e"


class _ClickableLabel(QLabel):
    # QLabel that emits clicked on mouse press
    clicked = pyqtSignal()

    def mousePressEvent(self, ev):
        self.clicked.emit()
        super().mousePressEvent(ev)


class AboutDialog(BaseDialog):
    """Two-column About dialog with dark Steam theme,
    showing version info, credits, and project links.

    Has a secret easter egg if you click the logo 5 times.
    """

    def __init__(self, parent=None):
        self._clicks = 0  # easter egg counter

        super().__init__(
            parent,
            title_text="%s - %s" % (t("menu.help.about"), __app_name__),
            min_width=650,
            show_title_label=False,
            buttons="none",
        )
        self.setFixedSize(650, 400)

    def _build_content(self, layout):
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(0)

        root = QHBoxLayout()
        root.setSpacing(0)

        # left: logo column
        root.addLayout(self._logo_col())

        # vertical divider
        div = QFrame()
        div.setFrameShape(QFrame.Shape.VLine)
        div.setStyleSheet("color: %s;" % _SEP)
        div.setFixedWidth(1)
        root.addSpacing(20)
        root.addWidget(div)
        root.addSpacing(20)

        # right: info column
        root.addLayout(self._info_col(), stretch=1)

        layout.addLayout(root)

        # global stylesheet
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
        """ % (_BG, _TXT, _BTN_BG, _TXT, _BTN_BD, _BTN_BD))

    def _logo_col(self):
        col = QVBoxLayout()
        col.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl = _ClickableLabel()
        lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        lbl.setToolTip("SwitchBros")

        logo_path = config.RESOURCES_DIR / "images" / "default_icons.webp"
        if logo_path.exists():
            px = QPixmap(str(logo_path))
            lbl.setPixmap(
                px.scaled(
                    200,
                    200,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            lbl.setText(__app_name__)
            lbl.setFont(FontHelper.get_font(16, FontHelper.BOLD))

        lbl.clicked.connect(self._logo_click)
        col.addWidget(lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        return col

    def _info_col(self):
        col = QVBoxLayout()
        col.setSpacing(6)

        # app name header
        name = QLabel(__app_name__)
        name.setFont(FontHelper.get_font(18, FontHelper.BOLD))
        name.setStyleSheet("color: white;")
        col.addWidget(name)

        # version + release date
        ver = QLabel("Version %s  -  Release: %s" % (__version__, __release_date__))
        ver.setStyleSheet("color: %s; font-size: 12px;" % _DIM)
        col.addWidget(ver)

        col.addSpacing(8)

        # description text
        about = _get_texts()
        desc = QLabel(about.description)
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 13px;")
        col.addWidget(desc)

        col.addSpacing(4)
        col.addWidget(self._hline())

        # credits section
        hdr = QLabel("Credits")
        hdr.setFont(FontHelper.get_font(11, FontHelper.BOLD))
        col.addWidget(hdr)

        txt = QLabel(about.credits)
        txt.setStyleSheet("color: %s; font-size: 12px;" % _DIM)
        txt.setWordWrap(True)
        col.addWidget(txt)

        col.addWidget(self._hline())

        # license & author
        lic = QLabel("License: %s  |  Author: %s" % (__license__, __author__))
        lic.setStyleSheet("color: %s; font-size: 12px;" % _DIM)
        col.addWidget(lic)

        # github link
        link = QLabel('GitHub: <a href="%s" style="color: %s;">%s</a>' % (_GITHUB_URL, _LINK, _GITHUB_URL))
        link.setTextFormat(Qt.TextFormat.RichText)
        link.setCursor(Qt.CursorShape.PointingHandCursor)
        link.linkActivated.connect(lambda url: open_url(url))
        link.setStyleSheet("font-size: 12px;")
        col.addWidget(link)

        col.addStretch()

        # built-with footer
        tag = QLabel(about.built_with)
        tag.setStyleSheet("color: %s; font-size: 11px;" % _DIM)
        tag.setAlignment(Qt.AlignmentFlag.AlignRight)
        col.addWidget(tag)

        col.addSpacing(4)

        # close button
        row = QHBoxLayout()
        row.addStretch()
        btn = QPushButton(t("common.close"))
        btn.setMinimumWidth(100)
        btn.clicked.connect(self.accept)
        row.addWidget(btn)
        col.addLayout(row)

        return col

    @staticmethod
    def _hline():
        # subtle horizontal separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: %s;" % _SEP)
        line.setFixedHeight(1)
        return line

    def _logo_click(self):
        self._clicks += 1

        if self._clicks == 3:
            open_url(_GITHUB_URL)

        elif self._clicks >= 5:
            # load easter egg
            from steam_library_manager.utils.enigma import load_easter_egg
            from steam_library_manager.ui.widgets.ui_helper import UIHelper

            egg = load_easter_egg("logo_tribute")
            if egg:
                UIHelper.show_info(
                    self,
                    egg.get("message", ""),
                    title=egg.get("title", ""),
                )
            self._clicks = 0
