"""Tests for EasterEggManager and KeySequenceEgg."""

from __future__ import annotations

from PyQt6.QtCore import Qt

from src.utils.enigma import KeySequenceEgg


class TestKeySequenceEgg:
    """Tests for KeySequenceEgg dataclass."""

    def test_feed_key_matches_sequence(self):
        """Full sequence match returns True."""
        egg = KeySequenceEgg(sequence=[1, 2, 3])
        assert not egg.feed_key(1)
        assert not egg.feed_key(2)
        assert egg.feed_key(3)

    def test_feed_key_partial_no_match(self):
        """Partial sequence does not trigger."""
        egg = KeySequenceEgg(sequence=[1, 2, 3])
        assert not egg.feed_key(1)
        assert not egg.feed_key(2)

    def test_reset_clears_buffer(self):
        """Reset clears the internal buffer."""
        egg = KeySequenceEgg(sequence=[1, 2, 3])
        egg.feed_key(1)
        egg.feed_key(2)
        egg.reset()
        # After reset, need full sequence again
        assert not egg.feed_key(3)

    def test_buffer_auto_truncation(self):
        """Buffer truncates to max sequence length."""
        egg = KeySequenceEgg(sequence=[4, 5, 6])
        # Feed many wrong keys first
        for i in range(20):
            egg.feed_key(99)
        # Then the correct sequence
        assert not egg.feed_key(4)
        assert not egg.feed_key(5)
        assert egg.feed_key(6)

    def test_wrong_sequence_no_match(self):
        """Wrong key sequence does not match."""
        egg = KeySequenceEgg(sequence=[1, 2, 3])
        egg.feed_key(1)
        egg.feed_key(2)
        assert not egg.feed_key(4)  # Wrong key

    def test_konami_sequence(self):
        """Konami code sequence matches correctly."""
        konami = [
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
        ]
        egg = KeySequenceEgg(sequence=konami, egg_id="konami")
        for key in konami[:-1]:
            assert not egg.feed_key(key)
        assert egg.feed_key(konami[-1])
