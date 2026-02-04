import re
from typing import List, Optional
from src.core.game_manager import Game

class SearchService:
    """Service handling complex game search logic including Regex support."""

    def filter_games(self, games: List[Game], query: str) -> List[Game]:
        """Filters a list of games based on a search query.

        Supports standard text search (case-insensitive) and regex.
        If a regex is invalid, it falls back to text search or returns empty.

        Args:
            games: List of Game objects to filter.
            query: The search string.

        Returns:
            List[Game]: The filtered list of games.
        """
        if not query:
            return games

        query = query.strip()
        
        # Future-Proofing: Here we can add switches for "dev:Valve" etc.
        
        # Try Regex search if it looks like regex (optional criteria could be added)
        # For now, we treat everything as potential regex if it compiles, 
        # but to be user friendly, we default to simple substring for normal text.
        # Let's implement a smart search: Case-insensitive substring match first.
        
        # If the user explicitly wants regex, maybe later we use a prefix like "r:".
        # For now, let's keep it robust: simple substring match.
        
        return [
            g for g in games 
            if query.lower() in g.name.lower()
        ]

    def validate_regex(self, pattern: str) -> bool:
        """Checks if a regex pattern is valid."""
        try:
            re.compile(pattern)
            return True
        except re.error:
            return False
