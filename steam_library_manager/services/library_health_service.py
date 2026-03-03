"""Dataclasses for library health check results.

Provides StoreCheckResult (per-game store status) and HealthReport
(aggregate health metrics) used by the LibraryHealthThread and
HealthCheckResultDialog.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["LibraryHealthService", "HealthReport", "StoreCheckResult"]


@dataclass(frozen=True)
class StoreCheckResult:
    """Result of a store availability check for a single game.

    Attributes:
        app_id: The Steam app ID.
        name: The game name.
        status: One of: 'available', 'age_gate', 'geo_locked',
            'delisted', 'removed', 'unknown'.
        details: Human-readable detail string (e.g. HTTP status code).
    """

    app_id: int
    name: str
    status: str
    details: str


@dataclass
class HealthReport:
    """Complete library health report.

    Attributes:
        store_unavailable: Games not available in the Steam Store.
        missing_artwork: Games without cover images as (app_id, name) tuples.
        missing_metadata: Games missing publisher/developer/release date.
        ghost_apps: App IDs that are not real games (DLCs, tools, demos).
        stale_hltb: Number of games with HLTB cache older than 30 days.
        stale_protondb: Number of games with ProtonDB cache older than 7 days.
        total_games: Total number of games checked.
    """

    store_unavailable: list[StoreCheckResult] = field(default_factory=list)
    missing_artwork: list[tuple[int, str]] = field(default_factory=list)
    missing_metadata: list[tuple[int, str]] = field(default_factory=list)
    ghost_apps: list[tuple[int, str]] = field(default_factory=list)
    stale_hltb: int = 0
    stale_protondb: int = 0
    total_games: int = 0

    def count_total_issues(self) -> int:
        """Returns the total number of issues found across all categories.

        Returns:
            Sum of all issue counts.
        """
        return (
            len(self.store_unavailable)
            + len(self.missing_artwork)
            + len(self.missing_metadata)
            + len(self.ghost_apps)
            + self.stale_hltb
            + self.stale_protondb
        )


class LibraryHealthService:
    """Placeholder for future library health service logic.

    Currently the health check logic lives in LibraryHealthThread.
    This class may be extended for non-threaded health queries.
    """
