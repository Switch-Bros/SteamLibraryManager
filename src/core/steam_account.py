"""
Steam Account data structure.

This module defines the SteamAccount dataclass which represents a Steam user account
with their various IDs and display information.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class SteamAccount:
    """Represents a Steam user account.
    
    Attributes:
        account_id: The short Steam account ID (from userdata folder name)
        steam_id_64: The 64-bit Steam ID (account_id + STEAM_ID_BASE)
        display_name: The user's Steam profile display name
        avatar_url: Optional URL to the user's avatar image
    """
    account_id: int
    steam_id_64: int
    display_name: str
    avatar_url: Optional[str] = None
    
    def __str__(self) -> str:
        """String representation showing account ID and display name."""
        return f"{self.account_id} ({self.display_name})"
    
    @property
    def formatted_id(self) -> str:
        """Returns formatted SteamID64 as string."""
        return str(self.steam_id_64)
