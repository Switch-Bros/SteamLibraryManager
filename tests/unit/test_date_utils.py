# tests/unit/test_date_utils.py

"""Tests for date_utils: parse_date_to_timestamp ↔ format_timestamp_to_date round-trips."""

import pytest
from datetime import datetime
from src.utils.date_utils import parse_date_to_timestamp, format_timestamp_to_date


# ==================================================================
# format_timestamp_to_date  (timestamp  →  DD.MM.YYYY)
# ==================================================================

class TestFormatTimestampToDate:
    """Tests for converting raw timestamps to display strings."""

    def test_known_timestamp(self):
        """1587646884 = 23.04.2020 (UTC+2, but local — just check format shape)."""
        result = format_timestamp_to_date("1587646884")
        # Must be DD.MM.YYYY shape
        parts = result.split(".")
        assert len(parts) == 3
        assert len(parts[0]) == 2  # day
        assert len(parts[1]) == 2  # month
        assert len(parts[2]) == 4  # year
        assert parts[2] == "2020"

    def test_bare_year_passthrough(self):
        """A 4-digit year like '2004' must come back unchanged."""
        assert format_timestamp_to_date("2004") == "2004"
        assert format_timestamp_to_date(2004) == "2004"

    def test_empty_and_none(self):
        """None / empty / whitespace → empty string."""
        assert format_timestamp_to_date(None) == ""
        assert format_timestamp_to_date("") == ""
        assert format_timestamp_to_date("   ") == ""

    def test_already_formatted_passthrough(self):
        """A string like '23.04.2020' is not numeric → returned as-is."""
        assert format_timestamp_to_date("23.04.2020") == "23.04.2020"

    def test_zero(self):
        """0 is ≤ 9999 → treated as bare year '0'."""
        assert format_timestamp_to_date("0") == "0"

    def test_integer_input(self):
        """Works with int input too, not just str."""
        result = format_timestamp_to_date(1587646884)
        assert "2020" in result


# ==================================================================
# parse_date_to_timestamp  (user input  →  timestamp string)
# ==================================================================

class TestParseDateToTimestamp:
    """Tests for converting user-entered date strings to timestamps."""

    def test_european_format(self):
        """DD.MM.YYYY → numeric timestamp."""
        result = parse_date_to_timestamp("23.04.2020")
        assert result.isdigit()
        # Verify round-trip: timestamp → back to same date
        assert format_timestamp_to_date(result) == "23.04.2020"

    def test_iso_format(self):
        """YYYY-MM-DD → numeric timestamp (fallback still works)."""
        result = parse_date_to_timestamp("2020-04-23")
        assert result.isdigit()
        # Should resolve to 23.04.2020
        assert format_timestamp_to_date(result) == "23.04.2020"

    def test_bare_year(self):
        """'2017' is numeric and ≤ 9999 → kept as-is."""
        assert parse_date_to_timestamp("2017") == "2017"

    def test_raw_timestamp_passthrough(self):
        """A raw timestamp string stays unchanged."""
        assert parse_date_to_timestamp("1587646884") == "1587646884"

    def test_empty_and_whitespace(self):
        """Empty / whitespace → empty string."""
        assert parse_date_to_timestamp("") == ""
        assert parse_date_to_timestamp("   ") == ""

    def test_garbage_input(self):
        """Totally invalid input → returned unchanged (user sees it)."""
        assert parse_date_to_timestamp("not-a-date") == "not-a-date"

    def test_slash_format(self):
        """YYYY/MM/DD is also accepted."""
        result = parse_date_to_timestamp("2020/04/23")
        assert result.isdigit()
        assert format_timestamp_to_date(result) == "23.04.2020"


# ==================================================================
# Round-trip: format → parse → format  (the real contract)
# ==================================================================

class TestDateRoundTrip:
    """The UI round-trip: timestamp → display → user saves → timestamp again."""

    @pytest.mark.parametrize("raw_ts", ["1587646884", "1494000108", "946684800"])
    def test_round_trip(self, raw_ts: str):
        """format(ts) → parse(display) → format again must be identical."""
        display: str = format_timestamp_to_date(raw_ts)
        back_to_ts: str = parse_date_to_timestamp(display)
        display_again: str = format_timestamp_to_date(back_to_ts)

        assert display == display_again, (
            f"Round-trip broken: {raw_ts} → '{display}' → {back_to_ts} → '{display_again}'"
        )