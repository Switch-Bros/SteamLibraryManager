# src/utils/date_utils.py

"""Utility functions for converting between date formats and Unix timestamps.

This module provides functions to parse various date formats and convert them
to Unix timestamps, as well as format timestamps back to readable dates.

Display format is locale-aware: the month name is resolved through the i18n
system so the output adapts automatically:
    German:  "07. Dez 2024"
    English: "07 Dec 2024"

Accepted input formats: DD.MM.YYYY, YYYY-MM-DD, YYYY, raw Unix timestamp.
"""

from __future__ import annotations

from datetime import datetime


__all__ = ['parse_date_to_timestamp', 'format_timestamp_to_date']

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_date_to_timestamp(date_str: str) -> str:
    """Converts various date formats to a Unix timestamp string.

    Accepted input formats (in order of priority):
        - DD.MM.YYYY   -> converted to Unix timestamp  (primary user input)
        - YYYY-MM-DD   -> converted to Unix timestamp  (ISO fallback)
        - YYYY         -> kept as-is (year-only shortcut)
        - Raw timestamp (numeric, > 100 000 000) -> kept as-is

    Args:
        date_str: The date string entered by the user.

    Returns:
        A Unix timestamp string, a bare year string, or the original value
        when no format matches.
    """
    if not date_str or not date_str.strip():
        return ""

    date_str = date_str.strip()

    # Already a pure number -> timestamp or bare year, keep as-is
    if date_str.isdigit():
        return date_str

    # --- Try formats in priority order ---
    # 1. European: DD.MM.YYYY  (user's preferred input)
    # 2. ISO:      YYYY-MM-DD
    # 3. Others:   YYYY/MM/DD, DD-MM-YYYY
    formats: list[str] = ["%d.%m.%Y", "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return str(int(dt.timestamp()))
        except ValueError:
            continue

    # Nothing matched -> return original so the user sees what went wrong
    return date_str

def format_timestamp_to_date(value) -> str:
    """Converts a Unix timestamp to a localised, human-readable date string.

    The month name is resolved via the i18n system so the output adapts to
    the current UI language automatically:
        - German:  "07. Dez 2024"  (dot after day)
        - English: "07 Dec 2024"   (no dot)

    Handles multiple input types gracefully:
        - Unix timestamp (int or str, > 100 000 000) -> localised date
        - Bare year (str or int, <= 9999)            -> returned as-is
        - Already formatted string                   -> returned as-is
        - None / empty / whitespace                  -> empty string

    Args:
        value: A Unix timestamp, a year string, or an already-formatted date.

    Returns:
        A localised date string, a bare year, or an empty string.
    """
    if not value:
        return ""

    value_str: str = str(value).strip()
    if not value_str:
        return ""

    if value_str.isdigit():
        ts: int = int(value_str)

        # Bare year (e.g. "2004") — return as-is
        if ts <= 9999:
            return value_str

        # Plausible Unix timestamp (> 100 000 000 ~ year 1973)
        if ts > 100_000_000:
            try:
                dt: datetime = datetime.fromtimestamp(ts)
                return _format_date_localised(dt)
            except (OSError, OverflowError, ValueError):
                pass  # fall through to raw return

    # Already a string like "07. Dez 2024" or anything else -> return unchanged
    return value_str

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Month-index -> i18n key suffix (1-based; index 0 is an unused placeholder)
_MONTH_KEYS: list[str] = [
    "",            # placeholder — so that index 1 = January
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec",
]

def _format_date_localised(dt: datetime) -> str:
    """Formats a datetime using a localised short month name from i18n.

    The import of t() is deferred to call-time (not import-time)
    to avoid circular imports during early boot.  If i18n is not yet
    initialised or raises for any reason the function falls back to the
    plain numeric DD.MM.YYYY format so that dates are never empty.

    German style:  "07. Dez 2024"  (dot after day)
    English style: "07 Dec 2024"   (no dot)

    Args:
        dt: The datetime object to format.

    Returns:
        A localised date string.
    """
    try:
        # Deferred import — date_utils can be loaded very early in boot
        from src.utils.i18n import t

        month_key: str = f"date.months_short.{_MONTH_KEYS[dt.month]}"
        month_name: str = t(month_key)

        # Detect locale via a sentinel key placed in each date.json
        locale_id: str = t("date.locale_id")  # "de" or "en"

        if locale_id == "de":
            # German convention: dot after day number
            return f"{dt.day:02d}. {month_name} {dt.year}"
        else:
            # English (and any other future locale): no dot
            return f"{dt.day:02d} {month_name} {dt.year}"

    except (ImportError, RuntimeError, KeyError, IndexError):
        # Fallback: plain numeric format — always works, zero i18n dependency
        return dt.strftime("%d.%m.%Y")