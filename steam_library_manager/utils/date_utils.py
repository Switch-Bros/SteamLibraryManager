#
# steam_library_manager/utils/date_utils.py
# Date formatting and parsing utilities
#
# Copyright (c) 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# FIXME: locale handling is fragile


from __future__ import annotations

import calendar
from datetime import datetime

__all__ = ["parse_date_to_timestamp", "format_timestamp_to_date", "to_timestamp", "year_from_timestamp"]

# public api


# various date formats -> unix timestamp string
def parse_date_to_timestamp(date_str: str) -> str:
    if not date_str or not date_str.strip():
        return ""

    date_str = date_str.strip()

    # Already a pure number -> timestamp or bare year, keep as-is
    if date_str.isdigit():
        return date_str

    # Try formats in priority order
    # European: DD.MM.YYYY  (user's preferred input)
    # ISO:      YYYY-MM-DD
    # Others:   YYYY/MM/DD, DD-MM-YYYY
    formats = ["%d.%m.%Y", "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return str(calendar.timegm(dt.timetuple()))
        except ValueError:
            continue

    # Nothing matched -> return original so the user sees what went wrong
    return date_str


# any date-like value -> unix timestamp int
def to_timestamp(value) -> int:
    if not value:
        return 0
    if isinstance(value, int):
        return value if value > 9999 else _year_to_ts(value) if value > 0 else 0
    s = str(value).strip()
    if not s:
        return 0
    # Pure digits
    if s.isdigit():
        n = int(s)
        if n > 100_000_000:
            return n
        if 1970 <= n <= 9999:
            return _year_to_ts(n)
        return 0
    # Numeric date formats (locale-independent)
    for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return calendar.timegm(datetime.strptime(s, fmt).timetuple())
        except ValueError:
            continue
    # Steam store format uses English month names ("Mar 23, 2020")
    # strptime depends on locale, so force C locale for parsing
    return _parse_english_date(s)


# unix timestamp -> year string
def year_from_timestamp(ts: int) -> str:
    if not ts or ts <= 0:
        return ""
    if ts <= 9999:
        return str(ts)
    try:
        return str(datetime.fromtimestamp(ts).year)
    except (OSError, OverflowError, ValueError):
        return ""


# parse english dates regardless of locale
def _parse_english_date(s: str) -> int:
    import locale

    saved = locale.getlocale(locale.LC_TIME)
    try:
        locale.setlocale(locale.LC_TIME, "C")
        for fmt in ("%b %d, %Y", "%d %b, %Y", "%b %Y", "%B %d, %Y"):
            try:
                return calendar.timegm(datetime.strptime(s, fmt).timetuple())
            except ValueError:
                continue
    except locale.Error:
        pass
    finally:
        try:
            locale.setlocale(locale.LC_TIME, saved)
        except locale.Error:
            pass
    return 0


# bare year -> jan 1 UTC timestamp
def _year_to_ts(year: int) -> int:
    try:
        return calendar.timegm(datetime(year, 1, 1).timetuple())
    except (ValueError, OverflowError):
        return 0


# unix timestamp -> localized date string
def format_timestamp_to_date(value) -> str:
    if not value:
        return ""

    val = str(value).strip()
    if not val:
        return ""

    if val.isdigit():
        ts = int(val)

        # Bare year (e.g. "2004") - return as-is
        if ts <= 9999:
            return val

        # Plausible Unix timestamp (> 100 000 000 ~ year 1973)
        if ts > 100_000_000:
            try:
                dt = datetime.fromtimestamp(ts)
                return _format_date_localised(dt)
            except (OSError, OverflowError, ValueError):
                pass  # fall through to raw return

    # Already a string like "07. Dez 2024" or anything else -> return unchanged
    return val


# internal

# Month-index -> i18n key suffix (1-based; index 0 is an unused placeholder)
_MONTH_KEYS: list[str] = [
    "",  # placeholder - so that index 1 = January
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec",
]


# format with i18n month names
def _format_date_localised(dt: datetime) -> str:
    try:
        # Deferred import - date_utils can be loaded very early in boot
        from steam_library_manager.utils.i18n import t

        mkey = "date.months_short.%s" % _MONTH_KEYS[dt.month]
        mname = t(mkey)

        # Detect locale via a sentinel key placed in each date.json
        loc = t("date.locale_id")  # "de" or "en"

        if loc == "de":
            # German convention: dot after day number
            return "%02d. %s %d" % (dt.day, mname, dt.year)
        else:
            # English (and any other future locale): no dot
            return "%02d %s %d" % (dt.day, mname, dt.year)

    except (ImportError, RuntimeError, KeyError, IndexError):
        # Fallback: plain numeric format - always works, zero i18n dependency
        return dt.strftime("%d.%m.%Y")
