#
# steam_library_manager/ui/dialogs/enrich_all_progress_dialog.py
# Progress dialog for bulk enrichment of the entire library
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from steam_library_manager.services.enrichment.enrich_all_coordinator import (
    TRK_CURATOR,
    TRK_DECK,
    TRK_HLTB,
    TRK_PEGI,
    TRK_PDB,
    TRK_STEAM,
    TRK_TAGS,
    EnrichAllCoordinator,
)
from steam_library_manager.ui.utils.font_helper import FontHelper
from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

__all__ = ["EnrichAllProgressDialog"]

_TRACK_LABELS = [
    (TRK_TAGS, "ui.enrichment.enrich_all_tags"),
    (TRK_STEAM, "ui.enrichment.enrich_all_steam"),
    (TRK_HLTB, "ui.enrichment.enrich_all_hltb"),
    (TRK_PDB, "ui.enrichment.enrich_all_protondb"),
    (TRK_DECK, "ui.enrichment.enrich_all_deck"),
    (TRK_PEGI, "ui.enrichment.enrich_all_pegi"),
    (TRK_CURATOR, "ui.enrichment.enrich_all_curator"),
]


class EnrichAllProgressDialog(BaseDialog):
    """Multi-track progress dialog for full library data refresh."""

    def __init__(self, parent: QWidget | None = None):
        self._coord = None
        self._pb = {}  # progress bars
        self._st = {}  # status labels
        self._run = False
        super().__init__(
            parent,
            title_key="ui.enrichment.enrich_all_title",
            show_title_label=False,
            buttons="custom",
        )
        self.setMinimumWidth(500)
        self.setMinimumHeight(250)

    def _build_content(self, layout: QVBoxLayout):
        # title at top
        hdr = QLabel(t("ui.enrichment.enrich_all_title"))
        hdr.setFont(FontHelper.get_font(size=14, weight=FontHelper.BOLD))
        layout.addWidget(hdr)

        for tid, lkey in _TRACK_LABELS:
            row = QHBoxLayout()

            nm = QLabel(t(lkey))
            nm.setMinimumWidth(220)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            status = QLabel("")
            status.setMinimumWidth(24)

            row.addWidget(nm)
            row.addWidget(bar, 1)
            row.addWidget(status)
            layout.addLayout(row)

            self._pb[tid] = bar
            self._st[tid] = status

        # cancel button, right-aligned
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn = QPushButton(t("common.cancel"))
        self._btn.clicked.connect(self._cancel)
        btn_row.addWidget(self._btn)
        layout.addLayout(btn_row)

    def set_coordinator(self, coord: EnrichAllCoordinator):
        # wire up coordinator signals
        self._coord = coord
        coord.track_progress.connect(self._on_prog)
        coord.track_finished.connect(self._on_done)
        coord.all_finished.connect(self._on_all)

    def showEvent(self, ev):
        super().showEvent(ev)
        if self._coord and not self._run:
            self._run = True
            self._coord.start()

    def _on_prog(self, track, cur, tot):
        if track in self._pb and tot > 0:
            pct = int((cur / tot) * 100)
            self._pb[track].setValue(pct)

    def _on_done(self, track, ok, bad):
        if track not in self._pb:
            return

        bar = self._pb[track]
        st = self._st[track]

        if ok == -1:
            # skipped entirely
            bar.setValue(0)
            st.setText(t("emoji.dash"))
            st.setStyleSheet("color: gray;")
        elif bad < 0:
            # errored out
            bar.setValue(100)
            st.setText(t("emoji.cross"))
            st.setStyleSheet("color: red; font-weight: bold;")
        else:
            bar.setValue(100)
            st.setText(t("emoji.check_mark"))
            st.setStyleSheet("color: green; font-weight: bold;")

    def _on_all(self, res):
        self._run = False
        # only count tracks that actually enriched something
        total = sum(s for s, _ in res.values() if s > 0)
        UIHelper.show_info(
            self,
            t("ui.enrichment.enrich_all_complete", total=total),
        )
        self.accept()

    def _cancel(self):
        if self._coord:
            self._coord.cancel()
        self._btn.setEnabled(False)
        self._btn.setText(t("emoji.ellipsis"))

    def closeEvent(self, ev):
        # don't let user close mid-enrichment
        if self._run:
            self._cancel()
            ev.ignore()
        else:
            ev.accept()
