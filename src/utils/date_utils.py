"""
Date Utilities - Unix Timestamp Conversion
Speichern als: src/utils/date_utils.py
"""

from datetime import datetime


def parse_date_to_timestamp(date_str: str) -> str:
    """
    Konvertiert verschiedene Datums-Formate zu Unix Timestamp

    Akzeptiert:
    - Unix Timestamp: "1494000108" → bleibt unverändert
    - ISO Date: "2017-05-05" → wird zu Unix Timestamp
    - Year only: "2017" → bleibt unverändert
    - Invalid: "" → bleibt leer

    Returns:
        String mit Unix Timestamp oder Original-Wert
    """
    if not date_str or not date_str.strip():
        return ""

    date_str = date_str.strip()

    # Ist es bereits eine Zahl? (Timestamp oder Jahr)
    if date_str.isdigit():
        # Wenn > 100000000 = Timestamp, behalte es
        # Wenn < 10000 = Jahr, behalte es
        return date_str

    # Versuche ISO-Format zu parsen (YYYY-MM-DD)
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        timestamp = int(dt.timestamp())
        return str(timestamp)
    except ValueError:
        pass

    # Versuche andere Formate
    formats = ["%Y/%m/%d", "%d.%m.%Y", "%d-%m-%Y"]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            timestamp = int(dt.timestamp())
            return str(timestamp)
        except ValueError:
            continue

    # Wenn nichts funktioniert, gib Original zurück
    return date_str


def format_timestamp_to_date(value) -> str:
    """
    Wandelt Unix-Timestamps in lesbares Datum um

    Args:
        value: Unix Timestamp (int/str), Jahr (str), oder ISO Datum (str)

    Returns:
        Formatiertes Datum als "YYYY-MM-DD" oder Original-Wert
    """
    if not value:
        return ""

    value_str = str(value).strip()

    # Prüfen, ob es eine Zahl ist
    if value_str.isdigit():
        try:
            ts = int(value_str)
            # Einfache Prüfung: Ist die Zahl größer als 100.000.000?
            # Timestamp für das Jahr 2000 ist 946684800
            # ein Jahr wie "2004" ist viel kleiner
            if ts > 100000000:
                dt = datetime.fromtimestamp(ts)
                return dt.strftime("%Y-%m-%d")
        except (ValueError, OSError, OverflowError):
            pass  # Falls Fehler, gib Original zurück

    return value_str