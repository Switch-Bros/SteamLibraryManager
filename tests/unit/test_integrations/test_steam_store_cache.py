# tests/unit/test_integrations/test_steam_store_cache.py

"""Tests for SteamStoreScraper cache coverage checking."""
import json
import time


class TestSteamStoreCacheCoverage:
    """Tests for cache coverage detection."""

    def test_get_cache_coverage_no_cache(self, tmp_path):
        """Test cache coverage when no cache exists."""
        from src.integrations.steam_store import SteamStoreScraper

        scraper = SteamStoreScraper(tmp_path, "en")
        app_ids = ["440", "730", "570"]

        coverage = scraper.get_cache_coverage(app_ids)

        assert coverage["total"] == 3
        assert coverage["cached"] == 0
        assert coverage["missing"] == 3
        assert coverage["percentage"] == 0.0

    def test_get_cache_coverage_full_cache(self, tmp_path):
        """Test cache coverage when all games are cached."""
        from src.integrations.steam_store import SteamStoreScraper

        scraper = SteamStoreScraper(tmp_path, "en")
        cache_dir = tmp_path / "store_tags"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Create cache files
        app_ids = ["440", "730", "570"]
        for app_id in app_ids:
            cache_file = cache_dir / f"{app_id}_en.json"
            with open(cache_file, "w") as f:
                json.dump(["Action", "FPS"], f)

        coverage = scraper.get_cache_coverage(app_ids)

        assert coverage["total"] == 3
        assert coverage["cached"] == 3
        assert coverage["missing"] == 0
        assert coverage["percentage"] == 100.0

    def test_get_cache_coverage_partial_cache(self, tmp_path):
        """Test cache coverage when some games are cached."""
        from src.integrations.steam_store import SteamStoreScraper

        scraper = SteamStoreScraper(tmp_path, "en")
        cache_dir = tmp_path / "store_tags"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Create cache for 2 out of 4 games
        for app_id in ["440", "730"]:
            cache_file = cache_dir / f"{app_id}_en.json"
            with open(cache_file, "w") as f:
                json.dump(["Action", "FPS"], f)

        app_ids = ["440", "730", "570", "271590"]
        coverage = scraper.get_cache_coverage(app_ids)

        assert coverage["total"] == 4
        assert coverage["cached"] == 2
        assert coverage["missing"] == 2
        assert coverage["percentage"] == 50.0

    def test_get_cache_coverage_expired_cache(self, tmp_path):
        """Test that expired cache (>30 days) is not counted."""
        from src.integrations.steam_store import SteamStoreScraper

        scraper = SteamStoreScraper(tmp_path, "en")
        cache_dir = tmp_path / "store_tags"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Create old cache file
        cache_file = cache_dir / "440_en.json"
        with open(cache_file, "w") as f:
            json.dump(["Action"], f)

        # Set modification time to 31 days ago
        old_time = time.time() - (31 * 24 * 60 * 60)
        import os

        os.utime(cache_file, (old_time, old_time))

        coverage = scraper.get_cache_coverage(["440"])

        # Expired cache should not be counted
        assert coverage["cached"] == 0
        assert coverage["missing"] == 1

    def test_get_cache_coverage_different_language(self, tmp_path):
        """Test that cache is language-specific."""
        from src.integrations.steam_store import SteamStoreScraper

        cache_dir = tmp_path / "store_tags"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Create cache for English
        cache_file = cache_dir / "440_en.json"
        with open(cache_file, "w") as f:
            json.dump(["Action"], f)

        # Check with German scraper
        scraper_de = SteamStoreScraper(tmp_path, "de")
        coverage = scraper_de.get_cache_coverage(["440"])

        # Should not find English cache when checking for German
        assert coverage["cached"] == 0
        assert coverage["missing"] == 1

    def test_get_cache_coverage_empty_list(self, tmp_path):
        """Test cache coverage with empty app_ids list."""
        from src.integrations.steam_store import SteamStoreScraper

        scraper = SteamStoreScraper(tmp_path, "en")
        coverage = scraper.get_cache_coverage([])

        assert coverage["total"] == 0
        assert coverage["cached"] == 0
        assert coverage["missing"] == 0
        assert coverage["percentage"] == 0.0
