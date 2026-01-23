"""
AppInfo VDF Parser - Binary Steam AppInfo with Write Support
Based on Steam-Metadata-Editor (GPL-3.0)
Integrated into SteamLibraryManager

FIXED: String Pool loading for AppInfo v29 with choose_apps
Speichern als: src/utils/appinfo.py
"""

import os
from hashlib import sha1
from struct import pack, unpack
from typing import Dict, Any, BinaryIO

__all__ = ('load', 'loads', 'Appinfo', 'IncompatibleVDFError')

# AppInfo Versions
APPINFO_29 = 0x107564429
APPINFO_28 = 0x107564428


class IncompatibleVDFError(Exception):
    """Raised when appinfo.vdf version is not supported"""

    def __init__(self, vdf_version):
        self.vdf_version = vdf_version
        super().__init__(f"Incompatible VDF version: {vdf_version:#08x}")


class Appinfo:
    """
    Steam appinfo.vdf Parser with Read & Write support
    Handles binary VDF format with correct SHA-1 checksum generation
    """

    def __init__(self, vdf_path: str, choose_apps: bool = False, apps: list = None):
        self.offset = 0
        self.string_pool = []
        self.string_offset = 0
        self.version = 0
        self.vdf_path = vdf_path

        self.COMPATIBLE_VERSIONS = [APPINFO_29, APPINFO_28]

        # Binary markers
        self.SEPARATOR = b"\x00"
        self.TYPE_DICT = b"\x00"
        self.TYPE_STRING = b"\x01"
        self.TYPE_INT32 = b"\x02"
        self.SECTION_END = b"\x08"

        # Integer versions
        self.INT_SEPARATOR = int.from_bytes(self.SEPARATOR, "little")
        self.INT_TYPE_DICT = int.from_bytes(self.TYPE_DICT, "little")
        self.INT_TYPE_STRING = int.from_bytes(self.TYPE_STRING, "little")
        self.INT_TYPE_INT32 = int.from_bytes(self.TYPE_INT32, "little")
        self.INT_SECTION_END = int.from_bytes(self.SECTION_END, "little")

        # Read file
        with open(self.vdf_path, "rb") as vdf:
            self.appinfoData = bytearray(vdf.read())

        # Verify and parse
        self.verify_vdf_version()

        # KRITISCH: String Pool MUSS IMMER geladen werden bei v29!
        if self.version == APPINFO_29:
            self.string_offset = self.read_int64()
            prev_offset = self.offset
            self.offset = self.string_offset
            string_count = self.read_uint32()
            for i in range(string_count):
                self.string_pool.append(self.read_string())
            self.offset = prev_offset  # Zurück zum Start

        # Load apps
        if choose_apps and apps:
            self.parsedAppInfo = {}
            for app in apps:
                try:
                    result = self.read_app(app)
                    if result:
                        self.parsedAppInfo[app] = result
                except Exception as e:
                    print(f"Warning: Could not load app {app}: {e}")
                    continue
        else:
            self.parsedAppInfo = self.read_all_apps()

    # ===== READ METHODS =====

    def read_string(self):
        """Read null-terminated string"""
        str_end = self.appinfoData.find(self.INT_SEPARATOR, self.offset)
        string = self.appinfoData[self.offset:str_end]
        try:
            string = string.decode("utf-8")
        except UnicodeDecodeError:
            # Fallback to latin-1, mark with \x06
            string = string.decode("latin-1") + "\x06"
        self.offset += str_end - self.offset + 1
        return string

    def read_string_appinfo29(self):
        """Read string from string pool (v29)"""
        index = self.read_uint32()
        if index >= len(self.string_pool):
            print(f"Warning: String index {index} out of range (pool size: {len(self.string_pool)})")
            return ""
        return self.string_pool[index]

    def read_int64(self):
        int64 = unpack("<q", self.appinfoData[self.offset:self.offset + 8])[0]
        self.offset += 8
        return int64

    def read_uint64(self):
        int64 = unpack("<Q", self.appinfoData[self.offset:self.offset + 8])[0]
        self.offset += 8
        return int64

    def read_uint32(self):
        int32 = unpack("<I", self.appinfoData[self.offset:self.offset + 4])[0]
        self.offset += 4
        return int32

    def read_byte(self):
        byte = self.appinfoData[self.offset]
        self.offset += 1
        return byte

    def parse_subsections(self):
        """Recursively parse nested dictionaries"""
        subsection = {}
        value_parsers = {
            self.INT_TYPE_DICT: self.parse_subsections,
            self.INT_TYPE_STRING: self.read_string if self.version == APPINFO_28 else self.read_string_appinfo29,
            self.INT_TYPE_INT32: self.read_uint32,
        }

        while True:
            value_type = self.read_byte()
            if value_type == self.INT_SECTION_END:
                break

            # Read key
            if self.version == APPINFO_29:
                key = self.read_string_appinfo29()
            else:
                key = self.read_string()

            # Parse value
            if value_type in value_parsers:
                value = value_parsers[value_type]()
                subsection[key] = value
            else:
                print(f"Warning: Unknown value type {value_type:#02x}, skipping")
                break

        return subsection

    def read_header(self):
        """Read app header (48 bytes)"""
        keys = [
            "appid", "size", "state", "last_update",
            "access_token", "checksum_text", "change_number", "checksum_binary"
        ]
        formats = [
            ["<I", 4], ["<I", 4], ["<I", 4], ["<I", 4],
            ["<Q", 8], ["<20s", 20], ["<I", 4], ["<20s", 20]
        ]

        header_data = {}
        for fmt, key in zip(formats, keys):
            value = unpack(fmt[0], self.appinfoData[self.offset:self.offset + fmt[1]])[0]
            self.offset += fmt[1]
            header_data[key] = value

        return header_data

    def verify_vdf_version(self):
        """Check if VDF version is supported"""
        self.version = self.read_uint64()
        if self.version not in self.COMPATIBLE_VERSIONS:
            raise IncompatibleVDFError(self.version)

    def read_app(self, app_id: int):
        """Read single app by ID"""
        byte_data = self.SECTION_END + pack("<I", app_id)
        found_offset = self.appinfoData.find(byte_data)

        if found_offset == -1:
            # App nicht gefunden
            return None

        self.offset = found_offset + 1

        try:
            app = self.read_header()
            app["sections"] = self.parse_subsections()
            app["installed"] = False
            app["install_path"] = "."
            return app
        except Exception as e:
            print(f"Error reading app {app_id}: {e}")
            return None

    def stop_reading(self):
        """Check if we reached end of apps section"""
        if self.version == APPINFO_28:
            return not self.offset < len(self.appinfoData) - 4
        elif self.version == APPINFO_29:
            return not self.offset < self.string_offset - 4
        else:
            raise IncompatibleVDFError(self.version)

    def read_all_apps(self):
        """Read all apps from appinfo.vdf"""
        apps = {}
        while not self.stop_reading():
            try:
                app = self.read_header()
                app["sections"] = self.parse_subsections()
                app["installed"] = False
                app["install_path"] = "."
                apps[app["appid"]] = app
            except Exception as e:
                print(f"Error reading app: {e}")
                break
        return apps

    # ===== WRITE METHODS =====

    def encode_header(self, data):
        """Encode app header to bytes"""
        return pack(
            "<4IQ20sI20s",
            data["appid"], data["size"], data["state"], data["last_update"],
            data["access_token"], data["checksum_text"],
            data["change_number"], data["checksum_binary"]
        )

    def encode_string(self, string):
        """Encode string to bytes"""
        if "\x06" in string:
            # Latin-1 encoded string
            return string[:-1].encode("latin-1") + self.SEPARATOR
        else:
            return string.encode() + self.SEPARATOR

    def encode_uint32(self, integer):
        return pack("<I", integer)

    def encode_int64(self, integer):
        return pack("<q", integer)

    def encode_key_appinfo29(self, key):
        """Encode key using string pool (v29)"""
        try:
            index = self.string_pool.index(key)
        except ValueError:
            self.string_pool.append(key)
            self.appinfoData += self.encode_string(key)
        index = self.string_pool.index(key)
        return self.encode_uint32(index)

    def encode_subsections(self, data):
        """Recursively encode nested dictionaries"""
        encoded_data = bytearray()
        for key, value in data.items():
            # Encode key
            key_encoded = (self.encode_string(key) if self.version == APPINFO_28
                           else self.encode_key_appinfo29(key))

            # Encode value based on type
            if isinstance(value, dict):
                encoded_data += self.TYPE_DICT + key_encoded + self.encode_subsections(value)
            elif isinstance(value, str):
                encoded_data += self.TYPE_STRING + key_encoded + self.encode_string(value)
            elif isinstance(value, int):
                encoded_data += self.TYPE_INT32 + key_encoded + self.encode_uint32(value)

        # End of dictionary marker
        encoded_data += self.SECTION_END
        return encoded_data

    def dict_to_text_vdf(self, data, number_of_tabs=0):
        """
        Format dictionary as text VDF (for checksum calculation)
        CRITICAL: Handles backslash escaping correctly
        """
        formatted_data = b""
        tabs = b"\t" * number_of_tabs

        for key in data.keys():
            if isinstance(data[key], dict):
                number_of_tabs += 1
                formatted_data += (
                        tabs + b'"' + key.replace("\\", "\\\\").encode() + b'"\n' +
                        tabs + b"{\n" +
                        self.dict_to_text_vdf(data[key], number_of_tabs) +
                        tabs + b"}\n"
                )
                number_of_tabs -= 1
            else:
                # Handle latin-1 encoded strings
                if isinstance(data[key], str) and "\x06" in data[key]:
                    formatted_data += (
                            tabs + b'"' + key.replace("\\", "\\\\").encode() + b'"\t\t"' +
                            data[key][:-1].replace("\\", "\\\\").encode("latin-1") + b'"\n'
                    )
                else:
                    formatted_data += (
                            tabs + b'"' + key.replace("\\", "\\\\").encode() + b'"\t\t"' +
                            str(data[key]).replace("\\", "\\\\").encode() + b'"\n'
                    )

        return formatted_data

    def get_text_checksum(self, data):
        """Calculate SHA-1 checksum of text-formatted data"""
        formatted_data = self.dict_to_text_vdf(data)
        hsh = sha1(formatted_data)
        return hsh.digest()

    def get_binary_checksum(self, data):
        """Calculate SHA-1 checksum of binary data"""
        hsh = sha1(data)
        return hsh.digest()

    def update_header_size_and_checksums(self, appinfo, size, checksum_text, checksum_binary):
        """Update header with new size and checksums"""
        appinfo["checksum_binary"] = checksum_binary
        appinfo["checksum_text"] = checksum_text
        appinfo["size"] = size
        return appinfo

    def update_string_offset_and_count(self):
        """Update string pool offset and count (v29 only)"""
        string_count = len(self.string_pool)
        encoded_string_count = self.encode_uint32(string_count)

        # Find end of last app
        last_app_start_index = self.appinfoData.rfind(b'\x08\x00\x00\x00\x00')
        string_table_offset = last_app_start_index + 5

        # Update offset in header
        encoded_offset = self.encode_int64(string_table_offset)
        self.appinfoData[8:16] = encoded_offset

        # Update string count
        self.appinfoData[string_table_offset:string_table_offset + 4] = encoded_string_count

    def update_app(self, app_id):
        """Update single app in appinfo data"""
        appinfo = self.parsedAppInfo[app_id]
        encoded_subsections = self.encode_subsections(appinfo["sections"])
        old_header = self.encode_header(appinfo)

        # Calculate new size (minus appid and size fields = 8 bytes)
        size = len(encoded_subsections) + len(old_header) - 8

        # Calculate checksums
        checksum_text = self.get_text_checksum(appinfo["sections"])
        checksum_binary = self.get_binary_checksum(encoded_subsections)

        # Find app location
        app_location = self.appinfoData.find(old_header)
        app_end_location = app_location + appinfo["size"] + 8

        # Update header
        self.parsedAppInfo[app_id] = self.update_header_size_and_checksums(
            appinfo, size, checksum_text, checksum_binary
        )

        updated_header = self.encode_header(appinfo)

        # Replace in data
        if app_location != -1:
            self.appinfoData[app_location:app_end_location] = updated_header + encoded_subsections
        else:
            # Append if not found
            self.appinfoData.extend(updated_header + encoded_subsections)

    def write_data(self):
        """Write appinfo data back to file"""
        if self.version == APPINFO_29:
            self.update_string_offset_and_count()

        with open(self.vdf_path, "wb") as vdf:
            vdf.write(self.appinfoData)

    def write_appinfo(self, modified_apps: list = None):
        """
        Write modified apps back to appinfo.vdf
        Args:
            modified_apps: List of app IDs to update (None = all)
        """
        if modified_apps:
            for app_id in modified_apps:
                if app_id in self.parsedAppInfo:
                    self.update_app(app_id)
        else:
            # Update all apps
            for app_id in self.parsedAppInfo.keys():
                self.update_app(app_id)

        self.write_data()


# ===== SIMPLE API (backwards compatible) =====

def loads(data: bytes, wrapper=dict) -> Dict[str, Any]:
    """
    Simple API: Parse appinfo from bytes
    (Simplified version without write support)
    """
    # Use simple decoder for backwards compatibility
    from collections import namedtuple
    import struct

    VDF_VERSIONS = [0x07564426, 0x07564427, 0x07564428, 0x07564429]
    SECTION_END = b'\x08'
    TYPE_SECTION = b'\x00'
    TYPE_STRING = b'\x01'
    TYPE_INT32 = b'\x02'
    TYPE_INT64 = b'\x07'

    offset = 0

    # Read header
    magic, universe = struct.unpack_from('<II', data, offset)
    if magic not in VDF_VERSIONS:
        raise ValueError(f"Invalid magic: {magic:08x}")
    offset += 8

    apps = wrapper()

    def decode_section(depth=0):
        nonlocal offset
        if depth > 50:
            return wrapper()

        res = wrapper()
        while True:
            t_byte = data[offset:offset + 1]
            offset += 1
            if t_byte == SECTION_END:
                break

            key_end = data.find(b'\x00', offset)
            key = data[offset:key_end].decode('utf-8', 'replace')
            offset = key_end + 1

            if t_byte == TYPE_SECTION:
                res[key] = decode_section(depth + 1)
            elif t_byte == TYPE_STRING:
                val_end = data.find(b'\x00', offset)
                res[key] = data[offset:val_end].decode('utf-8', 'replace')
                offset = val_end + 1
            elif t_byte == TYPE_INT32:
                res[key] = struct.unpack_from('<i', data, offset)[0]
                offset += 4
            elif t_byte == TYPE_INT64:
                res[key] = struct.unpack_from('<q', data, offset)[0]
                offset += 8
        return res

    # Read apps
    while True:
        app_id = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        if app_id == 0:
            break

        # Skip header (40 bytes)
        offset += 40

        apps[str(app_id)] = decode_section(depth=0)

    return apps


def load(fp: BinaryIO, wrapper=dict) -> Dict[str, Any]:
    """Simple API: Parse appinfo from file"""
    return loads(fp.read(), wrapper=wrapper)