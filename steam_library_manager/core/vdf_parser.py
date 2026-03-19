#
# steam_library_manager/core/vdf_parser.py
# VDF (Valve Data Format) text and binary parser
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

from __future__ import annotations

import struct
from io import BytesIO

__all__ = [
    "UINT_64",
    "INT_64",
    "binary_dump",
    "binary_dumps",
    "binary_load",
    "binary_loads",
]

# type tags
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

# 64-bit types
UINT_64 = int
INT_64 = int


class _Parser:
    # binary VDF parser

    def __init__(self, s, *, alt_end=False):
        self._s = s
        self._e = {BIN_END, BIN_END_ALT} if alt_end else {BIN_END}

    def parse(self):
        # parse dict
        o = {}

        while True:
            tag = self._s.read(1)
            if not tag or tag in self._e:
                break

            k = self._rs()

            if tag == BIN_NONE:
                o[k] = self.parse()
            elif tag == BIN_STRING:
                o[k] = self._rs()
            elif tag == BIN_INT32:
                o[k] = struct.unpack("<i", self._s.read(4))[0]
            elif tag == BIN_FLOAT32:
                o[k] = struct.unpack("<f", self._s.read(4))[0]
            elif tag == BIN_POINTER:
                o[k] = struct.unpack("<i", self._s.read(4))[0]
            elif tag == BIN_WIDESTRING:
                o[k] = self._rw()
            elif tag == BIN_COLOR:
                o[k] = struct.unpack("<i", self._s.read(4))[0]
            elif tag == BIN_UINT64:
                o[k] = struct.unpack("<Q", self._s.read(8))[0]
            elif tag == BIN_INT64:
                o[k] = struct.unpack("<q", self._s.read(8))[0]
            else:
                raise ValueError("bad tag: 0x%s" % tag.hex())

        return o

    def _rs(self):
        # read UTF-8
        b = bytearray()
        while True:
            c = self._s.read(1)
            if not c or c == b"\x00":
                break
            b.extend(c)
        return b.decode("utf-8", errors="replace")

    def _rw(self):
        # read UTF-16LE
        b = bytearray()
        while True:
            p = self._s.read(2)
            if not p or p == b"\x00\x00":
                break
            b.extend(p)
        return b.decode("utf-16-le", errors="replace")


def binary_load(fp):
    # parse from file
    p = _Parser(fp)
    o = {}

    while True:
        tag = fp.read(1)
        if not tag:
            break

        if tag == BIN_NONE:
            k = p._rs()
            o[k] = p.parse()
        elif tag in (BIN_END, BIN_END_ALT):
            break

    return o


def binary_loads(data):
    # parse from bytes
    return binary_load(BytesIO(data))


def binary_dump(obj, fp):
    # serialize to file
    fp.write(binary_dumps(obj))


def binary_dumps(obj):
    # serialize to bytes
    buf = BytesIO()
    _wd(buf, obj)
    return buf.getvalue()


def _wd(buf, obj):
    for k, v in obj.items():
        kb = k.encode("utf-8") + b"\x00"

        if isinstance(v, dict):
            buf.write(BIN_NONE)
            buf.write(kb)
            _wd(buf, v)
        elif isinstance(v, str):
            buf.write(BIN_STRING)
            buf.write(kb)
            buf.write(v.encode("utf-8") + b"\x00")
        elif isinstance(v, float):
            buf.write(BIN_FLOAT32)
            buf.write(kb)
            buf.write(struct.pack("<f", v))
        elif isinstance(v, int):
            if -(2**31) <= v < 2**31:
                buf.write(BIN_INT32)
                buf.write(kb)
                buf.write(struct.pack("<i", v))
            elif -(2**63) <= v < 2**63:
                buf.write(BIN_INT64)
                buf.write(kb)
                buf.write(struct.pack("<q", v))
            else:
                buf.write(BIN_UINT64)
                buf.write(kb)
                buf.write(struct.pack("<Q", v & 0xFFFFFFFFFFFFFFFF))

    buf.write(BIN_END)
