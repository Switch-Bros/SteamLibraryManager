#
# steam_library_manager/ui/widgets/image_badge_overlay.py
# Overlay widget that renders icon badges on top of game artwork
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from typing import cast

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from steam_library_manager.config import config
from steam_library_manager.utils.i18n import t

__all__ = ["ImageBadgeOverlay"]

_STRIPE_H = 5
_ICON_H = 28
_GAP = 2
_EXPANDED_H = _STRIPE_H + _GAP + _ICON_H
_STRIPE_W = 28
_STRIPE_GAP = 2


class ImageBadgeOverlay(QWidget):
    """Animated badge overlay for image covers.
    Shows colored stripe hints that expand into icons on hover.

    FIXME: hardcoded sizes everywhere, should be responsive
    """

    def __init__(self, parent, width):
        super().__init__(parent)
        self._w = width
        self.badges = []
        self._colors = []

        # 6px above the image top edge
        self.setGeometry(0, -6, width, _EXPANDED_H)
        self.raise_()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(5, 0, 0, 0)
        lay.setSpacing(_GAP)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        # stripe row -- always visible (thin colored bars)
        self._stripe_box = QWidget()
        sl = QHBoxLayout(self._stripe_box)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(_STRIPE_GAP)
        sl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._stripe_box.setFixedHeight(_STRIPE_H)
        lay.addWidget(self._stripe_box)

        # icon row -- only visible on hover
        self._icon_box = QWidget()
        il = QHBoxLayout(self._icon_box)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(_STRIPE_GAP)
        il.setAlignment(Qt.AlignmentFlag.AlignLeft)
        lay.addWidget(self._icon_box)

        # animation for expand/collapse
        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setDuration(180)

    def create_badges(self, meta, animated=False):
        # build badges from game metadata
        self.clear_badges()
        if not meta:
            return

        tags = meta.get("tags", [])

        # badge defs: (key, text, color, active)
        defs = [
            (
                "nsfw",
                "%s %s" % (t("emoji.nsfw"), t("ui.badges.nsfw")),
                "#d9534f",
                bool(meta.get("nsfw") or "nsfw" in tags),
            ),
            (
                "humor",
                "%s %s" % (t("emoji.humor"), t("ui.badges.humor")),
                "#f0ad4e",
                bool(meta.get("humor") or "humor" in tags),
            ),
            (
                "epilepsy",
                "%s %s" % (t("emoji.blitz"), t("ui.badges.epilepsy")),
                "#0275d8",
                bool(meta.get("epilepsy") or "epilepsy" in tags),
            ),
            ("animated", "%s %s" % (t("emoji.animated"), t("ui.badges.animated")), "#5cb85c", animated),
        ]

        act = [(k, txt, c) for k, txt, c, on in defs if on]

        if not act:
            self.setGeometry(0, 0, self._w, 0)
            return

        s_lay = cast(QHBoxLayout, self._stripe_box.layout())
        i_lay = cast(QHBoxLayout, self._icon_box.layout())

        for key, txt, bg in act:
            # stripe (always visible)
            st = QWidget()
            st.setFixedSize(_STRIPE_W, _STRIPE_H)
            st.setStyleSheet("background-color: %s;" % bg)
            s_lay.addWidget(st)

            # icon (visible on hover)
            ip = config.ICONS_DIR / ("flag_%s.png" % key)
            if ip.exists():
                lbl = QLabel()
                px = QPixmap(str(ip)).scaledToHeight(_ICON_H, Qt.TransformationMode.SmoothTransformation)
                lbl.setPixmap(px)
                lbl.setFixedWidth(_STRIPE_W)
                lbl.setStyleSheet(
                    "QLabel { "
                    "  border: 1px solid rgba(0, 0, 0, 0.45); "
                    "  border-radius: 0px 0px 3px 3px; "
                    "  background-color: rgba(0, 0, 0, 0.25); "
                    "  padding: 1px; "
                    "}"
                )
            else:
                # fallback: text badge when no PNG
                lbl = QLabel(txt)
                lbl.setFixedSize(_STRIPE_W, _ICON_H)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet(
                    "background-color: %s; color: white; "
                    "border-radius: 0px 0px 4px 4px; "
                    "font-weight: bold; font-size: 9px; "
                    "border: 1px solid rgba(255,255,255,0.3);" % bg
                )
            i_lay.addWidget(lbl)

            self._colors.append(bg)
            self.badges.append(lbl)

        # start collapsed -- only stripes visible
        self.setGeometry(0, 0, self._w, _STRIPE_H)

    def clear_badges(self):
        # remove all badges and hide
        il = cast(QHBoxLayout, self._icon_box.layout())
        for b in self.badges:
            il.removeWidget(b)
            b.deleteLater()
        self.badges = []

        sl = cast(QHBoxLayout, self._stripe_box.layout())
        while sl.count():
            item = sl.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._colors = []
        self.setGeometry(0, 0, self._w, 0)

    def expand(self):
        # show full icons
        if self.badges:
            self._go(_EXPANDED_H)

    def collapse(self):
        # show only stripes
        if self.badges:
            self._go(_STRIPE_H)

    def _go(self, h):
        # animate to target height
        self._anim.stop()
        cur = self.geometry()
        self._anim.setStartValue(cur)
        self._anim.setEndValue(QRect(0, 0, self._w, h))
        self._anim.start()
