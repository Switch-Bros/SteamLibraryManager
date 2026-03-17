#
# steam_library_manager/core/steam_account.py
# Steam account data model
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["SteamAccount"]


@dataclass
class SteamAccount:
    """Get Steam UserAccount from userdata/ folder.

    account_id is the short numeric id from folder name (example: 42927126),
    steam_id_64 is the full 64-bit id used by web api (example: 76562298104198224).
    """

    account_id: int
    steam_id_64: int
    display_name: str
    avatar_url: str | None = None

    def __str__(self):
        return "%d (%s)" % (self.account_id, self.display_name)

    @property
    def formatted_id(self):
        return str(self.steam_id_64)
