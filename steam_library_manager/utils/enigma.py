#
# steam_library_manager/utils/enigma.py
# Token obfuscation utilities for secure API key storage
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field

from PyQt6.QtCore import Qt, QTimer

from steam_library_manager.config import config

__all__ = [
    "EasterEggManager",
    "KeySequenceEgg",
    "load_easter_egg",
    "play_easter_egg_sound",
]


def load_easter_egg(egg_id):
    # Load egg data from the hidden .enigma resource file
    fpath = config.RESOURCES_DIR / ".enigma"
    try:
        with open(fpath, encoding="utf-8") as f:
            data = json.load(f)
        return data.get(egg_id, {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def play_easter_egg_sound(filename):
    # Play sound via paplay (PulseAudio/PipeWire)
    snd = config.RESOURCES_DIR / "sounds" / filename
    if not snd.exists():
        return

    try:
        subprocess.Popen(
            ["paplay", str(snd)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        # paplay not installed - fail silently, it's just an easter egg
        pass


# Key-sequence Easter egg system


@dataclass
class KeySequenceEgg:
    """A key-sequence-based Easter egg definition."""

    sequence: list[int]
    timeout_ms: int = 3000
    egg_id: str = ""
    _buffer: list[int] = field(default_factory=list, repr=False, compare=False)

    def feed_key(self, key):
        # Check if key completes the sequence
        self._buffer.append(key)
        maxlen = len(self.sequence)
        if len(self._buffer) > maxlen:
            self._buffer = self._buffer[-maxlen:]
        return self._buffer == self.sequence

    def reset(self):
        self._buffer.clear()


class EasterEggManager:
    """Central detection and triggering for all Easter eggs."""

    def __init__(self, mw):
        self._mw = mw

        self._eggs = {
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

    def on_key_event(self, key):
        # Feed key to all registered eggs, return name on match
        self._timer.start()
        for name, egg in self._eggs.items():
            if egg.feed_key(key):
                egg.reset()
                self._timer.stop()
                self._fire(name, egg)
                return name
        return None

    def _fire(self, name, egg):
        # Trigger the matched easter egg
        from steam_library_manager.ui.widgets.ui_helper import UIHelper

        if self._mw.search_entry and self._mw.search_entry.text():
            self._mw.search_entry.clear()

        data = load_easter_egg(egg.egg_id or name)
        if not data:
            return

        if "sound" in data:
            play_easter_egg_sound(data["sound"])

        QTimer.singleShot(
            1000,
            lambda: UIHelper.show_info(
                self._mw,
                data.get("message", ""),
                title=data.get("title", "Easter Egg"),
            ),
        )

    def _reset_all(self):
        # Called on timeout - clear all buffers
        for egg in self._eggs.values():
            egg.reset()
