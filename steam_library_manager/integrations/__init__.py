#
# steam_library_manager/integrations/__init__.py
# Integrations package
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
from __future__ import annotations

__all__: list[str] = ["SteamAppDetails", "SteamWebAPI"]

from steam_library_manager.integrations.steam_web_api import SteamAppDetails, SteamWebAPI
