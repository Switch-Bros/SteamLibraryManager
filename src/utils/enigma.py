# src/utils/enigma.py

"""Easter egg loader, sound player, and detection manager.

Reads egg data from the hidden resources/.enigma file and plays
sound effects via paplay (PulseAudio/PipeWire).

The EasterEggManager provides a generic key-sequence detection
system so new eggs can be added with a single dict entry.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer

from src.config import config

if TYPE_CHECKING:
    from src.ui.main_window import MainWindow

__all__ = [
    "EasterEggManager",
    "KeySequenceEgg",
    "load_easter_egg",
    "play_easter_egg_sound",
]


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


# ---------------------------------------------------------------------------
# Key-sequence-based Easter egg system
# ---------------------------------------------------------------------------


@dataclass
class KeySequenceEgg:
    """A key-sequence-based Easter egg definition.

    Attributes:
        sequence: List of Qt key codes to match.
        timeout_ms: Buffer auto-clear timeout in milliseconds.
        egg_id: Identifier for load_easter_egg() lookup.
    """

    sequence: list[int]
    timeout_ms: int = 3000
    egg_id: str = ""
    _buffer: list[int] = field(default_factory=list, repr=False, compare=False)

    def feed_key(self, key: int) -> bool:
        """Feeds a key press and checks for sequence match.

        Args:
            key: Qt key code from the event.

        Returns:
            True if the full sequence was matched.
        """
        self._buffer.append(key)
        max_len = len(self.sequence)
        if len(self._buffer) > max_len:
            self._buffer = self._buffer[-max_len:]
        return self._buffer == self.sequence

    def reset(self) -> None:
        """Clears the key buffer."""
        self._buffer.clear()


class EasterEggManager:
    """Central detection and triggering for all Easter eggs.

    Manages key sequence detection, timeouts, and triggering.
    New eggs are added by appending to the _eggs dict.

    Attributes:
        _mw: The parent MainWindow instance.
    """

    def __init__(self, mw: MainWindow) -> None:
        self._mw = mw

        self._eggs: dict[str, KeySequenceEgg] = {
            "konami": KeySequenceEgg(
                sequence=[
                    int(Qt.Key.Key_Up),
                    int(Qt.Key.Key_Up),
                    int(Qt.Key.Key_Down),
                    int(Qt.Key.Key_Down),
                    int(Qt.Key.Key_Left),
                    int(Qt.Key.Key_Right),
                    int(Qt.Key.Key_Left),
                    int(Qt.Key.Key_Right),
                    int(Qt.Key.Key_B),
                    int(Qt.Key.Key_A),
                ],
                timeout_ms=3000,
                egg_id="konami",
            ),
        }

        self._timer = QTimer(mw)
        self._timer.setSingleShot(True)
        self._timer.setInterval(3000)
        self._timer.timeout.connect(self._reset_all)

    def on_key_event(self, key: int) -> str | None:
        """Feeds a key press to all registered eggs.

        Args:
            key: Qt key code from the event.

        Returns:
            Name of triggered egg, or None.
        """
        self._timer.start()
        for name, egg in self._eggs.items():
            if egg.feed_key(key):
                egg.reset()
                self._timer.stop()
                self._trigger(name, egg)
                return name
        return None

    def _trigger(self, name: str, egg: KeySequenceEgg) -> None:
        """Triggers an Easter egg by name.

        Args:
            name: Registry key of the egg.
            egg: The egg definition.
        """
        from src.ui.widgets.ui_helper import UIHelper

        if self._mw.search_entry and self._mw.search_entry.text():
            self._mw.search_entry.clear()

        egg_data = load_easter_egg(egg.egg_id or name)
        if not egg_data:
            return

        if "sound" in egg_data:
            play_easter_egg_sound(egg_data["sound"])

        QTimer.singleShot(
            1000,
            lambda: UIHelper.show_info(
                self._mw,
                egg_data.get("message", ""),
                title=egg_data.get("title", "Easter Egg"),
            ),
        )

    def _reset_all(self) -> None:
        """Resets all egg buffers (called on timeout)."""
        for egg in self._eggs.values():
            egg.reset()
