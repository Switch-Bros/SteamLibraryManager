"""
AppInfo VDF Parser - Iterative Reader (No Recursion Limit!)
Speichern als: src/utils/appinfo_vdf_parser.py
"""

import struct
from pathlib import Path
from typing import Dict, Any, BinaryIO


class AppInfoParser:
    """Parser für Steam's appinfo.vdf (Binary VDF Format)"""

    # VDF Type Bytes
    TYPE_NONE = 0x00
    TYPE_STRING = 0x01
    TYPE_INT32 = 0x02
    TYPE_UINT64 = 0x06
    TYPE_END = 0x08
    TYPE_INT64 = 0x0A

    # Supported versions
    MAGIC_V27 = 0x07564427
    MAGIC_V28 = 0x07564428
    MAGIC_V29 = 0x07564429
    SUPPORTED_VERSIONS = [MAGIC_V27, MAGIC_V28, MAGIC_V29]

    @staticmethod
    def load(file_path: Path) -> Dict[str, Any]:
        """Load appinfo.vdf file"""
        with open(file_path, 'rb') as f:
            return AppInfoParser._parse_file(f)

    @staticmethod
    def _parse_file(f: BinaryIO) -> Dict[str, Any]:
        """Parse entire appinfo file"""
        try:
            magic_data = f.read(4)
            if not magic_data:
                return {}

            magic = struct.unpack('<I', magic_data)[0]
            if magic not in AppInfoParser.SUPPORTED_VERSIONS:
                print(f"Unsupported AppInfo version: {hex(magic)}")
                return {}

            # Skip header (universe version)
            f.read(4)

            apps = {}
            while True:
                app_id_data = f.read(4)
                if not app_id_data: break

                app_id = struct.unpack('<I', app_id_data)[0]
                if app_id == 0:
                    break

                # Skip various header fields
                f.read(4)  # Size
                f.read(4)  # Info state
                f.read(4)  # Last updated
                f.read(8)  # Token
                f.read(20)  # SHA1
                f.read(4)  # Change number

                # Binary VDF Data - ITERATIVE call
                app_data = AppInfoParser._read_binary_vdf_iterative(f)
                apps[str(app_id)] = app_data

            return apps
        except Exception as e:
            print(f"Error parsing appinfo.vdf: {e}")
            import traceback
            traceback.print_exc()
            return {}

    @staticmethod
    def _read_binary_vdf_iterative(f: BinaryIO) -> Dict[str, Any]:
        """
        Liest ein VDF Objekt ITERATIV (ohne Rekursion).
        Verhindert 'maximum recursion depth exceeded'.
        """
        root = {}
        # Der Stack speichert die Wörterbücher, an denen wir gerade arbeiten
        stack = [root]

        while stack:
            # Wir arbeiten immer am obersten Element des Stacks
            current_dict = stack[-1]

            type_byte = f.read(1)
            if not type_byte:
                break

            if type_byte == b'\x08':  # Type End
                stack.pop()  # Wir sind fertig mit diesem Dict, geh eins hoch
                continue

            type_id = ord(type_byte)
            key = AppInfoParser._read_string(f)

            if type_id == AppInfoParser.TYPE_NONE:
                # Das ist der Start eines neuen verschachtelten Objekts
                new_dict = {}
                current_dict[key] = new_dict
                # Push auf den Stack -> Im nächsten Schleifendurchlauf füllen wir DIESES Dict
                stack.append(new_dict)

            elif type_id == AppInfoParser.TYPE_STRING:
                current_dict[key] = AppInfoParser._read_string(f)

            elif type_id == AppInfoParser.TYPE_INT32:
                data = f.read(4)
                if len(data) == 4:
                    current_dict[key] = struct.unpack('<i', data)[0]

            elif type_id == AppInfoParser.TYPE_UINT64:
                data = f.read(8)
                if len(data) == 8:
                    current_dict[key] = struct.unpack('<Q', data)[0]

            elif type_id == AppInfoParser.TYPE_INT64:
                data = f.read(8)
                if len(data) == 8:
                    current_dict[key] = struct.unpack('<q', data)[0]

            # Unbekannte Typen überspringen wir hier sicherheitshalber nicht,
            # da wir sonst die Struktur verlieren würden.

        return root

    @staticmethod
    def _read_string(f: BinaryIO) -> str:
        """Read null-terminated string"""
        chars = []
        while True:
            c = f.read(1)
            if c == b'\x00' or not c:
                break
            chars.append(c)
        return b"".join(chars).decode('utf-8', errors='replace')

    @staticmethod
    def dump(data: Dict, file_path: Path) -> bool:
        """Dump not supported for binary format yet"""
        return False