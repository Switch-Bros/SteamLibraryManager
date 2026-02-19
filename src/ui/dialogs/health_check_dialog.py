"""Dialog for displaying library health check results.

Shows a tabbed view with store availability, missing data,
and cache freshness information from the health check report.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.ui.widgets.base_dialog import BaseDialog
from src.utils.i18n import t

if TYPE_CHECKING:
    from src.services.library_health_service import HealthReport

__all__ = ["HealthCheckResultDialog"]

# Status emoji mapping
_STATUS_ICONS: dict[str, str] = {
    "available": "\U0001f7e2",  # green circle
    "age_gate": "\U0001f7e1",  # yellow circle
    "geo_locked": "\U0001f7e1",  # yellow circle
    "delisted": "\U0001f534",  # red circle
    "removed": "\U0001f534",  # red circle
    "unknown": "\u26aa",  # white circle
}


class HealthCheckResultDialog(BaseDialog):
    """Dialog showing library health check results in tabs.

    Tabs:
        1. Store Availability — delisted, geo-locked, removed games.
        2. Missing Data — incomplete metadata, missing artwork.
        3. Cache Status — stale HLTB, ProtonDB caches.
    """

    def __init__(self, parent: QWidget | None, report: HealthReport) -> None:
        """Initializes the health check result dialog.

        Args:
            parent: Parent widget.
            report: HealthReport dataclass with all check results.
        """
        self._report = report
        super().__init__(
            parent,
            title_key="health_check.result.title",
            min_width=800,
            buttons="close",
        )
        self.setMinimumHeight(500)

    def _build_content(self, layout: QVBoxLayout) -> None:
        """Builds the tabbed result view.

        Args:
            layout: The main vertical layout from BaseDialog.
        """
        issues = self._report.count_total_issues()

        if issues == 0:
            no_issues = QLabel(t("health_check.result.no_issues"))
            no_issues.setWordWrap(True)
            layout.addWidget(no_issues)
            return

        summary = QLabel(
            t(
                "health_check.result.summary",
                total=self._report.total_games,
                issues=issues,
            )
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        tabs = QTabWidget()

        store_tab = self._build_store_tab()
        tabs.addTab(store_tab, t("health_check.tabs.store"))

        data_tab = self._build_data_tab()
        tabs.addTab(data_tab, t("health_check.tabs.data"))

        cache_tab = self._build_cache_tab()
        tabs.addTab(cache_tab, t("health_check.tabs.cache"))

        layout.addWidget(tabs)

    def _build_store_tab(self) -> QWidget:
        """Builds the store availability tab with a table of problem games.

        Returns:
            Widget containing the store results table.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        results = self._report.store_unavailable
        if not results:
            label = QLabel(t("health_check.result.no_issues"))
            layout.addWidget(label)
            return widget

        table = QTableWidget(len(results), 4)
        table.setHorizontalHeaderLabels(["App ID", "Name", "Status", "Details"])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        header = table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        for row, result in enumerate(results):
            table.setItem(row, 0, QTableWidgetItem(str(result.app_id)))
            table.setItem(row, 1, QTableWidgetItem(result.name))

            icon = _STATUS_ICONS.get(result.status, "\u26aa")
            status_text = t(f"health_check.store_status.{result.status}")
            status_item = QTableWidgetItem(f"{icon} {status_text}")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(row, 2, status_item)

            table.setItem(row, 3, QTableWidgetItem(result.details))

        layout.addWidget(table)
        return widget

    def _build_data_tab(self) -> QWidget:
        """Builds the missing data tab with summary statistics.

        Returns:
            Widget containing data completeness information.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(
            QLabel(
                t(
                    "health_check.data_status.missing_metadata",
                    count=len(self._report.missing_metadata),
                )
            )
        )
        layout.addWidget(
            QLabel(
                t(
                    "health_check.data_status.missing_artwork",
                    count=len(self._report.missing_artwork),
                )
            )
        )
        layout.addWidget(
            QLabel(
                t(
                    "health_check.data_status.ghost_apps",
                    count=len(self._report.ghost_apps),
                )
            )
        )
        layout.addStretch()
        return widget

    def _build_cache_tab(self) -> QWidget:
        """Builds the cache freshness tab with stale cache counts.

        Returns:
            Widget containing cache status information.
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(
            QLabel(
                t(
                    "health_check.cache_status.stale_hltb",
                    count=self._report.stale_hltb,
                )
            )
        )
        layout.addWidget(
            QLabel(
                t(
                    "health_check.cache_status.stale_protondb",
                    count=self._report.stale_protondb,
                )
            )
        )
        layout.addStretch()
        return widget
