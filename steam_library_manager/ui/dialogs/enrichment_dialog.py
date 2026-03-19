#
# steam_library_manager/ui/dialogs/enrichment_dialog.py
# Dialog for per-game enrichment selection and execution
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
)
from steam_library_manager.ui.utils.font_helper import FontHelper
from steam_library_manager.ui.widgets.base_dialog import BaseDialog
from steam_library_manager.ui.widgets.ui_helper import UIHelper
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.timeouts import THREAD_WAIT_MS

__all__ = ["EnrichmentDialog"]


class EnrichmentDialog(BaseDialog):
    """Progress dialog for background enrichment jobs.
    Shows progress bar, status text, and a cancel button.

    TODO: unify with other progress dialogs, too much duplication
    """

    def __init__(self, title, parent=None):
        self._hdr = title
        self._thr = None
        self.force_refresh = False  # public flag
        super().__init__(
            parent,
            title_key="ui.enrichment.dialog_title",
            show_title_label=False,
            buttons="custom",
        )
        self.setMinimumHeight(150)

    def _build_content(self, lyt):
        # header
        lbl = QLabel(self._hdr)
        lbl.setFont(FontHelper.get_font(size=14, weight=FontHelper.BOLD))
        lyt.addWidget(lbl)

        # progress
        self._pb = QProgressBar()
        self._pb.setRange(0, 100)
        self._pb.setValue(0)
        lyt.addWidget(self._pb)

        # status text
        self._status = QLabel("")
        lyt.addWidget(self._status)

        # cancel button
        row = QHBoxLayout()
        row.addStretch()
        self._btn = QPushButton(t("common.cancel"))
        self._btn.clicked.connect(self._cancel)
        row.addWidget(self._btn)
        lyt.addLayout(row)

    def start_thread(self, thr):
        # attach worker thread; auto-starts in showEvent
        self._thr = thr
        thr.progress.connect(self._upd)
        thr.finished_enrichment.connect(self._done)
        thr.error.connect(self._err)

    def showEvent(self, ev):
        super().showEvent(ev)
        if self._thr and not self._thr.isRunning():
            self._thr.start()

    def _upd(self, txt, cur, tot):
        if tot > 0:
            pct = int((cur / tot) * 100)
            self._pb.setValue(pct)
        self._status.setText(txt)

    def _done(self, ok, bad):
        self._clean()
        self.force_refresh = UIHelper.show_batch_result(
            self,
            t("ui.enrichment.complete", success=ok, failed=bad),
            t("ui.enrichment.complete_title"),
        )
        self.accept()

    def _err(self, msg):
        self._clean()
        UIHelper.show_warning(self, msg)
        self.reject()

    def _cancel(self):
        if self._thr:
            self._thr.cancel()
        self._btn.setEnabled(False)
        self._btn.setText(t("emoji.ellipsis"))

    def _clean(self):
        # cleanup thread
        if self._thr and self._thr.isRunning():
            self._thr.quit()
            self._thr.wait(THREAD_WAIT_MS)
        self._thr = None

    def closeEvent(self, ev):
        # block close while running
        if self._thr and self._thr.isRunning():
            self._cancel()
            ev.ignore()
        else:
            ev.accept()
