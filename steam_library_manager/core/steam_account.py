#
# steam_library_manager/core/steam_account.py
# SteamAccount dataclass for user identity and display info
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["SteamAccount"]


@dataclass
class SteamAccount:
    """Represents a Steam user account with IDs and display info."""

    account_id: int
    steam_id_64: int
    display_name: str
    avatar_url: str | None = None

    def __str__(self) -> str:
        return f"{self.account_id} ({self.display_name})"

    @property
    def formatted_id(self) -> str:
        return str(self.steam_id_64)
