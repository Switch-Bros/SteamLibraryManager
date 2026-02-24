"""
Steam Curator Client for fetching curator recommendations.

Parses curator recommendations from the Steam Store HTML endpoint,
supporting pagination and recommendation type classification.
"""

from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

logger = logging.getLogger("steamlibmgr.curator_client")

__all__ = ["CuratorClient", "CuratorRecommendation"]


class CuratorRecommendation(Enum):
    """Types of curator recommendations matching Steam Store classes."""

    RECOMMENDED = "recommended"
    NOT_RECOMMENDED = "not_recommended"
    INFORMATIONAL = "informational"


# Regex to extract curator ID and optional name slug from various URL formats
_CURATOR_ID_PATTERN = re.compile(r"/curator/(\d+)")
_CURATOR_NAME_PATTERN = re.compile(r"/curator/\d+-([^/?]+)")

# Regex to extract app IDs and recommendation types from HTML
_APP_PATTERN = re.compile(r'data-ds-appid="(\d+)"')
# Per-item pattern: finds recommendation blocks with their type
_ITEM_BLOCK_PATTERN = re.compile(
    r'class="recommendation[^"]*\s(color_recommended|color_not_recommended|color_informational)'
    r'[^"]*"[^>]*>.*?data-ds-appid="(\d+)"',
    re.DOTALL,
)
# Alternative: appid first, then color class
_ITEM_BLOCK_ALT_PATTERN = re.compile(
    r'data-ds-appid="(\d+)".*?' r"(color_recommended|color_not_recommended|color_informational)",
    re.DOTALL,
)

_COLOR_TO_ENUM: dict[str, CuratorRecommendation] = {
    "color_recommended": CuratorRecommendation.RECOMMENDED,
    "color_not_recommended": CuratorRecommendation.NOT_RECOMMENDED,
    "color_informational": CuratorRecommendation.INFORMATIONAL,
}

_PAGE_SIZE = 50
_API_TEMPLATE = (
    "https://store.steampowered.com/curator/{curator_id}"
    "/ajaxgetfilteredrecommendations/render/"
    "?query=&start={start}&count={count}"
)


class CuratorClient:
    """Client for fetching Steam Curator recommendations.

    Fetches paginated recommendations from the Steam Store API
    and parses the HTML response to extract app IDs and types.
    """

    @staticmethod
    def parse_curator_id(url: str) -> int | None:
        """Extract the numeric curator ID from a Steam Curator URL.

        Args:
            url: Full or partial Steam Curator URL.

        Returns:
            The curator ID as integer, or None if not found.
        """
        match = _CURATOR_ID_PATTERN.search(url)
        if match:
            return int(match.group(1))
        # Try plain numeric string
        stripped = url.strip().rstrip("/")
        if stripped.isdigit():
            return int(stripped)
        return None

    @staticmethod
    def parse_curator_name(url: str) -> str | None:
        """Extract the curator display name from a Steam Curator URL slug.

        Converts the URL slug (e.g. "PCGamer", "Waifu-Hunter") into a
        readable name by replacing hyphens with spaces.

        Args:
            url: Full or partial Steam Curator URL.

        Returns:
            The curator name, or None if not parseable from the URL.
        """
        match = _CURATOR_NAME_PATTERN.search(url)
        if not match:
            return None
        slug = match.group(1).rstrip("/")
        return slug.replace("-", " ")

    @staticmethod
    def parse_recommendations_html(html: str) -> dict[int, CuratorRecommendation]:
        """Parse recommendations from the HTML fragment returned by Steam.

        The HTML contains recommendation blocks with CSS classes indicating type
        (color_recommended, color_not_recommended, color_informational) and
        data-ds-appid attributes for the game.

        Args:
            html: Raw HTML string from the Steam curator API.

        Returns:
            Mapping of app_id to recommendation type.
        """
        results: dict[int, CuratorRecommendation] = {}

        # Try appid-first pattern (most common in Steam's HTML)
        for match in _ITEM_BLOCK_ALT_PATTERN.finditer(html):
            app_id_str, color_class = match.group(1), match.group(2)
            app_id = int(app_id_str)
            if app_id not in results:
                rec_type = _COLOR_TO_ENUM.get(color_class, CuratorRecommendation.RECOMMENDED)
                results[app_id] = rec_type

        # Fallback: try color-first pattern
        if not results:
            for match in _ITEM_BLOCK_PATTERN.finditer(html):
                color_class, app_id_str = match.group(1), match.group(2)
                app_id = int(app_id_str)
                if app_id not in results:
                    rec_type = _COLOR_TO_ENUM.get(color_class, CuratorRecommendation.RECOMMENDED)
                    results[app_id] = rec_type

        # Last resort: just extract app IDs without type info (default to RECOMMENDED)
        if not results:
            for match in _APP_PATTERN.finditer(html):
                app_id = int(match.group(1))
                if app_id not in results:
                    results[app_id] = CuratorRecommendation.RECOMMENDED

        return results

    def fetch_recommendations(
        self,
        curator_url: str,
        progress_callback: Callable[[int], None] | None = None,
    ) -> dict[int, CuratorRecommendation]:
        """Fetch all recommendations for a Steam Curator.

        Paginates through the Steam Store API in batches of 50.

        Args:
            curator_url: Steam Curator URL or numeric ID.
            progress_callback: Optional callback(page_number) for progress updates.

        Returns:
            Mapping of app_id to recommendation type.

        Raises:
            ValueError: If the curator URL is invalid.
            ConnectionError: If the Steam Store API is unreachable.
        """
        curator_id = self.parse_curator_id(curator_url)
        if curator_id is None:
            raise ValueError(f"Invalid curator URL: {curator_url}")

        all_recommendations: dict[int, CuratorRecommendation] = {}
        offset = 0
        page = 1

        while True:
            if progress_callback:
                progress_callback(page)

            url = _API_TEMPLATE.format(
                curator_id=curator_id,
                start=offset,
                count=_PAGE_SIZE,
            )

            try:
                import json

                request = Request(url)
                request.add_header("Accept", "application/json")
                with urlopen(request, timeout=15) as response:  # noqa: S310
                    data = json.loads(response.read().decode("utf-8"))
            except (URLError, TimeoutError, OSError) as exc:
                raise ConnectionError(f"Failed to fetch curator data: {exc}") from exc

            if not data.get("success"):
                break

            html = data.get("results_html", "")
            if not html or not html.strip():
                break

            page_results = self.parse_recommendations_html(html)
            if not page_results:
                break

            all_recommendations.update(page_results)

            total_count = data.get("total_count", 0)
            offset += _PAGE_SIZE
            page += 1

            if offset >= total_count:
                break

        logger.info("Fetched %d recommendations for curator %d", len(all_recommendations), curator_id)
        return all_recommendations

    @staticmethod
    def fetch_top_curators(count: int = 50) -> list[dict[str, int | str]]:
        """Fetches the most popular Steam curators via the public API.

        Args:
            count: Number of curators to fetch (max 50).

        Returns:
            List of dicts with keys: curator_id, name.

        Raises:
            ConnectionError: If the Steam Store API is unreachable.
        """
        import json

        url = f"https://store.steampowered.com/curators/ajaxgetcurators/render/" f"?start=0&count={min(count, 50)}"
        try:
            request = Request(url)
            request.add_header("Accept", "application/json")
            with urlopen(request, timeout=15) as response:  # noqa: S310
                data = json.loads(response.read().decode("utf-8"))
        except (URLError, TimeoutError, OSError) as exc:
            raise ConnectionError(f"Failed to fetch top curators: {exc}") from exc

        results: list[dict[str, int | str]] = []
        html = data.get("results_html", "")
        if not html:
            return results

        # Parse curator blocks from the HTML
        curator_block_pattern = re.compile(
            r'data-clanid="(\d+)".*?curator_name[^>]*>([^<]+)<',
            re.DOTALL,
        )
        for match in curator_block_pattern.finditer(html):
            results.append(
                {
                    "curator_id": int(match.group(1)),
                    "name": match.group(2).strip(),
                }
            )

        logger.info("Fetched %d top curators", len(results))
        return results

    @staticmethod
    def discover_subscribed_curators(steam_cookies: str) -> list[dict[str, int | str]]:
        """Discovers curators the user is currently following on Steam.

        Parses the ``gFollowedCuratorIDs`` JavaScript variable from the
        user's Steam curator page.

        Args:
            steam_cookies: Cookie header value for authentication
                           (must contain ``steamLoginSecure``).

        Returns:
            List of dicts with keys: curator_id, name (name may be empty).

        Raises:
            ConnectionError: If the Steam Store is unreachable.
        """
        url = "https://store.steampowered.com/curators/mycurators/"
        try:
            request = Request(url)
            request.add_header("Cookie", steam_cookies)
            with urlopen(request, timeout=15) as response:  # noqa: S310
                html = response.read().decode("utf-8", errors="replace")
        except (URLError, TimeoutError, OSError) as exc:
            raise ConnectionError(f"Failed to fetch subscribed curators: {exc}") from exc

        # Extract gFollowedCuratorIDs = [123, 456, ...]
        ids_pattern = re.compile(r"gFollowedCuratorIDs\s*=\s*\[([^\]]*)\]")
        match = ids_pattern.search(html)
        if not match:
            logger.warning("Could not find gFollowedCuratorIDs in page")
            return []

        raw_ids = match.group(1).strip()
        if not raw_ids:
            return []

        results: list[dict[str, int | str]] = []
        for chunk in raw_ids.split(","):
            chunk = chunk.strip()
            if chunk.isdigit():
                results.append({"curator_id": int(chunk), "name": ""})

        # Try to extract names from the same page
        name_pattern = re.compile(
            r'data-clanid="(\d+)"[^>]*>.*?curator_name[^>]*>([^<]+)<',
            re.DOTALL,
        )
        name_map = {int(m.group(1)): m.group(2).strip() for m in name_pattern.finditer(html)}
        for entry in results:
            cid = entry["curator_id"]
            if isinstance(cid, int) and cid in name_map:
                entry["name"] = name_map[cid]

        logger.info("Discovered %d subscribed curators", len(results))
        return results
