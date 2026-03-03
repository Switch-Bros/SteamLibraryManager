"""Emulator definitions and ROM directory configuration.

Provides frozen dataclasses and registry constants for all supported
emulators and ROM search paths. Used by RomParser to detect installed
emulators and locate ROM files.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

__all__ = [
    "EmulatorDef",
    "EMUDECK_ROM_DIRS",
    "EMULATORS",
    "ROM_SEARCH_PATHS",
    "SYSTEM_EMULATORS",
    "SystemName",
]

SystemName: TypeAlias = str


@dataclass(frozen=True)
class EmulatorDef:
    """Definition of a supported emulator.

    Args:
        name: Human-readable emulator name (e.g. "Eden").
        system: Console system ID (e.g. "switch").
        system_display: Display name for collections (e.g. "Nintendo Switch").
        extensions: Supported ROM file extensions.
        exe_patterns: Glob patterns to find the emulator executable.
        flatpak_id: Flatpak app ID if available.
        launch_template: Command template. {exe} = emulator, {rom} = ROM path.
        emudeck_launcher: EmuDeck launcher script name (if applicable).
    """

    name: str
    system: SystemName
    system_display: str
    extensions: tuple[str, ...]
    exe_patterns: tuple[str, ...]
    flatpak_id: str = ""
    launch_template: str = '"{exe}" "{rom}"'
    emudeck_launcher: str = ""


# All supported emulators with detection patterns
EMULATORS: tuple[EmulatorDef, ...] = (
    # --- Nintendo Switch ---
    EmulatorDef(
        name="Eden",
        system="switch",
        system_display="Nintendo Switch",
        extensions=(".nsp", ".xci", ".nca"),
        exe_patterns=(
            "Eden.AppImage",
            "eden.AppImage",
            "Eden-Linux-*.AppImage",
            "eden.sh",
        ),
        launch_template='"{exe}" "{rom}"',
        emudeck_launcher="eden.sh",
    ),
    EmulatorDef(
        name="Citron",
        system="switch",
        system_display="Nintendo Switch",
        extensions=(".nsp", ".xci", ".nca"),
        exe_patterns=(
            # Citron is discontinued (Feb 2026, internal drama) but still
            # works if installed. Detect for existing installations.
            "Citron.AppImage",
            "citron.AppImage",
            "citron-*-linux-*.AppImage",
            "Citron_stable_*_linux.AppImage",
            "Citron-*-Linux-*.AppImage",
            "citron",
        ),
        launch_template='"{exe}" "{rom}"',
    ),
    EmulatorDef(
        name="Ryujinx",
        system="switch",
        system_display="Nintendo Switch",
        extensions=(".nsp", ".xci", ".nca"),
        exe_patterns=(
            "Ryujinx.AppImage",
            "ryujinx.sh",
            "Ryujinx",
        ),
        flatpak_id="org.ryujinx.Ryujinx",
        launch_template='"{exe}" "{rom}"',
        emudeck_launcher="ryujinx.sh",
    ),
    EmulatorDef(
        name="Yuzu",
        system="switch",
        system_display="Nintendo Switch",
        extensions=(".nsp", ".xci", ".nca"),
        exe_patterns=(
            # Yuzu is unmaintained (DMCA 2024) but still works if installed.
            "yuzu.AppImage",
            "yuzu",
        ),
        launch_template='"{exe}" "{rom}"',
        emudeck_launcher="yuzu.sh",
    ),
    # --- Nintendo Wii U ---
    EmulatorDef(
        name="Cemu",
        system="wiiu",
        system_display="Nintendo Wii U",
        extensions=(".wud", ".wux", ".rpx", ".wua"),
        exe_patterns=(
            "Cemu.AppImage",
            "cemu.sh",
            "Cemu",
        ),
        launch_template='"{exe}" -g "{rom}"',
        emudeck_launcher="cemu.sh",
    ),
    # --- Nintendo 3DS ---
    EmulatorDef(
        name="Azahar",
        system="3ds",
        system_display="Nintendo 3DS",
        extensions=(".3ds", ".cia", ".cxi", ".app"),
        exe_patterns=(
            "Azahar.AppImage",
            "azahar.sh",
        ),
        launch_template='"{exe}" "{rom}"',
        emudeck_launcher="azahar.sh",
    ),
    # --- Nintendo DS ---
    EmulatorDef(
        name="melonDS",
        system="nds",
        system_display="Nintendo DS",
        extensions=(".nds", ".dsi"),
        exe_patterns=("melonDS",),
        flatpak_id="net.kuribo64.melonDS",
        launch_template='"{exe}" "{rom}"',
    ),
    # --- Nintendo GameCube / Wii ---
    # Separate entries with UNIQUE names because _detect_emulators()
    # deduplicates on emu_def.name.
    EmulatorDef(
        name="Dolphin (GC)",
        system="gc",
        system_display="Nintendo GameCube",
        extensions=(".iso", ".gcz", ".rvz", ".gcm", ".ciso"),
        exe_patterns=("dolphin-emu",),
        flatpak_id="org.DolphinEmu.dolphin-emu",
        launch_template='"{exe}" --exec="{rom}"',
    ),
    EmulatorDef(
        name="Dolphin (Wii)",
        system="wii",
        system_display="Nintendo Wii",
        extensions=(".iso", ".wbfs", ".rvz", ".wad", ".ciso"),
        exe_patterns=("dolphin-emu",),
        flatpak_id="org.DolphinEmu.dolphin-emu",
        launch_template='"{exe}" --exec="{rom}"',
    ),
    # --- Nintendo N64 ---
    EmulatorDef(
        name="RetroArch (N64)",
        system="n64",
        system_display="Nintendo 64",
        extensions=(".z64", ".n64", ".v64"),
        exe_patterns=("retroarch",),
        flatpak_id="org.libretro.RetroArch",
        launch_template='"{exe}" -L mupen64plus_next_libretro "{rom}"',
    ),
    # --- Nintendo SNES ---
    EmulatorDef(
        name="RetroArch (SNES)",
        system="snes",
        system_display="Super Nintendo",
        extensions=(".sfc", ".smc", ".fig"),
        exe_patterns=("retroarch",),
        flatpak_id="org.libretro.RetroArch",
        launch_template='"{exe}" -L snes9x_libretro "{rom}"',
    ),
    # --- Nintendo NES ---
    EmulatorDef(
        name="RetroArch (NES)",
        system="nes",
        system_display="Nintendo Entertainment System",
        extensions=(".nes", ".unf", ".fds"),
        exe_patterns=("retroarch",),
        flatpak_id="org.libretro.RetroArch",
        launch_template='"{exe}" -L nestopia_libretro "{rom}"',
    ),
    # --- Nintendo Game Boy / GBA ---
    EmulatorDef(
        name="RetroArch (GBA)",
        system="gba",
        system_display="Game Boy Advance",
        extensions=(".gba",),
        exe_patterns=("retroarch",),
        flatpak_id="org.libretro.RetroArch",
        launch_template='"{exe}" -L mgba_libretro "{rom}"',
    ),
    EmulatorDef(
        name="RetroArch (GB)",
        system="gb",
        system_display="Game Boy",
        extensions=(".gb", ".gbc"),
        exe_patterns=("retroarch",),
        flatpak_id="org.libretro.RetroArch",
        launch_template='"{exe}" -L gambatte_libretro "{rom}"',
    ),
    # --- Sony PSP ---
    EmulatorDef(
        name="PPSSPP",
        system="psp",
        system_display="PlayStation Portable",
        extensions=(".iso", ".cso", ".pbp"),
        exe_patterns=("PPSSPPSDL", "ppsspp"),
        flatpak_id="org.ppsspp.PPSSPP",
        launch_template='"{exe}" "{rom}"',
    ),
    # --- DOS ---
    EmulatorDef(
        name="DOSBox",
        system="dos",
        system_display="MS-DOS",
        extensions=(".exe", ".com", ".bat"),
        exe_patterns=("dosbox",),
        launch_template='"{exe}" "{rom}"',
    ),
    # ScummVM is intentionally excluded — it uses game IDs, not ROM files.
    # Needs a completely different parser approach in a future task.
)

# Build lookup: system -> list of emulators (priority order)
SYSTEM_EMULATORS: dict[str, list[EmulatorDef]] = {}
for _emu in EMULATORS:
    SYSTEM_EMULATORS.setdefault(_emu.system, []).append(_emu)


# Standard ROM directories (in priority order)
ROM_SEARCH_PATHS: tuple[str, ...] = (
    "~/Emulation/roms",
    "/mnt/volume/Emulation/roms",
    "~/.config/retroarch/roms",
    "~/Games/roms",
    "~/ROMs",
    "~/roms",
)

# EmuDeck standard subdirectory names per system
EMUDECK_ROM_DIRS: dict[str, str] = {
    "switch": "switch",
    "wiiu": "wiiu",
    "3ds": "3ds",
    "nds": "nds",
    "gc": "gc",
    "wii": "wii",
    "n64": "n64",
    "snes": "snes",
    "nes": "nes",
    "gba": "gba",
    "gb": "gb",
    "gbc": "gbc",
    "psp": "psp",
    "dos": "dos",
}
