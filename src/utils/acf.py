# src/utils/acf.py

"""
Parser for Steam's ACF (KeyValues Text Format).

This module provides functions to parse and serialize Steam's ACF file format,
which is a simple key-value text format used for configuration files like
appmanifest_*.acf.
"""

from __future__ import annotations

from typing import Any

__all__ = ("load", "loads", "dump", "dumps")

SECTION_START = "{"
SECTION_END = "}"


def loads(data: str, wrapper=dict) -> dict[str, Any]:
    """
    Parses an ACF string into a dictionary.

    Args:
        data (str): The ACF-formatted string to parse.
        wrapper (type): The dictionary type to use for parsed data. Defaults to dict.

    Returns:
        dict: A nested dictionary representing the parsed ACF data.

    Raises:
        TypeError: If data is not a string.
    """
    if not isinstance(data, str):
        raise TypeError(f"Can only load str, got {type(data).__name__}")

    parsed = wrapper()
    current_section = parsed
    sections = []
    lines = (line.strip() for line in data.splitlines() if line.strip())

    for line in lines:
        if line == SECTION_START:
            current_section = _prepare_subsection(parsed, sections, wrapper)
            continue
        if line == SECTION_END:
            if sections:
                sections.pop()
            continue

        try:
            # Try to split key-value
            parts = line.split(None, 1)
            if len(parts) == 2:
                key = parts[0].strip('"')
                value = parts[1].strip('"')
                current_section[key] = value
            else:
                # It's a new section
                sections.append(line.strip('"'))
        except ValueError:
            continue
    return parsed


def load(fp, wrapper=dict) -> dict[str, Any]:
    """
    Parses an ACF file into a dictionary.

    Args:
        fp: A file-like object opened in text mode.
        wrapper (type): The dictionary type to use for parsed data. Defaults to dict.

    Returns:
        dict: A nested dictionary representing the parsed ACF data.
    """
    return loads(fp.read(), wrapper=wrapper)


def dumps(obj: dict, level: int = 0) -> str:
    """
    Serializes a dictionary into an ACF-formatted string.

    Args:
        obj (dict): The dictionary to serialize.
        level (int): The current indentation level (used for recursion). Defaults to 0.

    Returns:
        str: The ACF-formatted string.
    """
    lines = []
    indent = "\t" * level
    for key, value in obj.items():
        if isinstance(value, dict):
            lines.append(f'{indent}"{key}"\n{indent}{{')
            lines.append(dumps(value, level + 1).rstrip())
            lines.append(f"{indent}}}")
        else:
            lines.append(f'{indent}"{key}"\t\t"{value}"')
    return "\n".join(lines) + "\n"


def dump(obj: dict, fp):
    """
    Serializes a dictionary into an ACF file.

    Args:
        obj (dict): The dictionary to serialize.
        fp: A file-like object opened in text mode for writing.
    """
    fp.write(dumps(obj))


def _prepare_subsection(data, sections, wrapper) -> dict[str, Any]:
    """
    Prepares a subsection for nested data.

    This is a helper function used during parsing to navigate nested sections.

    Args:
        data (dict): The root dictionary.
        sections (list): A list of section names representing the current path.
        wrapper (type): The dictionary type to use for new sections.

    Returns:
        dict: The current subsection dictionary.
    """
    current = data
    for section in sections:
        if section not in current:
            current[section] = wrapper()
        current = current[section]
    return current
