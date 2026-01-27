"""
Date Utilities - Unix Timestamp Conversion
"""

from datetime import datetime


def parse_date_to_timestamp(date_str: str) -> str:
    """
    Convert various date formats to Unix timestamp

    Accepts:
    - Unix Timestamp: "1494000108" → remains unchanged
    - ISO Date: "2017-05-05" → converted to Unix timestamp
    - Year only: "2017" → remains unchanged
    - Invalid: "" → remains empty

    Returns:
        String with Unix timestamp or original value
    """
    if not date_str or not date_str.strip():
        return ""

    date_str = date_str.strip()

    # Is it already a number? (Timestamp or year)
    if date_str.isdigit():
        # If > 100000000 = Timestamp, keep it
        # If < 10000 = Year, keep it
        return date_str

    # Try to parse ISO format (YYYY-MM-DD)
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        timestamp = int(dt.timestamp())
        return str(timestamp)
    except ValueError:
        pass

    # Try other formats
    formats = ["%Y/%m/%d", "%d.%m.%Y", "%d-%m-%Y"]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            timestamp = int(dt.timestamp())
            return str(timestamp)
        except ValueError:
            continue

    # If nothing works, return original
    return date_str


def format_timestamp_to_date(value) -> str:
    """
    Convert Unix timestamps to readable date

    Args:
        value: Unix Timestamp (int/str), year (str), or ISO date (str)

    Returns:
        Formatted date as "YYYY-MM-DD" or original value
    """
    if not value:
        return ""

    value_str = str(value).strip()

    # Check if it's a number
    if value_str.isdigit():
        try:
            ts = int(value_str)
            # Simple check: Is the number greater than 100,000,000?
            # Timestamp for year 2000 is 946684800
            # A year like "2004" is much smaller
            if ts > 100000000:
                dt = datetime.fromtimestamp(ts)
                return dt.strftime("%Y-%m-%d")
        except (ValueError, OSError, OverflowError):
            pass  # If error, return original

    return value_str