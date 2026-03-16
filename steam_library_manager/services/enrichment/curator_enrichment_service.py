#
# steam_library_manager/services/enrichment/curator_enrichment_service.py
# Background thread for curator recommendation enrichment
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from steam_library_manager.services.enrichment.base_enrichment_thread import BaseEnrichmentThread
from steam_library_manager.utils.i18n import t

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
        """Configure the thread with curator list and database path."""
        self._curators = curators
        self._db_path = db_path
        self._force_refresh = force_refresh
        self._db: Any = None

    def _setup(self) -> None:
        """Opens database connection and creates curator client."""
        from steam_library_manager.core.db import Database
        from steam_library_manager.services.curator_client import CuratorClient

        self._db = Database(self._db_path)
        self._client = CuratorClient()

    def _cleanup(self) -> None:
        if self._db is not None:
            self._db.close()
            self._db = None

    def _get_items(self) -> list[dict[str, Any]]:
        return self._curators

    def _process_item(self, item: dict[str, Any]) -> bool:
        """Fetch and persist recommendations for one curator."""
        from steam_library_manager.services.curator_client import CuratorRecommendation

        curator_id = item["curator_id"]
        name = item["name"]
        url = item.get("url") or (f"https://store.steampowered.com/curator/{curator_id}/")

        try:
            all_recs = self._client.fetch_recommendations(url)

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
        name = item.get("name", "?")
        return t(
            "ui.enrichment.curator_progress",
            current=current,
            total=total,
            name=name,
        )

    def _rate_limit(self) -> None:
        time.sleep(2.0)
