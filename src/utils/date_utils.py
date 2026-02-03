# src/utils/date_utils.py

"""
Utility functions for converting between date formats and Unix timestamps.

This module provides functions to parse various date formats and convert them
to Unix timestamps, as well as format timestamps back to readable dates.

Display format is DD.MM.YYYY (European) throughout the application.
Accepted input formats: DD.MM.YYYY, YYYY-MM-DD, YYYY, raw Unix timestamp.
"""

from datetime import datetime


def parse_date_to_timestamp(date_str: str) -> str:
    """Converts various date formats to a Unix timestamp string.

    Accepted input formats (in order of priority):
        - DD.MM.YYYY   → converted to Unix timestamp  (primary user input)
        - YYYY-MM-DD   → converted to Unix timestamp  (ISO fallback)
        - YYYY         → kept as-is (year-only shortcut)
        - Raw timestamp (numeric, > 100 000 000) → kept as-is

    Args:
        date_str: The date string entered by the user.

    Returns:
        A Unix timestamp string, a bare year string, or the original value
        when no format matches.
    """
    if not date_str or not date_str.strip():
        return ""

    date_str = date_str.strip()

    # Already a pure number → timestamp or bare year, keep as-is
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

    # Nothing matched → return original so the user sees what went wrong
    return date_str


def format_timestamp_to_date(value) -> str:
    """Converts a Unix timestamp to a human-readable date string (DD.MM.YYYY).

    Handles multiple input types gracefully:
        - Unix timestamp (int or str, > 100 000 000) → DD.MM.YYYY
        - Bare year (str, 4 digits, ≤ 9999)          → returned as-is
        - Already formatted string                    → returned as-is
        - None / empty                                → empty string

    Args:
        value: A Unix timestamp, a year string, or an already-formatted date.

    Returns:
        A date string in DD.MM.YYYY format, a bare year, or an empty string.
    """
    if not value:
        return ""

    value_str = str(value).strip()

    if value_str.isdigit():
        ts = int(value_str)

        # Bare year (e.g. "2004") — return as-is
        if ts <= 9999:
            return value_str

        # Plausible Unix timestamp (> 100 000 000 ≈ year 1973)
        if ts > 100_000_000:
            try:
                dt = datetime.fromtimestamp(ts)
                return dt.strftime("%d.%m.%Y")
            except (OSError, OverflowError, ValueError):
                pass  # fall through to raw return

    # Already a string like "05.05.2017" or anything else → return unchanged
    return value_str