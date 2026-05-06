#
# steam_library_manager/services/shortcuts_importer.py
# Bridges shortcuts.vdf (Steam non-Steam game shortcuts) into SLM's main library.
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging

from steam_library_manager.core.game import Game
from steam_library_manager.core.shortcuts_manager import ShortcutsManager, SteamShortcut

__all__ = ["ShortcutsImporter"]

logger = logging.getLogger("steamlibmgr.shortcuts_importer")


class ShortcutsImporter:
    """Loads Steam shortcuts.vdf and exposes its entries as Game objects.

    Tags from shortcuts.vdf become categories on the Game so they show up
    in SLM's category tree alongside regular Steam games. AppIDs for
    shortcuts are stored as their signed-int32 form (negative numbers),
    matching shortcuts.vdf and giving us a unique key that does not
    collide with Steam's positive appids.
    """

    def __init__(self, shortcuts_manager: ShortcutsManager) -> None:
        self._mgr = shortcuts_manager

    def is_available(self) -> bool:
        return self._mgr.get_shortcuts_path().is_file()

    def read_games(self) -> list[Game]:
        try:
            shortcuts = self._mgr.read_shortcuts()
        except Exception:
            logger.exception("could not read shortcuts.vdf")
            return []

        games: list[Game] = []
        for sc in shortcuts:
            game = self._to_game(sc)
            if game is not None:
                games.append(game)
        logger.info("imported %d shortcuts" % len(games))
        return games

    @staticmethod
    def _to_game(sc: SteamShortcut) -> Game | None:
        if not sc.app_name:
            return None

        # tags is a dict like {"0": "Heroic (GOG)", "1": "Indie"} - flatten to list
        cats: list[str] = []
        if isinstance(sc.tags, dict):
            for key in sorted(sc.tags.keys(), key=_safe_int):
                val = sc.tags[key]
                if isinstance(val, str) and val.strip():
                    cats.append(val.strip())

        # Use the unsigned uint32 form as the canonical Game.app_id. Steam writes
        # cover filenames and cloud-storage collection entries under this form too,
        # so keeping a single key avoids constant signed/unsigned conversion.
        unsigned = sc.appid & 0xFFFFFFFF if sc.appid < 0 else sc.appid

        return Game(
            app_id=str(unsigned),
            name=sc.app_name,
            categories=cats,
            developer="",
            publisher="",
            app_type="game",
            is_shortcut=True,
            shortcut_exe=sc.exe or "",
            shortcut_start_dir=sc.start_dir or "",
            shortcut_launch_options=sc.launch_options or "",
            shortcut_icon=sc.icon or "",
        )


def _safe_int(s: str) -> int:
    try:
        return int(s)
    except (ValueError, TypeError):
        return 0
