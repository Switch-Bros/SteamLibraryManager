#
# steam_library_manager/integrations/external_games/emulator_parsers/_yuzu_qt_config.py
# Shared parsing for Yuzu-derived emulators (Eden, Citron, Azahar, Suyu)
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger("steamlibmgr.emulator_parsers.yuzu_qt")

__all__ = ["parse_yuzu_qt_gamedirs"]

# Yuzu-style INI uses double-backslash keys like "Paths\gamedirs\1\path"
# Qt's INI escaping mangles backslashes - actual file syntax is single backslash
_GAMEDIR_LINE = re.compile(r"^Paths\\gamedirs\\\d+\\path\s*=\s*(.+?)\s*$")
_GAMEDIR_DEFAULT = re.compile(r"^Paths\\gamedirs\\\d+\\path\\default\s*=\s*(.+?)\s*$")


def parse_yuzu_qt_gamedirs(config_path: Path) -> list[str]:
    """Reads game directories from a Yuzu-style qt-config.ini file.

    Looks for keys matching `Paths\\gamedirs\\<N>\\path` and ignores the
    `\\default` companion lines that Qt writes for every key.
    """
    if not config_path.is_file():
        return []

    dirs: list[str] = []
    try:
        with open(config_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip("\r\n")
                if _GAMEDIR_DEFAULT.match(line):
                    # the boolean "is default value" companion line; skip
                    continue
                m = _GAMEDIR_LINE.match(line)
                if not m:
                    continue
                val = m.group(1).strip()
                if not val:
                    continue
                # Qt INI sometimes wraps paths in @ByteArray() or quotes
                if val.startswith("@ByteArray(") and val.endswith(")"):
                    val = val[len("@ByteArray(") : -1]
                val = val.strip().strip('"')
                if not val:
                    continue
                # Skip Yuzu/Eden internal markers (SDMC, UserNAND, SysNAND, ...)
                if not (val.startswith("/") or val.startswith("~") or val.startswith("$")):
                    continue
                dirs.append(val)
    except OSError as exc:
        logger.warning("could not read %s: %s" % (config_path, exc))
        return []

    return dirs
