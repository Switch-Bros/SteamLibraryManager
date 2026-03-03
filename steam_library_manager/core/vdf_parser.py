"""Binary VDF parser for Steam shortcuts.vdf.

Based on ValvePython/vdf v3.4 (MIT License).
Original: https://github.com/ValvePython/vdf
Copyright (c) 2015 Rossen Georgiev <rossen@rgp.io>

Only binary VDF functions included (not text VDF).
"""

from __future__ import annotations

import struct
from io import BytesIO
from typing import BinaryIO

__all__ = [
    "UINT_64",
    "INT_64",
    "binary_dump",
    "binary_dumps",
    "binary_load",
    "binary_loads",
]

# -- Type tag constants --

BIN_NONE = b"\x00"
BIN_STRING = b"\x01"
BIN_INT32 = b"\x02"
BIN_FLOAT32 = b"\x03"
BIN_POINTER = b"\x04"
BIN_WIDESTRING = b"\x05"
BIN_COLOR = b"\x06"
BIN_UINT64 = b"\x07"
BIN_END = b"\x08"
BIN_INT64 = b"\x0a"
BIN_END_ALT = b"\x0b"

# Sentinel types for forcing 64-bit int serialization
UINT_64 = int
INT_64 = int


class _BinaryVDFParser:
    """Stateful binary VDF stream parser."""

    def __init__(self, stream: BinaryIO, *, alt_end: bool = False) -> None:
        """Initializes the parser.

        Args:
            stream: Binary stream to read from.
            alt_end: Whether to accept BIN_END_ALT as end marker.
        """
        self._stream = stream
        self._end_tags = {BIN_END, BIN_END_ALT} if alt_end else {BIN_END}

    def parse(self) -> dict[str, object]:
        """Parse a single nested dict from the stream.

        Returns:
            Parsed dictionary.

        Raises:
            ValueError: If the stream contains invalid type tags.
        """
        result: dict[str, object] = {}

        while True:
            tag = self._stream.read(1)
            if not tag or tag in self._end_tags:
                break

            key = self._read_string()

            if tag == BIN_NONE:
                result[key] = self.parse()
            elif tag == BIN_STRING:
                result[key] = self._read_string()
            elif tag == BIN_INT32:
                result[key] = struct.unpack("<i", self._stream.read(4))[0]
            elif tag == BIN_FLOAT32:
                result[key] = struct.unpack("<f", self._stream.read(4))[0]
            elif tag == BIN_POINTER:
                result[key] = struct.unpack("<i", self._stream.read(4))[0]
            elif tag == BIN_WIDESTRING:
                result[key] = self._read_widestring()
            elif tag == BIN_COLOR:
                result[key] = struct.unpack("<i", self._stream.read(4))[0]
            elif tag == BIN_UINT64:
                result[key] = struct.unpack("<Q", self._stream.read(8))[0]
            elif tag == BIN_INT64:
                result[key] = struct.unpack("<q", self._stream.read(8))[0]
            else:
                msg = f"Unknown binary VDF type tag: 0x{tag.hex()}"
                raise ValueError(msg)

        return result

    def _read_string(self) -> str:
        """Read a null-terminated UTF-8 string.

        Returns:
            Decoded string without null terminator.
        """
        buf = bytearray()
        while True:
            ch = self._stream.read(1)
            if not ch or ch == b"\x00":
                break
            buf.extend(ch)
        return buf.decode("utf-8", errors="replace")

    def _read_widestring(self) -> str:
        """Read a null-terminated UTF-16LE string.

        Returns:
            Decoded string without null terminator.
        """
        buf = bytearray()
        while True:
            pair = self._stream.read(2)
            if not pair or pair == b"\x00\x00":
                break
            buf.extend(pair)
        return buf.decode("utf-16-le", errors="replace")


def binary_load(fp: BinaryIO) -> dict[str, object]:
    """Parse binary VDF from a file-like object.

    Args:
        fp: Binary file-like object to read from.

    Returns:
        Parsed dictionary.
    """
    parser = _BinaryVDFParser(fp)
    result: dict[str, object] = {}

    while True:
        tag = fp.read(1)
        if not tag:
            break

        if tag == BIN_NONE:
            key = parser._read_string()
            result[key] = parser.parse()
        elif tag in (BIN_END, BIN_END_ALT):
            break

    return result


def binary_loads(data: bytes) -> dict[str, object]:
    """Parse binary VDF from bytes.

    Args:
        data: Binary VDF data.

    Returns:
        Parsed dictionary.
    """
    return binary_load(BytesIO(data))


def binary_dump(obj: dict[str, object], fp: BinaryIO) -> None:
    """Serialize dict to binary VDF and write to file-like object.

    Args:
        obj: Dictionary to serialize.
        fp: Binary file-like object to write to.
    """
    fp.write(binary_dumps(obj))


def binary_dumps(obj: dict[str, object]) -> bytes:
    """Serialize dict to binary VDF bytes.

    Args:
        obj: Dictionary to serialize.

    Returns:
        Binary VDF representation.
    """
    buf = BytesIO()
    _write_dict(buf, obj)
    return buf.getvalue()


def _write_dict(buf: BytesIO, obj: dict[str, object]) -> None:
    """Write a dictionary as binary VDF.

    Args:
        buf: Output buffer.
        obj: Dictionary to write.
    """
    for key, value in obj.items():
        key_bytes = key.encode("utf-8") + b"\x00"

        if isinstance(value, dict):
            buf.write(BIN_NONE)
            buf.write(key_bytes)
            _write_dict(buf, value)
        elif isinstance(value, str):
            buf.write(BIN_STRING)
            buf.write(key_bytes)
            buf.write(value.encode("utf-8") + b"\x00")
        elif isinstance(value, float):
            buf.write(BIN_FLOAT32)
            buf.write(key_bytes)
            buf.write(struct.pack("<f", value))
        elif isinstance(value, int):
            if -(2**31) <= value < 2**31:
                buf.write(BIN_INT32)
                buf.write(key_bytes)
                buf.write(struct.pack("<i", value))
            elif -(2**63) <= value < 2**63:
                buf.write(BIN_INT64)
                buf.write(key_bytes)
                buf.write(struct.pack("<q", value))
            else:
                buf.write(BIN_UINT64)
                buf.write(key_bytes)
                buf.write(struct.pack("<Q", value & 0xFFFFFFFFFFFFFFFF))

    buf.write(BIN_END)
