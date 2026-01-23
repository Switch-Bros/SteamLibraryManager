"""
Robust AppInfo Parser (Binary VDF) - Cleaned
Speichern als: src/utils/appinfo.py
"""
import struct
from collections import namedtuple
from typing import BinaryIO, Any, Dict

__all__ = ('load', 'loads', 'dump', 'dumps')

VDF_VERSIONS = [0x07564426, 0x07564427, 0x07564428, 0x07564429]
VDF_UNIVERSE = 0x00000001

SECTION_END = b'\x08'
TYPE_SECTION = b'\x00'
TYPE_STRING = b'\x01'
TYPE_INT32 = b'\x02'
TYPE_INT64 = b'\x07'

Integer = namedtuple('Integer', ('size', 'data'))


class AppInfoDecoder:
    def __init__(self, data: bytes, wrapper=dict):
        self.data = data
        self.offset = 0
        self.wrapper = wrapper

    def decode(self) -> Dict[str, Any]:
        magic, universe = struct.unpack_from('<II', self.data, self.offset)
        if magic not in VDF_VERSIONS:
            raise ValueError(f"Invalid magic: {magic:08x}")
        self.offset += 8

        apps = self.wrapper()
        while True:
            app_id = struct.unpack_from('<I', self.data, self.offset)[0]
            self.offset += 4
            if app_id == 0:
                break

            # Skip header (40 bytes after app_id)
            self.offset += 40

            apps[str(app_id)] = self.decode_section(depth=0)  # FIX: depth hinzugefügt
        return apps

    def decode_section(self, depth=0) -> Dict[str, Any]:  # FIX: depth Parameter
        # FIX: Tiefenlimit gegen Endlosschleife
        if depth > 50:
            return self.wrapper()

        res = self.wrapper()
        while True:
            t_byte = self.data[self.offset:self.offset + 1]
            self.offset += 1
            if t_byte == SECTION_END:
                break

            key_end = self.data.find(b'\x00', self.offset)
            key = self.data[self.offset:key_end].decode('utf-8', 'replace')
            self.offset = key_end + 1

            if t_byte == TYPE_SECTION:
                res[key] = self.decode_section(depth + 1)  # FIX: depth + 1
            elif t_byte == TYPE_STRING:
                val_end = self.data.find(b'\x00', self.offset)
                res[key] = self.data[self.offset:val_end].decode('utf-8', 'replace')
                self.offset = val_end + 1
            elif t_byte == TYPE_INT32:
                res[key] = struct.unpack_from('<i', self.data, self.offset)[0]
                self.offset += 4
            elif t_byte == TYPE_INT64:
                res[key] = struct.unpack_from('<q', self.data, self.offset)[0]
                self.offset += 8
        return res

def loads(data: bytes, wrapper=dict) -> Dict[str, Any]:
    return AppInfoDecoder(data, wrapper).decode()

def load(fp: BinaryIO, wrapper=dict) -> Dict[str, Any]:
    return loads(fp.read(), wrapper=wrapper)

def dumps(obj: Dict[str, Any]) -> bytes:
    """Erzeugt einen minimalen Header (Schreiben von Daten ist komplex)"""
    if not obj:
        return b""
    return struct.pack('<II', 0x07564428, VDF_UNIVERSE)

def dump(obj: Dict[str, Any], fp: BinaryIO):
    fp.write(dumps(obj))