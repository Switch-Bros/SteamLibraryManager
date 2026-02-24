"""Background thread for curator recommendation enrichment.

Fetches recommendations for all configured curators and persists
them to the database. Unlike other enrichment threads that iterate
games (3000+), this iterates curators (5-20).
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from src.services.enrichment.base_enrichment_thread import BaseEnrichmentThread
from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.curator_enrichment")

__all__ = ["CuratorEnrichmentThread"]


class CuratorEnrichmentThread(BaseEnrichmentThread):
    """Fetches recommendations for all configured curators.

    Each curator may have paginated results (50-2000 recommendations).
    Progress: "Curator 3/8: PCGamer"
    """

    def configure(
        self,
        curators: list[dict[str, Any]],
        db_path: Path,
        force_refresh: bool = False,
    ) -> None:
        """Configures the thread with curator list and database path.

        Args:
            curators: List of curator dicts from DB.
            db_path: Path to SQLite database.
            force_refresh: If True, refresh all curators regardless of age.
        """
        self._curators = curators
        self._db_path = db_path
        self._force_refresh = force_refresh
        self._db: Any = None

    def _setup(self) -> None:
        """Opens database connection and creates curator client."""
        from src.core.db import Database
        from src.services.curator_client import CuratorClient

        self._db = Database(self._db_path)
        self._client = CuratorClient()

    def _cleanup(self) -> None:
        """Closes database connection."""
        if self._db is not None:
            self._db.close()
            self._db = None

    def _get_items(self) -> list[dict[str, Any]]:
        """Returns curators to process.

        Returns:
            List of curator dicts.
        """
        return self._curators

    def _process_item(self, item: dict[str, Any]) -> bool:
        """Fetches and persists recommendations for one curator.

        Args:
            item: Curator dict with keys: curator_id, name, url.

        Returns:
            True on success, False on failure.
        """
        from src.services.curator_client import CuratorRecommendation

        curator_id = item["curator_id"]
        name = item["name"]
        url = item.get("url") or (f"https://store.steampowered.com/curator/{curator_id}/")

        try:
            all_recs = self._client.fetch_recommendations(url)

            # Filter: only "Recommended" (design decision)
            recommended_ids = [
                app_id for app_id, rec_type in all_recs.items() if rec_type == CuratorRecommendation.RECOMMENDED
            ]

            self._db.save_curator_recommendations(curator_id, recommended_ids)

            logger.info(
                t(
                    "logs.curator.fetch_success",
                    name=name,
                    count=len(recommended_ids),
                )
            )
            return True

        except (ConnectionError, ValueError, OSError) as exc:
            logger.warning(t("logs.curator.fetch_failed", name=name, error=str(exc)))
            return False

    def _format_progress(self, item: Any, current: int, total: int) -> str:
        """Formats a progress message for the current curator.

        Args:
            item: The curator dict being processed.
            current: 1-based index.
            total: Total curators.

        Returns:
            Formatted progress string.
        """
        name = item.get("name", "?")
        return t(
            "ui.enrichment.curator_progress",
            current=current,
            total=total,
            name=name,
        )

    def _rate_limit(self) -> None:
        """Sleeps between curators to respect Steam rate limits."""
        time.sleep(2.0)
