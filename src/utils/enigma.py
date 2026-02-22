# src/utils/enigma.py

"""Easter egg loader and sound player.

Reads egg data from the hidden resources/.enigma file and plays
sound effects via paplay (PulseAudio/PipeWire).  This module is
intentionally kept free of PyQt6 dependencies so it can be used
from any part of the codebase.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from src.config import config

__all__ = ["load_easter_egg", "play_easter_egg_sound"]


def load_easter_egg(egg_id: str) -> dict[str, str]:
    """Load easter egg data from the hidden .enigma file.

    Args:
        egg_id: Key in the JSON file (e.g. "konami", "searchbar").

    Returns:
        Dict with 'title', 'message', and optionally 'sound'.
        Empty dict if egg_id not found or file missing.
    """
    egg_file: Path = config.RESOURCES_DIR / ".enigma"
    try:
        with open(egg_file, encoding="utf-8") as f:
            data = json.load(f)
        return data.get(egg_id, {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def play_easter_egg_sound(filename: str) -> None:
    """Play an easter egg sound file via system audio.

    Uses paplay (PulseAudio/PipeWire) which is available on
    virtually all Linux desktops.  Fails silently if unavailable.

    Args:
        filename: Sound file name (e.g. "Konami-victory.wav").
    """
    sound_path: Path = config.RESOURCES_DIR / "sounds" / filename
    if not sound_path.exists():
        return

    try:
        subprocess.Popen(
            ["paplay", str(sound_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        # paplay not installed — fail silently, it's just an easter egg
        pass
