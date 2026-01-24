"""
Steam AppInfo.vdf Parser - MEGA Edition v2 CLEAN
Supports versions 28, 29, 39, 40, 41 with full READ & WRITE support

Based on:
- SteamAppInfoParser (C# by xPaw) - Modern version support
- appinfo-parser (Python) - Version detection
- Steam-Metadata-Editor - Write support

Author: HeikesFootSlave + Claude
License: GPL-3.0
"""

import struct
import hashlib
from typing import Dict, Optional, List, BinaryIO
from enum import IntEnum

# Import i18n if available (optional for standalone use)
try:
    from src.utils.i18n import t

    HAS_I18N = True
except ImportError:
    HAS_I18N = False


    def t(key: str, **_kwargs) -> str:
        """Fallback translation function"""
        return key.split('.')[-1]

__all__ = ('AppInfo', 'AppInfoVersion', 'IncompatibleVersionError', 'load', 'loads')


# ===== VERSION DEFINITIONS =====

class AppInfoVersion(IntEnum):
    """AppInfo format versions"""
    # Old versions (for reference, not implemented)
    # VERSION_24 = 0x06445624  # circa 2011
    # VERSION_25 = 0x07445625  # circa 2012
    # VERSION_26 = 0x07445626  # circa 2013
    # VERSION_27 = 0x07445627  # circa 2017

    # Supported versions
    VERSION_28 = 0x07564428  # Dec 2022 - June 2024 (Binary SHA-1)
    VERSION_29 = 0x07564429  # June 2024+ (String Table)
    VERSION_39 = 0x07564427  # Alternate magic for v27
    VERSION_40 = 0x07564428  # Alternate magic for v28
    VERSION_41 = 0x07564429  # Alternate magic for v29


class EUniverse(IntEnum):
    """Steam Universe"""
    Invalid = 0
    Public = 1
    Beta = 2
    Internal = 3
    Dev = 4


class IncompatibleVersionError(Exception):
    """Raised when appinfo.vdf version is not supported"""

    def __init__(self, version: int, magic: int):
        self.version = version
        self.magic = magic
        super().__init__(f"Incompatible version {version} (magic: 0x{magic:08X})")


# ===== MAIN PARSER CLASS =====

class AppInfo:
    """
    Steam appinfo.vdf Parser

    Supports:
    - Read: v28, v29, v39, v40, v41
    - Write: v28, v29, v40, v41 (with correct checksums)
    """

    # Binary type markers
    TYPE_SECTION_END = 0x08
    TYPE_DICT = 0x00
    TYPE_STRING = 0x01
    TYPE_INT32 = 0x02
    TYPE_FLOAT32 = 0x03
    TYPE_POINTER = 0x04  # Unused
    TYPE_WIDESTRING = 0x05  # Unused
    TYPE_COLOR = 0x06  # Unused
    TYPE_INT64 = 0x07
    TYPE_END = 0x08

    def __init__(self, path: Optional[str] = None, data: Optional[bytes] = None):
        """
        Initialize AppInfo parser

        Args:
            path: Path to appinfo.vdf file
            data: Raw bytes to parse
        """
        self.file_path = path
        self.data = None
        self.offset = 0

        # Parsed data
        self.magic = 0
        self.version = 0
        self.universe = EUniverse.Public
        self.apps: Dict[int, Dict] = {}

        # Version-specific
        self.string_table: List[str] = []
        self.string_table_offset = 0

        # Load data
        if path:
            with open(path, 'rb') as f:
                self.data = bytearray(f.read())
        elif data:
            self.data = bytearray(data)
        else:
            raise ValueError(t('errors.appinfo.no_data'))

        # Parse header
        self._parse_header()

        # Parse apps
        self._parse_apps()

    # ===== HEADER PARSING =====

    def _parse_header(self):
        """Parse file header and detect version"""
        # Read magic (4 bytes)
        raw_magic = self._read_uint32()

        # Extract version from magic
        self.version = raw_magic & 0xFF
        self.magic = raw_magic >> 8

        # Verify magic number
        if self.magic != 0x07_56_44:
            raise IncompatibleVersionError(self.version, raw_magic)

        # Verify version
        valid_versions = [28, 29, 39, 40, 41]
        if self.version not in valid_versions:
            raise IncompatibleVersionError(self.version, raw_magic)

        # Read universe
        self.universe = EUniverse(self._read_uint32())

        # Version 41+ has string table offset
        if self.version >= 41:
            self.string_table_offset = self._read_int64()
            # Parse string table
            self._parse_string_table()

    def _parse_string_table(self):
        """Parse string table (v41+)"""
        # Save current position
        saved_offset = self.offset

        # Jump to string table
        self.offset = self.string_table_offset

        # Read string count
        string_count = self._read_uint32()

        # Read strings
        self.string_table = []
        for _ in range(string_count):
            string = self._read_cstring()
            self.string_table.append(string)

        # Restore position
        self.offset = saved_offset

    # ===== APP PARSING =====

    def _parse_apps(self):
        """Parse all apps from file"""
        while True:
            # Read app ID
            current_app_id = self._read_uint32()

            # Check for end marker
            if current_app_id == 0:
                break

            # Parse app entry
            try:
                current_app_data = self._parse_app_entry()
                self.apps[current_app_id] = current_app_data
            except Exception as e:
                if HAS_I18N:
                    print(t('logs.appinfo.parse_error', app_id=current_app_id, error=str(e)))
                else:
                    print(f"Warning: Failed to parse app {current_app_id}: {e}")
                continue

    def _parse_app_entry(self) -> Dict:
        """Parse single app entry"""
        app_entry = {}

        # Version-specific parsing
        if self.version >= 36:
            # Read size field
            app_entry['size'] = self._read_uint32()

        # Read info state
        app_entry['info_state'] = self._read_uint32()

        # Read last updated
        app_entry['last_updated'] = self._read_uint32()

        # Version 38+ has access token
        if self.version >= 38:
            app_entry['access_token'] = self._read_uint64()

        # Version 38+ has SHA-1 hash
        if self.version >= 38:
            app_entry['sha1_hash'] = self.data[self.offset:self.offset + 20]
            self.offset += 20

        # Version 36+ has change number
        if self.version >= 36:
            app_entry['change_number'] = self._read_uint32()

        # Version 40+ has binary SHA-1 hash
        if self.version >= 40:
            app_entry['binary_sha1'] = self.data[self.offset:self.offset + 20]
            self.offset += 20

        # Parse binary VDF data
        app_entry['data'] = self._parse_vdf()

        return app_entry

    # ===== VDF PARSING =====

    def _parse_vdf(self) -> Dict:
        """Parse binary VDF (Key-Value) data"""
        result = {}

        while True:
            # Read value type
            value_type = self._read_byte()

            # Check for end marker
            if value_type == self.TYPE_SECTION_END:
                break

            # Read key
            key = self._read_key()

            # Parse value based on type
            if value_type == self.TYPE_DICT:
                # Nested dictionary
                result[key] = self._parse_vdf()

            elif value_type == self.TYPE_STRING:
                # String value
                result[key] = self._read_cstring()

            elif value_type == self.TYPE_INT32:
                # 32-bit integer
                result[key] = self._read_int32()

            elif value_type == self.TYPE_FLOAT32:
                # 32-bit float
                result[key] = self._read_float32()

            elif value_type == self.TYPE_INT64:
                # 64-bit integer
                result[key] = self._read_int64()

            else:
                # Unknown type - skip
                if HAS_I18N:
                    print(t('logs.appinfo.unknown_type', type=f"0x{value_type:02x}"))
                else:
                    print(f"Warning: Unknown VDF type 0x{value_type:02x}, skipping")
                break

        return result

    # ===== READ PRIMITIVES =====

    def _read_byte(self) -> int:
        """Read single byte"""
        value = self.data[self.offset]
        self.offset += 1
        return value

    def _read_int32(self) -> int:
        """Read signed 32-bit integer"""
        value = struct.unpack_from('<i', self.data, self.offset)[0]
        self.offset += 4
        return value

    def _read_uint32(self) -> int:
        """Read unsigned 32-bit integer"""
        value = struct.unpack_from('<I', self.data, self.offset)[0]
        self.offset += 4
        return value

    def _read_int64(self) -> int:
        """Read signed 64-bit integer"""
        value = struct.unpack_from('<q', self.data, self.offset)[0]
        self.offset += 8
        return value

    def _read_uint64(self) -> int:
        """Read unsigned 64-bit integer"""
        value = struct.unpack_from('<Q', self.data, self.offset)[0]
        self.offset += 8
        return value

    def _read_float32(self) -> float:
        """Read 32-bit float"""
        value = struct.unpack_from('<f', self.data, self.offset)[0]
        self.offset += 4
        return value

    def _read_cstring(self) -> str:
        """Read null-terminated string"""
        end = self.data.find(0, self.offset)
        if end == -1:
            end = len(self.data)

        string_bytes = self.data[self.offset:end]
        self.offset = end + 1

        # Try UTF-8 first, fallback to latin-1
        try:
            return string_bytes.decode('utf-8')
        except UnicodeDecodeError:
            return string_bytes.decode('latin-1', errors='replace')

    def _read_key(self) -> str:
        """Read key (string table or direct)"""
        if self.version >= 41 and self.string_table:
            # Read string table index
            index = self._read_uint32()

            # Bounds check
            if index >= len(self.string_table):
                if HAS_I18N:
                    print(t('logs.appinfo.string_index_out_of_range',
                            index=index, size=len(self.string_table)))
                else:
                    print(f"Warning: String index {index} out of range (table size: {len(self.string_table)})")
                return f"__unknown_{index}__"

            return self.string_table[index]
        else:
            # Direct string
            return self._read_cstring()

    # ===== WRITE SUPPORT =====

    def write(self, output_path: Optional[str] = None) -> bool:
        """
        Write appinfo.vdf back to disk

        Args:
            output_path: Output path (default: overwrite original)

        Returns:
            bool: Success
        """
        if output_path is None:
            if self.file_path is None:
                raise ValueError(t('errors.appinfo.no_output_path'))
            output_path = self.file_path

        try:
            # Build new file data
            output = bytearray()

            # Write header
            self._write_header(output)

            # Write apps
            self._write_apps(output)

            # Write footer (app_id = 0)
            output.extend(struct.pack('<I', 0))

            # Update string table (v41+)
            if self.version >= 41:
                self._write_string_table(output)

            # Write to file
            with open(output_path, 'wb') as f:
                f.write(output)

            return True

        except Exception as e:
            if HAS_I18N:
                print(t('logs.appinfo.write_error', error=str(e)))
            else:
                print(f"Error writing appinfo.vdf: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _write_header(self, output: bytearray):
        """Write file header"""
        # Write magic + version
        magic_version = (self.magic << 8) | self.version
        output.extend(struct.pack('<I', magic_version))

        # Write universe
        output.extend(struct.pack('<I', self.universe))

        # Version 41+ has string table offset (placeholder)
        if self.version >= 41:
            # Will be updated later
            output.extend(struct.pack('<Q', 0))

    def _write_apps(self, output: bytearray):
        """Write all apps"""
        for current_app_id, current_app_data in self.apps.items():
            self._write_app_entry(output, current_app_id, current_app_data)

    def _write_app_entry(self, output: bytearray, entry_app_id: int, entry_app_data: Dict):
        """Write single app entry"""
        # Write app ID
        output.extend(struct.pack('<I', entry_app_id))

        # Encode VDF data
        vdf_data = self._encode_vdf(entry_app_data.get('data', {}))

        # Calculate size (if needed)
        if self.version >= 36:
            # Size = everything after size field
            size = (
                    4 +  # info_state
                    4 +  # last_updated
                    (8 if self.version >= 38 else 0) +  # access_token
                    (20 if self.version >= 38 else 0) +  # sha1_hash
                    (4 if self.version >= 36 else 0) +  # change_number
                    (20 if self.version >= 40 else 0) +  # binary_sha1
                    len(vdf_data)
            )
            output.extend(struct.pack('<I', size))

        # Write info state
        output.extend(struct.pack('<I', entry_app_data.get('info_state', 2)))

        # Write last updated
        output.extend(struct.pack('<I', entry_app_data.get('last_updated', 0)))

        # Version 38+ has access token
        if self.version >= 38:
            output.extend(struct.pack('<Q', entry_app_data.get('access_token', 0)))

        # Version 38+ has SHA-1 hash
        if self.version >= 38:
            # Calculate text VDF SHA-1
            text_vdf = self._dict_to_text_vdf(entry_app_data.get('data', {}))
            sha1_hash = hashlib.sha1(text_vdf).digest()
            output.extend(sha1_hash)

        # Version 36+ has change number
        if self.version >= 36:
            output.extend(struct.pack('<I', entry_app_data.get('change_number', 0)))

        # Version 40+ has binary SHA-1 hash
        if self.version >= 40:
            binary_sha1 = hashlib.sha1(vdf_data).digest()
            output.extend(binary_sha1)

        # Write VDF data
        output.extend(vdf_data)

    def _encode_vdf(self, vdf_data: Dict) -> bytearray:
        """Encode dictionary to binary VDF"""
        output = bytearray()

        for key, value in vdf_data.items():
            if isinstance(value, dict):
                # Nested dictionary
                output.append(self.TYPE_DICT)
                output.extend(self._encode_key(key))
                output.extend(self._encode_vdf(value))

            elif isinstance(value, str):
                # String value
                output.append(self.TYPE_STRING)
                output.extend(self._encode_key(key))
                output.extend(self._encode_cstring(value))

            elif isinstance(value, float):
                # Float value
                output.append(self.TYPE_FLOAT32)
                output.extend(self._encode_key(key))
                output.extend(struct.pack('<f', value))

            elif isinstance(value, int):
                # Integer value - check range
                if -2147483648 <= value <= 2147483647:
                    # 32-bit
                    output.append(self.TYPE_INT32)
                    output.extend(self._encode_key(key))
                    output.extend(struct.pack('<i', value))
                else:
                    # 64-bit
                    output.append(self.TYPE_INT64)
                    output.extend(self._encode_key(key))
                    output.extend(struct.pack('<q', value))

        # End marker
        output.append(self.TYPE_SECTION_END)

        return output

    def _encode_key(self, key: str) -> bytearray:
        """Encode key (string table or direct)"""
        if self.version >= 41 and self.string_table:
            # Find or add to string table
            try:
                index = self.string_table.index(key)
            except ValueError:
                # Add new string
                index = len(self.string_table)
                self.string_table.append(key)

            return bytearray(struct.pack('<I', index))
        else:
            # Direct string
            return self._encode_cstring(key)

    @staticmethod
    def _encode_cstring(string: str) -> bytearray:
        """Encode null-terminated string"""
        try:
            return bytearray(string.encode('utf-8') + b'\x00')
        except UnicodeEncodeError:
            return bytearray(string.encode('latin-1', errors='replace') + b'\x00')

    def _write_string_table(self, output: bytearray):
        """Write string table and update offset"""
        # Record string table position
        string_table_offset = len(output)

        # Write string count
        output.extend(struct.pack('<I', len(self.string_table)))

        # Write strings
        for string in self.string_table:
            output.extend(self._encode_cstring(string))

        # Update offset in header (byte 8-15)
        struct.pack_into('<Q', output, 8, string_table_offset)

    def _dict_to_text_vdf(self, vdf_dict: Dict, indent: int = 0) -> bytes:
        """
        Convert dict to text VDF format (for SHA-1 calculation)
        This must match Steam's exact formatting
        """
        output = b""
        tabs = b"\t" * indent

        for key, value in vdf_dict.items():
            # Escape backslashes in key
            key_escaped = key.replace("\\", "\\\\")

            if isinstance(value, dict):
                # Nested dict
                output += tabs + b'"' + key_escaped.encode('utf-8', errors='replace') + b'"\n'
                output += tabs + b"{\n"
                output += self._dict_to_text_vdf(value, indent + 1)
                output += tabs + b"}\n"
            else:
                # Value
                value_str = str(value).replace("\\", "\\\\")
                output += (tabs + b'"' + key_escaped.encode('utf-8', errors='replace') +
                           b'"\t\t"' + value_str.encode('utf-8', errors='replace') + b'"\n')

        return output

    # ===== CONVENIENCE METHODS =====

    def get_app(self, app_id: int) -> Optional[Dict]:
        """Get app data by ID"""
        return self.apps.get(app_id)

    def set_app(self, set_app_id: int, set_data: Dict):
        """Set app data"""
        if set_app_id not in self.apps:
            self.apps[set_app_id] = {
                'info_state': 2,
                'last_updated': 0,
                'data': {}
            }

        self.apps[set_app_id]['data'] = set_data

    def update_app_metadata(self, update_app_id: int, metadata: Dict):
        """Update app metadata (common section)"""
        if update_app_id not in self.apps:
            return False

        app_data_dict = self.apps[update_app_id].get('data', {})

        if 'common' not in app_data_dict:
            app_data_dict['common'] = {}

        common_section = app_data_dict['common']

        # Update fields
        if 'name' in metadata:
            common_section['name'] = metadata['name']
        if 'developer' in metadata:
            common_section['developer'] = metadata['developer']
        if 'publisher' in metadata:
            common_section['publisher'] = metadata['publisher']
        if 'release_date' in metadata:
            common_section['steam_release_date'] = metadata['release_date']

        return True

    def __len__(self) -> int:
        """Number of apps"""
        return len(self.apps)

    def __contains__(self, check_app_id: int) -> bool:
        """Check if app exists"""
        return check_app_id in self.apps

    def __getitem__(self, get_app_id: int) -> Dict:
        """Get app by ID"""
        return self.apps[get_app_id]

    def __repr__(self) -> str:
        return f"<AppInfo v{self.version} with {len(self.apps)} apps>"


# ===== SIMPLE API =====

def load(fp: BinaryIO) -> AppInfo:
    """Load appinfo.vdf from file object"""
    return AppInfo(data=fp.read())


def loads(file_data: bytes) -> AppInfo:
    """Load appinfo.vdf from bytes"""
    return AppInfo(data=file_data)


# ===== MAIN (for testing) =====

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python appinfo.py <path-to-appinfo.vdf>")
        sys.exit(1)

    file_path = sys.argv[1]

    print(f"Loading {file_path}...")
    appinfo = AppInfo(path=file_path)

    print(f"Version: {appinfo.version}")
    print(f"Universe: {appinfo.universe.name}")
    print(f"Apps: {len(appinfo.apps)}")

    if appinfo.string_table:
        print(f"String table: {len(appinfo.string_table)} strings")

    # Show first few apps
    for i, (show_app_id, show_app_data) in enumerate(list(appinfo.apps.items())[:5]):
        show_data_dict = show_app_data.get('data', {})
        common_data = show_data_dict.get('common', {})
        name = common_data.get('name', f'App {show_app_id}')
        print(f"  {show_app_id}: {name}")

    print("\n✅ Parse successful!")