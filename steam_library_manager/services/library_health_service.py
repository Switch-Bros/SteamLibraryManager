#
# steam_library_manager/services/library_health_service.py
# Dataclasses for library health check results
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["LibraryHealthService", "HealthReport", "StoreCheckResult"]


@dataclass(frozen=True)
class StoreCheckResult:
    """Store availability check result for a single game."""

    app_id: int
    name: str
    status: str
    details: str


@dataclass
class HealthReport:
    """Aggregate library health metrics across all check categories."""

    store_unavailable: list[StoreCheckResult] = field(default_factory=list)
    missing_artwork: list[tuple[int, str]] = field(default_factory=list)
    missing_metadata: list[tuple[int, str]] = field(default_factory=list)
    ghost_apps: list[tuple[int, str]] = field(default_factory=list)
    stale_hltb: int = 0
    stale_protondb: int = 0
    total_games: int = 0

    def count_total_issues(self) -> int:
        """Sum of all issue counts across categories."""
        return (
            len(self.store_unavailable)
            + len(self.missing_artwork)
            + len(self.missing_metadata)
            + len(self.ghost_apps)
            + self.stale_hltb
            + self.stale_protondb
        )


class LibraryHealthService:
    """Placeholder for future non-threaded health queries."""
