"""Base class for all enrichment background threads.

Provides standard signals, cancellation, and the run() template.
Subclasses implement: _get_items(), _process_item(),
_format_progress(), and optionally _setup(), _cleanup(), _rate_limit().
"""

from __future__ import annotations

import logging
import time
from typing import Any

from PyQt6.QtCore import QThread, pyqtSignal

__all__ = ["BaseEnrichmentThread"]

logger = logging.getLogger("steamlibmgr.enrichment.base")


class BaseEnrichmentThread(QThread):
    """Template base class for enrichment threads.

    Signals:
        progress: Emitted before each item (message, current, total).
        finished_enrichment: Emitted when done (success_count, fail_count).
        error: Emitted on fatal error (error_message).
    """

    progress = pyqtSignal(str, int, int)
    finished_enrichment = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def __init__(self, parent: Any = None) -> None:
        """Initializes the base enrichment thread.

        Args:
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._cancelled: bool = False
        self._force_refresh: bool = False

    def cancel(self) -> None:
        """Request cancellation of the enrichment loop."""
        self._cancelled = True

    def run(self) -> None:
        """Template method: iterate items, call _process_item() for each."""
        self._cancelled = False
        try:
            self._setup()
            items = self._get_items()
        except Exception as exc:
            self.error.emit(str(exc))
            return

        total = len(items)
        success = 0
        failed = 0

        try:
            for i, item in enumerate(items):
                if self._cancelled:
                    break

                self.progress.emit(
                    self._format_progress(item, i + 1, total),
                    i + 1,
                    total,
                )

                try:
                    if self._process_item(item):
                        success += 1
                    else:
                        failed += 1
                except Exception as exc:
                    logger.warning("Enrichment failed for item %r: %s", item, exc)
                    failed += 1

                self._rate_limit()
        finally:
            self._cleanup()

        self.finished_enrichment.emit(success, failed)

    # ── Subclasses MUST override these ──────────────────

    def _get_items(self) -> list:
        """Return the list of items to process.

        Raises:
            NotImplementedError: Subclass must implement.
        """
        raise NotImplementedError

    def _process_item(self, item: Any) -> bool:
        """Process a single item.

        Args:
            item: The item from _get_items() to process.

        Returns:
            True on success, False on expected failure.

        Raises:
            NotImplementedError: Subclass must implement.
        """
        raise NotImplementedError

    def _format_progress(self, item: Any, current: int, total: int) -> str:
        """Format a progress message for the current item.

        Args:
            item: The current item being processed.
            current: 1-based index of the current item.
            total: Total number of items.

        Returns:
            Formatted progress string.

        Raises:
            NotImplementedError: Subclass must implement.
        """
        raise NotImplementedError

    # ── Subclasses MAY override these ────────────────────

    def _setup(self) -> None:
        """Initialize resources before the processing loop.

        Override to open database connections, API clients, etc.
        """

    def _cleanup(self) -> None:
        """Release resources after the processing loop.

        Override to close database connections, etc.
        Always called, even on cancellation.
        """

    def _rate_limit(self) -> None:
        """Sleep between items to respect rate limits. Override as needed."""
        time.sleep(1.0)
