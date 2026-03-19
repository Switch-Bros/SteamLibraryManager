#
# steam_library_manager/integrations/external_games/base_parser.py
# ABC for all external game library parsers
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import sqlite3
from abc import ABC, abstractmethod

__all__ = ["BaseExternalParser"]

logger = logging.getLogger("steamlibmgr.external_games")


class BaseExternalParser(ABC):
    """Base for external game platform parsers.

    Provides path-detection and DB helpers.
    Subclasses implement platform-specific game reading.
    """

    @abstractmethod
    def platform_name(self):
        # human-readable name
        raise NotImplementedError

    @abstractmethod
    def is_available(self):
        # check if platform is installed
        raise NotImplementedError

    @abstractmethod
    def read_games(self):
        # return list[ExternalGame]
        raise NotImplementedError

    def get_config_paths(self):
        # override to provide native + flatpak paths
        return []

    def _find_config_file(self):
        # first existing config from get_config_paths()
        for p in self.get_config_paths():
            if p.exists():
                logger.debug("found %s config: %s" % (self.platform_name(), p))
                return p
        return None

    def _open_readonly_db(self, db_path):
        # open sqlite in read-only mode
        try:
            conn = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logger.warning("failed to open %s db: %s" % (self.platform_name(), e))
            return None
