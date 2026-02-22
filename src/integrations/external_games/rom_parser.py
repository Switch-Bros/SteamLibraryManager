"""Parser for ROM files paired with detected emulators.

Scans ROM directories, matches files to emulators by extension,
and creates ExternalGame objects for each individual ROM.
Each ROM becomes its own Steam shortcut — not the emulator app.
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from pathlib import Path

from src.integrations.external_games.base_parser import BaseExternalParser
from src.integrations.external_games.emulator_config import (
    EMUDECK_ROM_DIRS,
    EMULATORS,
    ROM_SEARCH_PATHS,
    SYSTEM_EMULATORS,
    EmulatorDef,
)
from src.integrations.external_games.models import ExternalGame

__all__ = ["RomParser"]

logger = logging.getLogger("steamlibmgr.external_games.rom_parser")


class RomParser(BaseExternalParser):
    """Scan ROM directories and pair with detected emulators.

    Creates one ExternalGame per ROM file. Each ROM gets its own
    Steam shortcut with the emulator as executable and ROM as argument.

    Detection strategy (priority order):
    1. EmuDeck launcher scripts (/mnt/volume/Emulation/tools/launchers/)
    2. Flatpak installations (flatpak info)
    3. System PATH (shutil.which)
    4. Common AppImage locations (~/.local/share/applications/, ~/Applications/)
    """

    # System aliases — maps alternative directory names to canonical system IDs.
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
        """Return platform name.

        Returns:
            Platform identifier string.
        """
        return "Emulation (ROMs)"

    def is_available(self) -> bool:
        """Check if any ROM directory exists with files.

        Returns:
            True if at least one ROM directory exists and is non-empty.
        """
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
        """Return found ROM directories.

        Returns:
            List of existing ROM directory paths.
        """
        found: list[Path] = []
        for path_str in ROM_SEARCH_PATHS:
            path = Path(path_str).expanduser()
            if path.is_dir():
                found.append(path)
        return found

    def read_games(self) -> list[ExternalGame]:
        """Scan all ROM directories and pair ROMs with emulators.

        Returns:
            List of ExternalGame objects, one per ROM file.
        """
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

            # Use first available emulator (priority order)
            emulator, exe_path = emulators_for_system[0]

            # Scan ROM files
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
        """Detect installed emulators on the system.

        Returns:
            Dict mapping emulator name to executable path.
        """
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
        """Find an emulator executable on the system.

        Priority: EmuDeck launcher -> Flatpak -> PATH -> AppImage.

        Args:
            emu: Emulator definition to search for.

        Returns:
            Path to executable, or None if not found.
        """
        # 1. EmuDeck launcher scripts
        if emu.emudeck_launcher:
            for launcher_dir in self.EMUDECK_LAUNCHER_DIRS:
                launcher = Path(launcher_dir).expanduser() / emu.emudeck_launcher
                if launcher.is_file() and launcher.stat().st_mode & 0o111:
                    return launcher

        # 2. Flatpak
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
                        # Sentinel path — _build_launch_command checks this
                        return Path(f"/flatpak/{emu.flatpak_id}")
                except (subprocess.TimeoutExpired, OSError):
                    pass

        # 3. System PATH
        for pattern in emu.exe_patterns:
            if "*" not in pattern:
                which_result = shutil.which(pattern)
                if which_result:
                    return Path(which_result)

        # 4. AppImage in common locations (FIRST MATCH WINS)
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
        """Find ROM directories with their system names.

        Returns:
            List of (directory_path, system_name) tuples, deduplicated.
        """
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

        # Deduplicate (same physical directory via different base paths)
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
        """Get available emulators for a specific system.

        Resolves system aliases (e.g. "gbc" -> "gb") before lookup,
        so ROMs in EmuDeck's roms/gbc/ directory find the GB emulator.

        Args:
            system_name: System ID (e.g. "switch", "gbc").
            detected: Dict of detected emulator name to path.

        Returns:
            List of (EmulatorDef, exe_path) tuples, ordered by priority.
        """
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
        """Scan a directory for ROM files with given extensions.

        Non-recursive scan (EmuDeck puts ROMs directly in system dirs).

        Args:
            directory: Directory to scan.
            extensions: Tuple of supported extensions (e.g. (".nsp", ".xci")).

        Returns:
            Sorted list of ROM file paths.
        """
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
        """Extract clean game name from ROM filename.

        Handles common ROM naming patterns:
        - "Metroid Dread.nsp" -> "Metroid Dread"
        - "Super Mario Odyssey [01006A800016E000][v0].nsp" -> "Super Mario Odyssey"
        - "Zelda - BOTW (USA) (v1.6).xci" -> "Zelda - BOTW"

        Args:
            rom_path: Path to ROM file.

        Returns:
            Cleaned game name.
        """
        name = rom_path.stem

        # Remove title IDs in brackets: [01006A800016E000]
        name = re.sub(r"\s*\[[0-9A-Fa-f]{16}\]", "", name)

        # Remove version tags: [v0], [v131072], (v1.6)
        name = re.sub(r"\s*\[v\d+\]", "", name)
        name = re.sub(r"\s*\(v[\d.]+\)", "", name)

        # Remove region codes: (USA), (Europe), (Japan), (World)
        name = re.sub(r"\s*\((USA|Europe|Japan|World|En|De|Fr|Es|It|Ko|Zh)\)", "", name)

        # Remove other common tags: (DLC), (Update), (NSP), (XCI)
        name = re.sub(
            r"\s*\((DLC|Update|NSP|XCI|CIA|Demo)\)",
            "",
            name,
            flags=re.IGNORECASE,
        )

        # Remove anything in remaining brackets at end
        name = re.sub(r"\s*\[.*?\]\s*$", "", name)
        name = re.sub(r"\s*\(.*?\)\s*$", "", name)

        # Clean up whitespace
        name = name.strip(" -_.")

        return name if name else rom_path.stem

    @staticmethod
    def _build_launch_command(
        emu: EmulatorDef,
        exe_path: Path,
        rom_path: Path,
    ) -> str:
        """Build the full launch command for a ROM.

        Args:
            emu: Emulator definition with launch template.
            exe_path: Path to emulator executable.
            rom_path: Path to ROM file.

        Returns:
            Complete launch command string.
        """
        exe_str = str(exe_path)

        # Flatpak sentinel path handling: /flatpak/<app_id>
        if exe_str.startswith("/flatpak/"):
            flatpak_id = exe_path.name
            # Split template on "{exe}" to extract the argument pattern
            parts = emu.launch_template.split('"{exe}"')
            if len(parts) == 2:
                args = parts[1].format(rom=str(rom_path))
                return f"flatpak run {flatpak_id}{args}"
            # Fallback: no special args in template
            return f'flatpak run {flatpak_id} "{rom_path}"'

        # Normal AppImage/binary
        return emu.launch_template.format(
            exe=exe_str,
            rom=str(rom_path),
        )
