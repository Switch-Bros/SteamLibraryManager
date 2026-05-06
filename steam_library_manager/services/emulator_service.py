#
# steam_library_manager/services/emulator_service.py
# Orchestrator for emulator detection, game discovery, Steam export pairing
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from steam_library_manager.integrations.external_games.emulator_config import (
    EMULATORS,
    EmulatorDef,
)
from steam_library_manager.integrations.external_games.emulator_parsers import (
    ALL_PARSERS,
    EmuDeckHintProvider,
)
from steam_library_manager.integrations.external_games.emulator_parsers.protocol import (
    EmulatorConfigParser,
    InstalledEmulator,
)

__all__ = [
    "EmulatorService",
    "DiscoveryResult",
    "RomConflict",
    "GameForExport",
]

logger = logging.getLogger("steamlibmgr.emulator_service")

# regex patterns for stripping ROM filename junk
_RE_TITLE_ID = re.compile(r"\s*\[[0-9A-Fa-f]{16}\]")
_RE_VER_BRACKET = re.compile(r"\s*\[v\d+\]")
_RE_VER_PAREN = re.compile(r"\s*\(v[\d.]+\)")
_RE_REGION = re.compile(r"\s*\((USA|Europe|Japan|World|En|De|Fr|Es|It|Ko|Zh)\)")
_RE_TAGS = re.compile(r"\s*\((DLC|Update|NSP|XCI|CIA|Demo)\)", re.IGNORECASE)
_RE_TRAIL_BRACKET = re.compile(r"\s*\[.*?\]\s*$")
_RE_TRAIL_PAREN = re.compile(r"\s*\(.*?\)\s*$")
_RE_EXTRACT_VERSION = re.compile(r"\[v(\d+)\]")

# Systems where Title-Updates ship as separate ROM files alongside the base game
# (Nintendo distribution model). For these we deduplicate on (system, game_name)
# and keep the file with the lowest version number = the base game.
# Other systems keep every file because identical extracted names there usually
# mean genuinely different games (regional variants, romhacks, etc).
_NINTENDO_TITLE_SYSTEMS = frozenset({"switch", "wiiu", "3ds"})


@dataclass(frozen=True)
class RomConflict:
    """Same ROM file is reachable through multiple emulators."""

    rom_path: str
    game_name: str
    system: str
    emulators: tuple[str, ...]


@dataclass
class DiscoveryResult:
    """Outcome of a single discover_libraries() pass."""

    emulators_found: int = 0
    roms_found: int = 0
    systems: list[str] = field(default_factory=list)
    conflicts: list[RomConflict] = field(default_factory=list)


@dataclass(frozen=True)
class GameForExport:
    """ROM ready to be exported as a Steam non-Steam shortcut."""

    name: str
    rom_path: str
    system: str
    emulator_name: str
    launch_command: str
    system_display: str


class EmulatorService:
    """Detects emulators, discovers their game libraries, builds Steam launch commands."""

    def __init__(
        self,
        database,
        parsers: list[EmulatorConfigParser] | None = None,
        emudeck_hint: EmuDeckHintProvider | None = None,
    ) -> None:
        self._db = database
        self._parsers: list[EmulatorConfigParser] = parsers if parsers is not None else ALL_PARSERS()
        self._emudeck = emudeck_hint if emudeck_hint is not None else EmuDeckHintProvider()
        # cache of name -> EmulatorDef from emulator_config.py for launch templates
        self._defs_by_name = self._build_defs_index()

    # ---- public API ----

    def detect_installed_emulators(self) -> list[InstalledEmulator]:
        installed: list[InstalledEmulator] = []
        for parser in self._parsers:
            if not parser.is_installed():
                continue
            ie = self._build_installed(parser)
            if ie is not None:
                installed.append(ie)
        return installed

    def discover_libraries(self) -> DiscoveryResult:
        result = DiscoveryResult()
        seen_systems: set[str] = set()

        # path -> list of parser names that found it (for conflict detection)
        rom_to_emulators: dict[str, list[tuple[str, str, str]]] = {}

        for parser in self._parsers:
            if not parser.is_installed():
                continue

            settings = self._db.get_emulator_settings(parser.name) or {}
            if settings.get("enabled") is False:
                continue

            result.emulators_found += 1

            # 1) games the emulator already knows about (RetroArch playlists)
            for ref in parser.get_known_games():
                self._record_rom(rom_to_emulators, parser, ref.system, ref.path, ref.name)
                seen_systems.add(ref.system)

            # 2) directories from the emulator's own config + user custom dirs
            game_dirs = list(parser.get_game_dirs())
            game_dirs.extend(Path(d).expanduser() for d in settings.get("custom_game_dirs", []))

            # 3) EmuDeck hint as fallback if parser has no dirs and supports a single system
            if not game_dirs and self._emudeck.is_available():
                for sys_id in parser.systems:
                    hint = self._emudeck.get_rom_dir(sys_id)
                    if hint:
                        game_dirs.append(hint)

            # 4) scan dirs for ROMs matching emulator's extensions
            for emu_def in self._defs_for_parser(parser.name):
                for d in game_dirs:
                    d_path = Path(d).expanduser()
                    if not d_path.is_dir():
                        continue
                    # if this dir is system-specific (e.g. /roms/switch), only that system applies
                    sys_id = self._infer_system(d_path, emu_def.system, parser.systems)
                    if sys_id != emu_def.system:
                        continue
                    for rom in self._scan_rom_files(d_path, emu_def.extensions):
                        name = self._extract_game_name(rom)
                        self._record_rom(rom_to_emulators, parser, sys_id, rom, name)
                        seen_systems.add(sys_id)

        # detect conflicts and pick winner per ROM
        winners: list[tuple[str, str, str, str]] = []  # (emulator, system, rom_path, name)
        priority = self._priority_order()
        for rom_path, hits in rom_to_emulators.items():
            if len(hits) > 1:
                emu_names = tuple(h[0] for h in hits)
                result.conflicts.append(
                    RomConflict(
                        rom_path=rom_path,
                        game_name=hits[0][2],
                        system=hits[0][1],
                        emulators=emu_names,
                    )
                )
            winner = self._pick_winner(hits, priority)
            winners.append((winner[0], winner[1], rom_path, winner[2]))

        # collapse Nintendo title-update / DLC duplicates to the base game
        winners, dropped_rom_paths = self._collapse_nintendo_updates(winners)

        # bulk-write to DB
        self._db.bulk_upsert_emulator_games(winners)

        # remove stale title-update entries that earlier scans had cached
        # (only when their base game is still in the new scan, so we never
        # orphan a user who only has the update file on disk)
        self._purge_stale_updates(dropped_rom_paths)

        result.roms_found = len(winners)
        result.systems = sorted(seen_systems)
        logger.info(
            "discover_libraries: %d emulators, %d ROMs, %d systems, %d conflicts"
            % (result.emulators_found, result.roms_found, len(result.systems), len(result.conflicts))
        )
        return result

    def get_games_for_steam_export(self, only_unexported: bool = True) -> list[GameForExport]:
        rows = self._db.get_emulator_games()
        out: list[GameForExport] = []
        for r in rows:
            if only_unexported and r["added_to_steam"]:
                continue
            emu = r["emulator_name"]
            sys_id = r["system"]
            # honor user's default_for_system override
            user_default = self._db.get_default_emulator_for_system(sys_id)
            effective_emu = user_default if user_default else emu

            cmd = self.build_launch_command(r["rom_path"], effective_emu, sys_id)
            if not cmd:
                continue
            emu_def = self._lookup_def(effective_emu, sys_id)
            display = emu_def.system_display if emu_def else sys_id
            out.append(
                GameForExport(
                    name=r["game_name"],
                    rom_path=r["rom_path"],
                    system=sys_id,
                    emulator_name=effective_emu,
                    launch_command=cmd,
                    system_display=display,
                )
            )
        return out

    def set_default_emulator_for_system(self, system: str, emulator_name: str) -> None:
        self._db.set_default_emulator_for_system(system, emulator_name)

    def add_user_game_dir(self, emulator_name: str, path: Path) -> None:
        self._db.add_custom_game_dir(emulator_name, str(path))

    def remove_user_game_dir(self, emulator_name: str, path: Path) -> None:
        self._db.remove_custom_game_dir(emulator_name, str(path))

    def enable_emulator(self, emulator_name: str) -> None:
        self._db.set_emulator_enabled(emulator_name, True)

    def disable_emulator(self, emulator_name: str) -> None:
        self._db.set_emulator_enabled(emulator_name, False)

    def set_executable_override(self, emulator_name: str, path: str) -> None:
        self._db.set_executable_override(emulator_name, path)

    def build_launch_command(self, rom_path: str, emulator_name: str, system: str) -> str:
        emu_def = self._lookup_def(emulator_name, system)
        if not emu_def:
            return ""
        exe = self._resolve_executable(emulator_name)
        if not exe:
            return ""
        if str(exe).startswith("/flatpak/"):
            flatpak_id = exe.name
            args_part = emu_def.launch_template.split('"{exe}"', 1)
            if len(args_part) == 2:
                args = args_part[1].format(rom=rom_path)
                return "flatpak run %s%s" % (flatpak_id, args)
            return 'flatpak run %s "%s"' % (flatpak_id, rom_path)
        return emu_def.launch_template.format(exe=str(exe), rom=rom_path)

    # ---- internal helpers ----

    @staticmethod
    def _build_defs_index() -> dict[tuple[str, str], EmulatorDef]:
        # (parser_name, system) -> EmulatorDef
        # Maps every entry in EMULATORS, with the parser_name being the
        # un-suffixed form (e.g. "Dolphin (GC)" -> "Dolphin", "RetroArch (N64)" -> "RetroArch")
        index: dict[tuple[str, str], EmulatorDef] = {}
        for d in EMULATORS:
            base_name = d.name.split(" (")[0]
            index[(base_name, d.system)] = d
            # also map by full name for backward compatibility
            index[(d.name, d.system)] = d
        return index

    def _defs_for_parser(self, parser_name: str) -> list[EmulatorDef]:
        return [d for (n, _s), d in self._defs_by_name.items() if n == parser_name]

    def _lookup_def(self, parser_name: str, system: str) -> EmulatorDef | None:
        return self._defs_by_name.get((parser_name, system))

    @staticmethod
    def _priority_order() -> dict[str, int]:
        # earlier entries in EMULATORS = higher priority
        order: dict[str, int] = {}
        for i, d in enumerate(EMULATORS):
            base = d.name.split(" (")[0]
            if base not in order:
                order[base] = i
        return order

    def _pick_winner(
        self,
        hits: list[tuple[str, str, str]],
        priority: dict[str, int],
    ) -> tuple[str, str, str]:
        # honor user default_for_system override first
        sys_id = hits[0][1]
        user_default = self._db.get_default_emulator_for_system(sys_id)
        if user_default:
            for h in hits:
                if h[0] == user_default:
                    return h
        # fall back to EMULATORS priority order
        return min(hits, key=lambda h: priority.get(h[0], 9999))

    @staticmethod
    def _record_rom(
        store: dict[str, list[tuple[str, str, str]]],
        parser: EmulatorConfigParser,
        system: str,
        rom_path: Path,
        name: str,
    ) -> None:
        key = str(rom_path)
        bucket = store.setdefault(key, [])
        # avoid duplicates from the same parser
        if any(h[0] == parser.name for h in bucket):
            return
        bucket.append((parser.name, system, name))

    @staticmethod
    def _infer_system(directory: Path, default_system: str, supported: tuple[str, ...]) -> str:
        # if the directory name matches a supported system id, use that;
        # otherwise fall back to the emulator's default system
        leaf = directory.name.lower()
        if leaf in supported:
            return leaf
        if leaf == "n3ds" and "3ds" in supported:
            return "3ds"
        if leaf == "ps1" and "psx" in supported:
            return "psx"
        return default_system

    @staticmethod
    def _scan_rom_files(d: Path, exts: tuple[str, ...]) -> list[Path]:
        roms: list[Path] = []
        try:
            for entry in d.iterdir():
                if entry.is_file() and entry.suffix.lower() in exts:
                    roms.append(entry)
        except (PermissionError, OSError):
            logger.warning("cannot read: %s" % d)
        return sorted(roms, key=lambda p: p.name.lower())

    @staticmethod
    def _collapse_nintendo_updates(
        winners: list[tuple[str, str, str, str]],
    ) -> tuple[list[tuple[str, str, str, str]], list[str]]:
        """For Nintendo systems, collapse `Game [v0].nsp` + `Game [v327680].nsp`
        into the single base entry. Title updates are separate files but are
        loaded automatically by the emulator alongside the base game, so a
        second Steam shortcut would be useless or broken.

        Returns (kept_winners, dropped_rom_paths) so callers can remove stale
        cache entries from previous scans.
        """
        # bucket: (system, game_name) -> list[(version, entry)]
        buckets: dict[tuple[str, str], list[tuple[int, tuple[str, str, str, str]]]] = {}
        passthrough: list[tuple[str, str, str, str]] = []

        for entry in winners:
            _emu, system, rom_path, name = entry
            if system not in _NINTENDO_TITLE_SYSTEMS:
                passthrough.append(entry)
                continue
            ver = EmulatorService._extract_version_number(rom_path)
            buckets.setdefault((system, name), []).append((ver, entry))

        kept: list[tuple[str, str, str, str]] = []
        dropped: list[str] = []
        for items in buckets.values():
            # lowest version = base game; updates have higher numbers
            items.sort(key=lambda x: x[0])
            kept.append(items[0][1])
            for _ver, losing_entry in items[1:]:
                dropped.append(losing_entry[2])  # rom_path
        return passthrough + kept, dropped

    def _purge_stale_updates(self, rom_paths: list[str]) -> None:
        # delete cache rows for collapsed update files. Direct DELETE is fine -
        # if the user re-scans after removing the base game, the update would
        # be re-added as its own row by the next discover pass.
        if not rom_paths:
            return
        for rp in rom_paths:
            try:
                self._db.conn.execute("DELETE FROM emulator_games WHERE rom_path = ?", (rp,))
            except Exception:
                logger.exception("failed to purge stale update entry: %s" % rp)
        self._db.conn.commit()

    @staticmethod
    def _extract_version_number(rom_path: str) -> int:
        m = _RE_EXTRACT_VERSION.search(rom_path)
        return int(m.group(1)) if m else 0

    @staticmethod
    def _extract_game_name(rom_path: Path) -> str:
        name = rom_path.stem
        for pat in (
            _RE_TITLE_ID,
            _RE_VER_BRACKET,
            _RE_VER_PAREN,
            _RE_REGION,
            _RE_TAGS,
            _RE_TRAIL_BRACKET,
            _RE_TRAIL_PAREN,
        ):
            name = pat.sub("", name)
        name = name.strip(" -_.")
        return name if name else rom_path.stem

    def _build_installed(self, parser: EmulatorConfigParser) -> InstalledEmulator | None:
        exe = self._resolve_executable(parser.name) or parser.get_executable()
        if exe is None:
            # parser is "installed" (config exists) but no binary - record placeholder
            exe = Path("/missing/%s" % parser.name)
        if str(exe).startswith("/flatpak/"):
            source = "flatpak"
        elif str(exe).startswith("/missing/"):
            source = "config_only"
        elif "AppImage" in exe.name:
            source = "appimage"
        elif str(exe) == self._user_override(parser.name):
            source = "user_override"
        else:
            source = "system"
        return InstalledEmulator(
            name=parser.name,
            systems=parser.systems,
            executable=exe,
            source=source,
            game_dirs=tuple(parser.get_game_dirs()),
        )

    def _resolve_executable(self, emulator_name: str) -> Path | None:
        # priority: user override -> parser detection
        override = self._user_override(emulator_name)
        if override:
            p = Path(override)
            if p.is_file() or str(p).startswith("/flatpak/"):
                return p
        for parser in self._parsers:
            if parser.name == emulator_name:
                return parser.get_executable()
        return None

    def _user_override(self, emulator_name: str) -> str:
        s = self._db.get_emulator_settings(emulator_name)
        return s["executable_override"] if s else ""
