# src/core/non_game_apps.py

"""
List of Steam App IDs that are NOT actual games.

These include:
- Proton compatibility tools
- Steam Play tools
- Soundtracks
- Development tools
- Other non-game content
"""
from __future__ import annotations

__all__ = ["NON_GAME_APP_IDS", "is_real_game"]

# Proton versions and compatibility tools
NON_GAME_APP_IDS = {
    # Proton versions
    "1887720",  # Proton 7.0
    "1493710",  # Proton Experimental
    "1420170",  # Proton 5.0
    "1113280",  # Proton 4.11
    "961940",  # Proton 4.2
    "930400",  # Proton 3.16
    "858280",  # Proton 3.7
    # Proton Beta versions
    "1826330",  # Proton 8.0
    "2180100",  # Proton 9.0
    "2348590",  # Proton Hotfix
    # Steam Linux Runtime
    "1070560",  # Steam Linux Runtime - Soldier
    "1391110",  # Steam Linux Runtime - Sniper
    "1628350",  # Steam Linux Runtime 3.0 (sniper)
    # Steam Play compatibility tools
    "1517290",  # Steamworks Common Redistributables
    "228980",  # Steamworks Common Redistributables (old)
    # Development tools
    "1628350",  # Steamworks SDK
    "223530",  # SDK Base 2006
    "243750",  # Source Filmmaker
    # Other non-game content
    "0",  # Invalid/Unknown
}


def is_real_game(app_id: str) -> bool:
    """
    Check if an app ID represents a real game.

    Args:
        app_id: Steam app ID as string

    Returns:
        bool: True if it's a real game, False if it's a tool/soundtrack/etc.
    """
    return app_id not in NON_GAME_APP_IDS
