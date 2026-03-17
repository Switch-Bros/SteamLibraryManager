#
# steam_library_manager/services/library_health_service.py
# Data models for library health checks
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["LibraryHealthService", "HealthReport", "StoreCheckResult"]


@dataclass(frozen=True)
class StoreCheckResult:
    """Result of checking one game against the Steam Store.

    Tells if a game is still available, age-gated, geo-locked, delisted or just gone.
    LibraryHealthThread fills these in by hitting the store API and falling back to HTTP status codes.
    """

    app_id: int
    name: str
    status: str
    details: str


@dataclass
class HealthReport:
    """Full library health report - store availability, missing artwork, stale caches, ghost apps.
    Populated by LibraryHealthThread > displayed in the health check dialog with three tabs.
    """

    store_unavailable: list[StoreCheckResult] = field(default_factory=list)
    missing_artwork: list[tuple[int, str]] = field(default_factory=list)
    missing_metadata: list[tuple[int, str]] = field(default_factory=list)
    ghost_apps: list[tuple[int, str]] = field(default_factory=list)
    stale_hltb: int = 0
    stale_protondb: int = 0
    total_games: int = 0

    def count_total_issues(self):
        return (
            len(self.store_unavailable)
            + len(self.missing_artwork)
            + len(self.missing_metadata)
            + len(self.ghost_apps)
            + self.stale_hltb
            + self.stale_protondb
        )


class LibraryHealthService:
    """Placeholder for future non-threaded health queries.

    All the heavy lifting happens in LibraryHealthThread which runs in a QThread).
    This class might get static helper methods later.
    """

    pass
