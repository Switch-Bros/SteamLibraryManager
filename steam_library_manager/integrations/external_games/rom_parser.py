#
# steam_library_manager/integrations/external_games/rom_parser.py
# Scan ROM directories, pair with emulators, create Steam shortcuts
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path

from steam_library_manager.integrations.external_games.base_parser import BaseExternalParser
from steam_library_manager.integrations.external_games.emulator_config import (
    EMUDECK_ROM_DIRS,
    EMULATORS,
    ROM_SEARCH_PATHS,
    SYSTEM_EMULATORS,
    EmulatorDef,
)
from steam_library_manager.integrations.external_games.models import ExternalGame

__all__ = ["RomParser"]

logger = logging.getLogger("steamlibmgr.external_games.rom_parser")


class RomParser(BaseExternalParser):
    """Scan ROM directories and pair each ROM with its emulator as a Steam shortcut."""

    # System aliases - maps alternative directory names to canonical system IDs.
    # EmuDeck creates separate roms/gbc/ directories, but RetroArch (GB) handles both.
    _SYSTEM_ALIASES: dict[str, str] = {
        "gbc": "gb",
    }

    # Common AppImage search directories (ORDER = PRIORITY!)
    APPIMAGE_DIRS: tuple[str, ...] = (
        "~/.local/share/applications",
        "~/Applications",
        "~/apps",
        "~/AppImages",
        "/mnt/volume/Emulation/tools",
        "~/Emulation/tools",
        "~/Downloads",
    )

    # EmuDeck launcher directory
    EMUDECK_LAUNCHER_DIRS: tuple[str, ...] = (
        "/mnt/volume/Emulation/tools/launchers",
        "~/Emulation/tools/launchers",
    )

    def platform_name(self) -> str:
        return "Emulation (ROMs)"

    def is_available(self) -> bool:
        for path_str in ROM_SEARCH_PATHS:
            path = Path(path_str).expanduser()
            if path.is_dir():
                try:
                    if any(path.iterdir()):
                        return True
                except PermissionError:
                    continue
        return False

    def get_config_paths(self) -> list[Path]:
        found: list[Path] = []
        for path_str in ROM_SEARCH_PATHS:
            path = Path(path_str).expanduser()
            if path.is_dir():
                found.append(path)
        return found

    def read_games(self) -> list[ExternalGame]:
        """Scan all ROM directories and return one ExternalGame per ROM."""
        detected_emulators = self._detect_emulators()
        if not detected_emulators:
            logger.info("No emulators detected on system")
            return []

        rom_dirs = self._find_rom_directories()
        if not rom_dirs:
            logger.info("No ROM directories found")
            return []

        games: list[ExternalGame] = []

        for system_dir, system_name in rom_dirs:
            emulators_for_system = self._get_emulators_for_system(system_name, detected_emulators)
            if not emulators_for_system:
                logger.debug("No emulator for system: %s", system_name)
                continue

            emulator, exe_path = emulators_for_system[0]
            roms = self._scan_rom_files(system_dir, emulator.extensions)
            for rom_path in roms:
                game_name = self._extract_game_name(rom_path)
                launch_cmd = self._build_launch_command(emulator, exe_path, rom_path)

                games.append(
                    ExternalGame(
                        platform=f"Emulation ({emulator.system_display})",
                        platform_app_id=f"rom:{system_name}:{rom_path.name}",
                        name=game_name,
                        install_path=rom_path.parent,
                        executable=str(exe_path),
                        launch_command=launch_cmd,
                        platform_metadata=(
                            ("emulator", emulator.name),
                            ("system", system_name),
                            ("rom_file", rom_path.name),
                            ("rom_extension", rom_path.suffix.lower()),
                        ),
                    )
                )

        logger.info("Found %d ROMs across %d systems", len(games), len(rom_dirs))
        return games

    def _detect_emulators(self) -> dict[str, Path]:
        found: dict[str, Path] = {}

        for emu_def in EMULATORS:
            if emu_def.name in found:
                continue

            exe_path = self._find_emulator(emu_def)
            if exe_path:
                found[emu_def.name] = exe_path
                logger.debug("Found emulator %s at %s", emu_def.name, exe_path)

        return found

    def _find_emulator(self, emu: EmulatorDef) -> Path | None:
        """Find emulator executable: EmuDeck -> Flatpak -> PATH -> AppImage."""
        # EmuDeck launcher scripts
        if emu.emudeck_launcher:
            for launcher_dir in self.EMUDECK_LAUNCHER_DIRS:
                launcher = Path(launcher_dir).expanduser() / emu.emudeck_launcher
                if launcher.is_file() and launcher.stat().st_mode & 0o111:
                    return launcher

        # Flatpak
        if emu.flatpak_id:
            flatpak_check = shutil.which("flatpak")
            if flatpak_check:
                try:
                    result = subprocess.run(
                        ["flatpak", "info", emu.flatpak_id],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        return Path(f"/flatpak/{emu.flatpak_id}")
                except (subprocess.TimeoutExpired, OSError):
                    pass

        # System PATH
        for pattern in emu.exe_patterns:
            if "*" not in pattern:
                which_result = shutil.which(pattern)
                if which_result:
                    return Path(which_result)

        # AppImage in common locations
        for dir_str in self.APPIMAGE_DIRS:
            search_dir = Path(dir_str).expanduser()
            if not search_dir.is_dir():
                continue
            for pattern in emu.exe_patterns:
                if "*" in pattern:
                    matches = sorted(search_dir.glob(pattern), reverse=True)
                    if matches:
                        return matches[0]
                else:
                    exact = search_dir / pattern
                    if exact.is_file():
                        return exact

        return None

    def _find_rom_directories(self) -> list[tuple[Path, str]]:
        """Find ROM directories with their system names, deduplicated."""
        found: list[tuple[Path, str]] = []

        for base_str in ROM_SEARCH_PATHS:
            base = Path(base_str).expanduser()
            if not base.is_dir():
                continue

            for system_name, dir_name in EMUDECK_ROM_DIRS.items():
                system_dir = base / dir_name
                if system_dir.is_dir():
                    try:
                        if any(system_dir.iterdir()):
                            found.append((system_dir, system_name))
                    except PermissionError:
                        continue

        seen: set[str] = set()
        unique: list[tuple[Path, str]] = []
        for path, name in found:
            try:
                resolved = str(path.resolve())
            except OSError:
                resolved = str(path)
            if resolved not in seen:
                seen.add(resolved)
                unique.append((path, name))

        return unique

    @staticmethod
    def _get_emulators_for_system(
        system_name: str,
        detected: dict[str, Path],
    ) -> list[tuple[EmulatorDef, Path]]:
        """Get available emulators for a system, resolving aliases like gbc->gb."""
        effective_system = RomParser._SYSTEM_ALIASES.get(system_name, system_name)
        results: list[tuple[EmulatorDef, Path]] = []
        for emu_def in SYSTEM_EMULATORS.get(effective_system, []):
            if emu_def.name in detected:
                results.append((emu_def, detected[emu_def.name]))
        return results

    @staticmethod
    def _scan_rom_files(
        directory: Path,
        extensions: tuple[str, ...],
    ) -> list[Path]:
        """Non-recursive scan for ROM files matching the given extensions."""
        roms: list[Path] = []
        try:
            for entry in directory.iterdir():
                if entry.is_file() and entry.suffix.lower() in extensions:
                    roms.append(entry)
        except PermissionError:
            logger.warning("Cannot read directory: %s", directory)
        return sorted(roms, key=lambda p: p.name.lower())

    @staticmethod
    def _extract_game_name(rom_path: Path) -> str:
        """Extract clean game name from ROM filename, stripping tags and IDs."""
        name = rom_path.stem

        name = re.sub(r"\s*\[[0-9A-Fa-f]{16}\]", "", name)
        name = re.sub(r"\s*\[v\d+\]", "", name)
        name = re.sub(r"\s*\(v[\d.]+\)", "", name)
        name = re.sub(r"\s*\((USA|Europe|Japan|World|En|De|Fr|Es|It|Ko|Zh)\)", "", name)
        name = re.sub(
            r"\s*\((DLC|Update|NSP|XCI|CIA|Demo)\)",
            "",
            name,
            flags=re.IGNORECASE,
        )
        name = re.sub(r"\s*\[.*?\]\s*$", "", name)
        name = re.sub(r"\s*\(.*?\)\s*$", "", name)
        name = name.strip(" -_.")

        return name if name else rom_path.stem

    @staticmethod
    def _build_launch_command(
        emu: EmulatorDef,
        exe_path: Path,
        rom_path: Path,
    ) -> str:
        """Build the full launch command for a ROM."""
        exe_str = str(exe_path)

        # Flatpak sentinel path: /flatpak/<app_id>
        if exe_str.startswith("/flatpak/"):
            flatpak_id = exe_path.name
            parts = emu.launch_template.split('"{exe}"')
            if len(parts) == 2:
                args = parts[1].format(rom=str(rom_path))
                return f"flatpak run {flatpak_id}{args}"
            return f'flatpak run {flatpak_id} "{rom_path}"'

        return emu.launch_template.format(
            exe=exe_str,
            rom=str(rom_path),
        )
