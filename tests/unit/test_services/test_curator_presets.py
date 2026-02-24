"""Tests for curator preset data integrity."""

from __future__ import annotations

from src.services.curator_presets import POPULAR_CURATORS, CuratorPreset


class TestCuratorPresets:
    """Tests for POPULAR_CURATORS preset list."""

    def test_popular_curators_is_tuple(self) -> None:
        """POPULAR_CURATORS should be an immutable tuple."""
        assert isinstance(POPULAR_CURATORS, tuple)

    def test_all_entries_are_curator_presets(self) -> None:
        """Every entry should be a CuratorPreset instance."""
        for preset in POPULAR_CURATORS:
            assert isinstance(preset, CuratorPreset)

    def test_all_ids_are_positive_integers(self) -> None:
        """All curator_ids should be positive integers."""
        for preset in POPULAR_CURATORS:
            assert isinstance(preset.curator_id, int)
            assert preset.curator_id > 0

    def test_no_duplicate_ids(self) -> None:
        """No two presets should have the same curator_id."""
        ids = [p.curator_id for p in POPULAR_CURATORS]
        assert len(ids) == len(set(ids))

    def test_all_names_non_empty(self) -> None:
        """All preset names should be non-empty strings."""
        for preset in POPULAR_CURATORS:
            assert isinstance(preset.name, str)
            assert len(preset.name) > 0

    def test_all_descriptions_non_empty(self) -> None:
        """All preset descriptions should be non-empty strings."""
        for preset in POPULAR_CURATORS:
            assert isinstance(preset.description, str)
            assert len(preset.description) > 0

    def test_preset_count(self) -> None:
        """Should have exactly 20 presets as specified."""
        assert len(POPULAR_CURATORS) == 20

    def test_preset_is_frozen(self) -> None:
        """CuratorPreset should be frozen (immutable)."""
        preset = POPULAR_CURATORS[0]
        with __import__("pytest").raises(AttributeError):
            preset.name = "Modified"  # type: ignore[misc]
