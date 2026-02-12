# tests/unit/test_date_utils.py

"""Tests for date_utils with localised month names.

format_timestamp_to_date() resolves month names via a *deferred* import:
    from src.utils.i18n import t
Because the import happens at call-time (not at module-load time) the correct
mock target is ``src.utils.i18n.t``, NOT ``src.utils.date_utils.t``.

All tests are fully self-contained — no application boot or file-system
access is required.
"""

import pytest
from unittest.mock import patch
from datetime import datetime

# ---------------------------------------------------------------------------
# Mock translation dictionaries — simulate what t() returns per locale
# ---------------------------------------------------------------------------

_DE: dict[str, str] = {
    "date.locale_id": "de",
    "date.months_short.jan": "Jan",
    "date.months_short.feb": "Feb",
    "date.months_short.mar": "Mrz",
    "date.months_short.apr": "Apr",
    "date.months_short.may": "Mai",
    "date.months_short.jun": "Jun",
    "date.months_short.jul": "Jul",
    "date.months_short.aug": "Aug",
    "date.months_short.sep": "Sep",
    "date.months_short.oct": "Okt",
    "date.months_short.nov": "Nov",
    "date.months_short.dec": "Dez",
}

_EN: dict[str, str] = {
    "date.locale_id": "en",
    "date.months_short.jan": "Jan",
    "date.months_short.feb": "Feb",
    "date.months_short.mar": "Mar",
    "date.months_short.apr": "Apr",
    "date.months_short.may": "May",
    "date.months_short.jun": "Jun",
    "date.months_short.jul": "Jul",
    "date.months_short.aug": "Aug",
    "date.months_short.sep": "Sep",
    "date.months_short.oct": "Oct",
    "date.months_short.nov": "Nov",
    "date.months_short.dec": "Dec",
}


def _t_de(key: str) -> str:
    """Mock t() returning German translations."""
    return _DE.get(key, f"[{key}]")


def _t_en(key: str) -> str:
    """Mock t() returning English translations."""
    return _EN.get(key, f"[{key}]")


# ==================================================================
# German locale — format output
# ==================================================================


class TestFormatDE:
    """format_timestamp_to_date() with German locale active."""

    @patch("src.utils.i18n.t", side_effect=_t_de)
    def test_dezember(self, _mock_t):
        """December date displays as '07. Dez 2024'."""
        from src.utils.date_utils import format_timestamp_to_date

        ts = str(int(datetime(2024, 12, 7, 12, 0).timestamp()))
        assert format_timestamp_to_date(ts) == "07. Dez 2024"

    @patch("src.utils.i18n.t", side_effect=_t_de)
    def test_mai(self, _mock_t):
        """May date displays as '21. Mai 2019'."""
        from src.utils.date_utils import format_timestamp_to_date

        ts = str(int(datetime(2019, 5, 21, 12, 0).timestamp()))
        assert format_timestamp_to_date(ts) == "21. Mai 2019"

    @patch("src.utils.i18n.t", side_effect=_t_de)
    def test_maerz(self, _mock_t):
        """March date displays as '01. Mrz 2020'."""
        from src.utils.date_utils import format_timestamp_to_date

        ts = str(int(datetime(2020, 3, 1, 12, 0).timestamp()))
        assert format_timestamp_to_date(ts) == "01. Mrz 2020"

    @patch("src.utils.i18n.t", side_effect=_t_de)
    def test_oktober(self, _mock_t):
        """October date displays as '15. Okt 2021'."""
        from src.utils.date_utils import format_timestamp_to_date

        ts = str(int(datetime(2021, 10, 15, 12, 0).timestamp()))
        assert format_timestamp_to_date(ts) == "15. Okt 2021"

    @patch("src.utils.i18n.t", side_effect=_t_de)
    def test_januar(self, _mock_t):
        """January date displays as '03. Jan 2018'."""
        from src.utils.date_utils import format_timestamp_to_date

        ts = str(int(datetime(2018, 1, 3, 12, 0).timestamp()))
        assert format_timestamp_to_date(ts) == "03. Jan 2018"

    @patch("src.utils.i18n.t", side_effect=_t_de)
    def test_august(self, _mock_t):
        """August date displays as '30. Aug 2022'."""
        from src.utils.date_utils import format_timestamp_to_date

        ts = str(int(datetime(2022, 8, 30, 12, 0).timestamp()))
        assert format_timestamp_to_date(ts) == "30. Aug 2022"


# ==================================================================
# English locale — format output (no dot after day)
# ==================================================================


class TestFormatEN:
    """format_timestamp_to_date() with English locale active."""

    @patch("src.utils.i18n.t", side_effect=_t_en)
    def test_december(self, _mock_t):
        """December date displays as '07 Dec 2024' (no dot)."""
        from src.utils.date_utils import format_timestamp_to_date

        ts = str(int(datetime(2024, 12, 7, 12, 0).timestamp()))
        assert format_timestamp_to_date(ts) == "07 Dec 2024"

    @patch("src.utils.i18n.t", side_effect=_t_en)
    def test_may(self, _mock_t):
        """May date displays as '21 May 2019'."""
        from src.utils.date_utils import format_timestamp_to_date

        ts = str(int(datetime(2019, 5, 21, 12, 0).timestamp()))
        assert format_timestamp_to_date(ts) == "21 May 2019"

    @patch("src.utils.i18n.t", side_effect=_t_en)
    def test_march(self, _mock_t):
        """March date displays as '01 Mar 2020' (not 'Mrz')."""
        from src.utils.date_utils import format_timestamp_to_date

        ts = str(int(datetime(2020, 3, 1, 12, 0).timestamp()))
        assert format_timestamp_to_date(ts) == "01 Mar 2020"

    @patch("src.utils.i18n.t", side_effect=_t_en)
    def test_october(self, _mock_t):
        """October date displays as '15 Oct 2021'."""
        from src.utils.date_utils import format_timestamp_to_date

        ts = str(int(datetime(2021, 10, 15, 12, 0).timestamp()))
        assert format_timestamp_to_date(ts) == "15 Oct 2021"


# ==================================================================
# Edge cases — locale-independent paths (never reach i18n)
# ==================================================================


class TestEdgeCases:
    """Inputs that bypass the i18n path entirely."""

    def test_none(self):
        """None -> empty string."""
        from src.utils.date_utils import format_timestamp_to_date

        assert format_timestamp_to_date(None) == ""

    def test_empty_string(self):
        """'' -> empty string."""
        from src.utils.date_utils import format_timestamp_to_date

        assert format_timestamp_to_date("") == ""

    def test_whitespace_only(self):
        """'   ' -> empty string."""
        from src.utils.date_utils import format_timestamp_to_date

        assert format_timestamp_to_date("   ") == ""

    def test_bare_year_str(self):
        """'2004' is <= 9999 -> returned unchanged."""
        from src.utils.date_utils import format_timestamp_to_date

        assert format_timestamp_to_date("2004") == "2004"

    def test_bare_year_int(self):
        """int 2004 is <= 9999 -> returned as '2004'."""
        from src.utils.date_utils import format_timestamp_to_date

        assert format_timestamp_to_date(2004) == "2004"

    def test_zero_is_bare_year(self):
        """'0' is <= 9999 -> returned as '0'."""
        from src.utils.date_utils import format_timestamp_to_date

        assert format_timestamp_to_date("0") == "0"

    def test_already_formatted_german_passthrough(self):
        """'07. Dez 2024' is non-numeric -> returned as-is."""
        from src.utils.date_utils import format_timestamp_to_date

        assert format_timestamp_to_date("07. Dez 2024") == "07. Dez 2024"

    def test_already_formatted_english_passthrough(self):
        """'21 May 2019' is non-numeric -> returned as-is."""
        from src.utils.date_utils import format_timestamp_to_date

        assert format_timestamp_to_date("21 May 2019") == "21 May 2019"

    def test_int_timestamp_contains_year(self):
        """Plain int timestamp works — result must contain '2020'."""
        from src.utils.date_utils import format_timestamp_to_date

        result = format_timestamp_to_date(1587646884)
        assert "2020" in result


# ==================================================================
# Fallback: i18n kaputt -> numerisches Format
# ==================================================================


class TestFallback:
    """When i18n raises an exception the fallback DD.MM.YYYY must fire."""

    @patch("src.utils.i18n.t", side_effect=RuntimeError("boom"))
    def test_fallback_numeric(self, _mock_t):
        """Broken i18n -> falls back to plain DD.MM.YYYY."""
        from src.utils.date_utils import format_timestamp_to_date

        ts = str(int(datetime(2024, 12, 7, 12, 0).timestamp()))
        assert format_timestamp_to_date(ts) == "07.12.2024"


# ==================================================================
# parse_date_to_timestamp — locale-independent
# ==================================================================


class TestParse:
    """parse_date_to_timestamp — input parsing has no i18n dependency."""

    def test_european_format(self):
        """DD.MM.YYYY -> numeric timestamp."""
        from src.utils.date_utils import parse_date_to_timestamp

        assert parse_date_to_timestamp("23.04.2020").isdigit()

    def test_iso_format(self):
        """YYYY-MM-DD -> numeric timestamp."""
        from src.utils.date_utils import parse_date_to_timestamp

        assert parse_date_to_timestamp("2020-04-23").isdigit()

    def test_bare_year(self):
        """'2017' -> kept as-is."""
        from src.utils.date_utils import parse_date_to_timestamp

        assert parse_date_to_timestamp("2017") == "2017"

    def test_raw_timestamp_passthrough(self):
        """Already a timestamp -> kept as-is."""
        from src.utils.date_utils import parse_date_to_timestamp

        assert parse_date_to_timestamp("1587646884") == "1587646884"

    def test_empty(self):
        """'' -> ''."""
        from src.utils.date_utils import parse_date_to_timestamp

        assert parse_date_to_timestamp("") == ""

    def test_whitespace(self):
        """'   ' -> ''."""
        from src.utils.date_utils import parse_date_to_timestamp

        assert parse_date_to_timestamp("   ") == ""

    def test_garbage(self):
        """Totally invalid -> returned unchanged."""
        from src.utils.date_utils import parse_date_to_timestamp

        assert parse_date_to_timestamp("nein-das-ist-kein-datum") == "nein-das-ist-kein-datum"

    def test_slash_format(self):
        """YYYY/MM/DD is also accepted."""
        from src.utils.date_utils import parse_date_to_timestamp

        assert parse_date_to_timestamp("2020/04/23").isdigit()


# ==================================================================
# Round-trip: parse -> format -> correct month preserved
# ==================================================================


class TestRoundTrip:
    """UI round-trip: user types DD.MM.YYYY -> timestamp -> localised string.

    The month name in the output must match the month that was typed.
    """

    @patch("src.utils.i18n.t", side_effect=_t_de)
    @pytest.mark.parametrize(
        "input_date,expected_month",
        [
            ("23.04.2020", "Apr"),
            ("15.12.2019", "Dez"),
            ("01.03.2021", "Mrz"),
            ("10.10.2018", "Okt"),
            ("28.02.2020", "Feb"),
        ],
    )
    def test_month_preserved_de(self, _mock_t, input_date: str, expected_month: str):
        """parse -> format preserves the correct German month abbreviation."""
        from src.utils.date_utils import parse_date_to_timestamp, format_timestamp_to_date

        ts: str = parse_date_to_timestamp(input_date)
        display: str = format_timestamp_to_date(ts)
        assert expected_month in display, f"Expected '{expected_month}' in '{display}'"

    @patch("src.utils.i18n.t", side_effect=_t_en)
    @pytest.mark.parametrize(
        "input_date,expected_month",
        [
            ("23.04.2020", "Apr"),
            ("15.12.2019", "Dec"),
            ("01.03.2021", "Mar"),
        ],
    )
    def test_month_preserved_en(self, _mock_t, input_date: str, expected_month: str):
        """parse -> format preserves the correct English month abbreviation."""
        from src.utils.date_utils import parse_date_to_timestamp, format_timestamp_to_date

        ts: str = parse_date_to_timestamp(input_date)
        display: str = format_timestamp_to_date(ts)
        assert expected_month in display, f"Expected '{expected_month}' in '{display}'"
