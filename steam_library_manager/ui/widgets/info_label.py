#
# steam_library_manager/ui/widgets/info_label.py
# Label components for game details panel
#
# Copyright 2025 SwitchBros
# MIT License
#

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QGridLayout, QLabel

from steam_library_manager.ui.theme import Theme
from steam_library_manager.utils.i18n import t

__all__ = [
    "InfoLabel",
    "build_detail_grid",
    "set_info_label_value",
    "update_hltb_label",
    "format_proton_html",
    "format_deck_html",
]


class InfoLabel(QLabel):
    """Gray title + bold value label."""

    def __init__(self, tk, v=""):
        super().__init__()
        txt = t(tk)
        self.setText("<span style='color:%s;'>%s:</span> <b>%s</b>" % (Theme.TXT_MUTED, txt, v))
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setStyleSheet("padding: 1px 0;")


def build_detail_grid(title, keys, widths=None, space=30):
    # TODO: refactor this mess later
    w = QWidget()
    lay = QGridLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setHorizontalSpacing(space)
    lay.setVerticalSpacing(2)

    hdr = QLabel("<b>%s:</b>" % t(title))
    hdr.setStyleSheet("padding: 1px 0;")
    lay.addWidget(hdr, 0, 0)

    lbls = []
    for i, k in enumerate(keys):
        lbl = InfoLabel(k)
        lay.addWidget(lbl, 0, i + 1)
        lbls.append(lbl)

    if widths:
        for col, cw in widths.items():
            lay.setColumnMinimumWidth(col, cw)

    lay.setColumnStretch(len(keys) + 1, 1)
    return w, lay, lbls


def set_info_label_value(lbl, val, col=""):
    parts = lbl.text().split(":</span>")
    pfx = parts[0] + ":</span>" if len(parts) > 1 else ""
    if col:
        lbl.setText("%s <b style='color:%s;'>%s</b>" % (pfx, col, val))
    else:
        lbl.setText("%s <b>%s</b>" % (pfx, val))


def update_hltb_label(lbl, h, d):
    parts = lbl.text().split(":</span>")
    pfx = parts[0] + ":</span>" if len(parts) > 1 else ""
    v = t("time.time_hours_short", hours="%.1f" % h) if h > 0 else d
    lbl.setText("%s <b>%s</b>" % (pfx, v))


def _fmt(val, cols, prefix, title):
    k = val.lower() if val else "unknown"
    if k not in cols:
        k = "unknown"
    c = cols[k]
    disp = t("%s.%s" % (prefix, k))
    if disp.startswith("["):
        disp = k.title()
    ttl = t(title)
    return "<span style='color:%s;'>%s:</span> <span style='color:%s; font-weight:bold;'>%s</span>" % (
        Theme.TXT_MUTED,
        ttl,
        c,
        disp,
    )


def format_proton_html(tr):
    return _fmt(tr, Theme.PDB_COLORS, "ui.game_details.proton_tiers", "ui.game_details.proton_db")


def format_deck_html(st):
    return _fmt(st, Theme.DECK_COLORS, "ui.game_details.steam_deck_status", "ui.game_details.steam_deck")
