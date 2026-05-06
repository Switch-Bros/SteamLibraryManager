#
# steam_library_manager/integrations/external_games/emulator_parsers/__init__.py
# Emulator config parser package - one parser per emulator
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

from steam_library_manager.integrations.external_games.emulator_parsers.azahar import AzaharParser
from steam_library_manager.integrations.external_games.emulator_parsers.cemu import CemuParser
from steam_library_manager.integrations.external_games.emulator_parsers.citron import CitronParser
from steam_library_manager.integrations.external_games.emulator_parsers.dolphin import DolphinParser
from steam_library_manager.integrations.external_games.emulator_parsers.dosbox import DOSBoxParser
from steam_library_manager.integrations.external_games.emulator_parsers.eden import EdenParser
from steam_library_manager.integrations.external_games.emulator_parsers.emudeck_hint import EmuDeckHintProvider
from steam_library_manager.integrations.external_games.emulator_parsers.melonds import MelonDSParser
from steam_library_manager.integrations.external_games.emulator_parsers.ppsspp import PPSSPPParser
from steam_library_manager.integrations.external_games.emulator_parsers.protocol import (
    EmulatorConfigParser,
    GameRef,
    InstalledEmulator,
)
from steam_library_manager.integrations.external_games.emulator_parsers.retroarch import RetroArchParser
from steam_library_manager.integrations.external_games.emulator_parsers.ryujinx import RyujinxParser

__all__ = [
    "AzaharParser",
    "CemuParser",
    "CitronParser",
    "DOSBoxParser",
    "DolphinParser",
    "EdenParser",
    "EmuDeckHintProvider",
    "EmulatorConfigParser",
    "GameRef",
    "InstalledEmulator",
    "MelonDSParser",
    "PPSSPPParser",
    "RetroArchParser",
    "RyujinxParser",
    "ALL_PARSERS",
]


def _build_parsers() -> list:
    return [
        EdenParser(),
        CitronParser(),
        RyujinxParser(),
        CemuParser(),
        DolphinParser(),
        AzaharParser(),
        RetroArchParser(),
        PPSSPPParser(),
        MelonDSParser(),
        DOSBoxParser(),
    ]


ALL_PARSERS = _build_parsers
