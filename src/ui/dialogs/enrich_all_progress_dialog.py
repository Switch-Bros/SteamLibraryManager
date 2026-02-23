"""Progress dialog for the 'Refresh ALL Data' operation.

Displays five track rows with independent progress bars for
Tags, Steam API, HLTB, ProtonDB, and Deck status enrichment.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from src.services.enrichment.enrich_all_coordinator import (
    TRACK_DECK,
    TRACK_HLTB,
    TRACK_PEGI,
    TRACK_PROTONDB,
    TRACK_STEAM,
    TRACK_TAGS,
    EnrichAllCoordinator,
)
from src.ui.utils.font_helper import FontHelper
from src.ui.widgets.base_dialog import BaseDialog
from src.ui.widgets.ui_helper import UIHelper
from src.utils.i18n import t

if TYPE_CHECKING:
    from PyQt6.QtWidgets import QWidget

__all__ = ["EnrichAllProgressDialog"]

_TRACK_LABELS: list[tuple[str, str]] = [
    (TRACK_TAGS, "ui.enrichment.enrich_all_tags"),
    (TRACK_STEAM, "ui.enrichment.enrich_all_steam"),
    (TRACK_HLTB, "ui.enrichment.enrich_all_hltb"),
    (TRACK_PROTONDB, "ui.enrichment.enrich_all_protondb"),
    (TRACK_DECK, "ui.enrichment.enrich_all_deck"),
    (TRACK_PEGI, "ui.enrichment.enrich_all_pegi"),
]


class EnrichAllProgressDialog(BaseDialog):
    """Multi-track progress dialog for full data refresh.

    Shows five rows (one per enrichment track) with independent
    progress bars, status indicators, and a cancel button.

    Attributes:
        _coordinator: The EnrichAllCoordinator managing the tracks.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initializes the dialog.

        Args:
            parent: Parent widget.
        """
        self._coordinator: EnrichAllCoordinator | None = None
        self._track_bars: dict[str, QProgressBar] = {}
        self._track_status: dict[str, QLabel] = {}
        self._is_running: bool = False
        super().__init__(
            parent,
            title_key="ui.enrichment.enrich_all_title",
            show_title_label=False,
            buttons="custom",
        )
        self.setMinimumWidth(500)
        self.setMinimumHeight(250)

    def _build_content(self, layout: QVBoxLayout) -> None:
        """Builds the track rows and cancel button.

        Args:
            layout: The main vertical layout.
        """
        title_label = QLabel(t("ui.enrichment.enrich_all_title"))
        title_label.setFont(FontHelper.get_font(size=14, weight=FontHelper.BOLD))
        layout.addWidget(title_label)

        for track_id, label_key in _TRACK_LABELS:
            row = QHBoxLayout()
            label = QLabel(t(label_key))
            label.setMinimumWidth(220)
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            status = QLabel("")
            status.setMinimumWidth(24)
            row.addWidget(label)
            row.addWidget(bar, 1)
            row.addWidget(status)
            layout.addLayout(row)
            self._track_bars[track_id] = bar
            self._track_status[track_id] = status

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._cancel_btn = QPushButton(t("common.cancel"))
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_layout.addWidget(self._cancel_btn)
        layout.addLayout(btn_layout)

    def set_coordinator(self, coordinator: EnrichAllCoordinator) -> None:
        """Attaches the coordinator and connects signals.

        Args:
            coordinator: The configured EnrichAllCoordinator.
        """
        self._coordinator = coordinator
        coordinator.track_progress.connect(self._on_track_progress)
        coordinator.track_finished.connect(self._on_track_finished)
        coordinator.all_finished.connect(self._on_all_finished)

    def showEvent(self, event) -> None:
        """Starts the coordinator when the dialog becomes visible.

        Args:
            event: The show event.
        """
        super().showEvent(event)
        if self._coordinator and not self._is_running:
            self._is_running = True
            self._coordinator.start()

    def _on_track_progress(self, track: str, current: int, total: int) -> None:
        """Updates a track's progress bar.

        Args:
            track: Track identifier.
            current: Current progress count.
            total: Total items to process.
        """
        if track in self._track_bars and total > 0:
            percent = int((current / total) * 100)
            self._track_bars[track].setValue(percent)

    def _on_track_finished(self, track: str, success: int, failed: int) -> None:
        """Marks a track as complete with status indicator.

        Args:
            track: Track identifier.
            success: Successful items (-1 = skipped).
            failed: Failed items (-1 = error).
        """
        if track not in self._track_bars:
            return

        bar = self._track_bars[track]
        status = self._track_status[track]

        if success == -1:
            bar.setValue(0)
            status.setText(t("emoji.em_dash"))
            status.setStyleSheet("color: gray;")
        elif failed < 0:
            bar.setValue(100)
            status.setText(t("emoji.cross"))
            status.setStyleSheet("color: red; font-weight: bold;")
        else:
            bar.setValue(100)
            status.setText(t("emoji.check_mark"))
            status.setStyleSheet("color: green; font-weight: bold;")

    def _on_all_finished(self, results: dict[str, tuple[int, int]]) -> None:
        """Shows completion summary and closes the dialog.

        Args:
            results: Dict mapping track names to (success, failed) tuples.
        """
        self._is_running = False
        total = sum(s for s, _ in results.values() if s > 0)
        UIHelper.show_info(
            self,
            t("ui.enrichment.enrich_all_complete", total=total),
        )
        self.accept()

    def _on_cancel(self) -> None:
        """Handles the cancel button click."""
        if self._coordinator:
            self._coordinator.cancel()
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.setText(t("emoji.ellipsis"))

    def closeEvent(self, event) -> None:
        """Prevents closing while enrichment is running.

        Args:
            event: The close event.
        """
        if self._is_running:
            self._on_cancel()
            event.ignore()
        else:
            event.accept()
