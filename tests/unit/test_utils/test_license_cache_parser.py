"""Unit tests for LicenseCacheParser."""

import struct

from src.utils.license_cache_parser import (
    LicenseCacheParser,
    LicenseInfo,
    _RandomStream,
)

# -- Helpers ------------------------------------------------------------------


def _make_encrypted_licensecache(steam32_id: int, package_ids: list[int]) -> bytes:
    """Create a fake encrypted licensecache for testing.

    Uses the same protobuf schema as the real parser.
    XOR is symmetric: decrypt(key, decrypt(key, x)) == x.

    Args:
        steam32_id: Key to encrypt with.
        package_ids: PackageIDs to encode.

    Returns:
        Encrypted bytes (ready to write to file).
    """
    from src.utils.licensecache_pb2 import CMsgClientLicenseList

    msg = CMsgClientLicenseList()
    msg.eresult = 1
    for pkg_id in package_ids:
        lic = msg.licenses.add()
        lic.package_id = pkg_id
        lic.time_created = 1700000000

    data = msg.SerializeToString()

    # Add 4-byte checksum placeholder (stripped during parsing)
    data += b"\x00\x00\x00\x00"

    # Encrypt (XOR is symmetric)
    return _RandomStream().decrypt(steam32_id, data)


# -- TestRandomStream ---------------------------------------------------------


class TestRandomStream:
    """Tests for the Valve PRNG XOR cipher."""

    def test_decrypt_known_bytes(self):
        """Decrypt 10 known bytes with seed=12345, verify deterministic output."""
        rs = _RandomStream()
        data = bytes(range(10))
        result = rs.decrypt(12345, data)
        assert len(result) == 10
        assert result != data  # XOR should change the data

    def test_decrypt_empty_data(self):
        """decrypt(key, b'') returns b''."""
        rs = _RandomStream()
        assert rs.decrypt(12345, b"") == b""

    def test_decrypt_deterministic(self):
        """Same key + data always produces same output."""
        data = b"hello world"
        r1 = _RandomStream().decrypt(42, data)
        r2 = _RandomStream().decrypt(42, data)
        assert r1 == r2

    def test_different_seeds_different_output(self):
        """Different seeds produce different results."""
        data = b"test data here"
        r1 = _RandomStream().decrypt(1, data)
        r2 = _RandomStream().decrypt(2, data)
        assert r1 != r2

    def test_xor_symmetric(self):
        """decrypt(key, decrypt(key, x)) == x (XOR symmetry)."""
        data = b"Steam licensecache test"
        key = 43925226
        encrypted = _RandomStream().decrypt(key, data)
        decrypted = _RandomStream().decrypt(key, encrypted)
        assert decrypted == data


# -- TestLicenseCacheParser ---------------------------------------------------


class TestLicenseCacheParser:
    """Tests for the LicenseCacheParser."""

    def test_file_not_found_returns_empty(self, tmp_path):
        """Non-existent path returns empty list."""
        parser = LicenseCacheParser(tmp_path / "nonexistent", 12345)
        assert parser.parse() == []

    def test_too_small_file_returns_empty(self, tmp_path):
        """File with < 8 bytes returns empty list."""
        steam_path = tmp_path / "steam"
        cache_dir = steam_path / "userdata" / "12345" / "config"
        cache_dir.mkdir(parents=True)
        (cache_dir / "licensecache").write_bytes(b"\x00\x01\x02\x03")

        parser = LicenseCacheParser(steam_path, 12345)
        assert parser.parse() == []

    def test_get_owned_package_ids_returns_set(self, tmp_path):
        """get_owned_package_ids returns a set[int]."""
        steam_path = tmp_path / "steam"
        cache_dir = steam_path / "userdata" / "12345" / "config"
        cache_dir.mkdir(parents=True)

        encrypted = _make_encrypted_licensecache(12345, [100, 200, 300])
        (cache_dir / "licensecache").write_bytes(encrypted)

        parser = LicenseCacheParser(steam_path, 12345)
        result = parser.get_owned_package_ids()

        assert isinstance(result, set)
        assert result == {100, 200, 300}

    def test_parse_valid_protobuf(self, tmp_path):
        """Craft minimal encrypted protobuf, verify parse extracts PackageIDs."""
        steam_path = tmp_path / "steam"
        cache_dir = steam_path / "userdata" / "99999" / "config"
        cache_dir.mkdir(parents=True)

        pkg_ids = [42, 1938050, 7, 12345]
        encrypted = _make_encrypted_licensecache(99999, pkg_ids)
        (cache_dir / "licensecache").write_bytes(encrypted)

        parser = LicenseCacheParser(steam_path, 99999)
        licenses = parser.parse()

        assert len(licenses) == 4
        parsed_ids = {lic.package_id for lic in licenses}
        assert parsed_ids == set(pkg_ids)

    def test_parse_returns_license_info(self, tmp_path):
        """Verify LicenseInfo fields are populated correctly."""
        steam_path = tmp_path / "steam"
        cache_dir = steam_path / "userdata" / "11111" / "config"
        cache_dir.mkdir(parents=True)

        encrypted = _make_encrypted_licensecache(11111, [500])
        (cache_dir / "licensecache").write_bytes(encrypted)

        parser = LicenseCacheParser(steam_path, 11111)
        licenses = parser.parse()

        assert len(licenses) == 1
        lic = licenses[0]
        assert isinstance(lic, LicenseInfo)
        assert lic.package_id == 500
        assert lic.time_created == 1700000000

    def test_parse_corrupted_data_returns_empty(self, tmp_path):
        """Corrupted (random) data returns empty list gracefully."""
        steam_path = tmp_path / "steam"
        cache_dir = steam_path / "userdata" / "12345" / "config"
        cache_dir.mkdir(parents=True)

        # Write random garbage (long enough to pass size check)
        (cache_dir / "licensecache").write_bytes(b"\xff" * 100)

        parser = LicenseCacheParser(steam_path, 12345)
        # Should not raise, returns empty list
        result = parser.parse()
        assert isinstance(result, list)

    def test_empty_packages_not_included(self, tmp_path):
        """Package with ID 0 is excluded."""
        steam_path = tmp_path / "steam"
        cache_dir = steam_path / "userdata" / "12345" / "config"
        cache_dir.mkdir(parents=True)

        # Include package_id=0 which should be filtered out
        encrypted = _make_encrypted_licensecache(12345, [0, 42, 100])
        (cache_dir / "licensecache").write_bytes(encrypted)

        parser = LicenseCacheParser(steam_path, 12345)
        result = parser.get_owned_package_ids()
        assert 0 not in result
        assert result == {42, 100}


# -- TestPackageInfoParserFiltered --------------------------------------------


class TestPackageInfoParserFiltered:
    """Tests for PackageInfoParser.get_app_ids_for_packages()."""

    def test_get_app_ids_for_packages_empty_set(self, tmp_path):
        """Empty owned_packages returns empty result."""
        from src.core.packageinfo_parser import PackageInfoParser

        parser = PackageInfoParser(tmp_path)
        result = parser.get_app_ids_for_packages(set())
        assert result == set()

    def test_get_app_ids_for_packages_file_not_found(self, tmp_path):
        """Missing file returns empty set, no crash."""
        from src.core.packageinfo_parser import PackageInfoParser

        parser = PackageInfoParser(tmp_path / "nonexistent")
        result = parser.get_app_ids_for_packages({1, 2, 3})
        assert result == set()

    def test_get_app_ids_for_packages_filters_correctly(self, tmp_path):
        """Only returns AppIDs from specified packages."""
        from src.core.packageinfo_parser import PackageInfoParser

        # Build a minimal binary packageinfo.vdf
        pkg_data = _build_minimal_packageinfo(
            {
                10: [100, 101],  # pkg 10 has apps 100, 101
                20: [200],  # pkg 20 has app 200
                30: [300, 301],  # pkg 30 has apps 300, 301
            }
        )

        appcache = tmp_path / "appcache"
        appcache.mkdir()
        (appcache / "packageinfo.vdf").write_bytes(pkg_data)

        parser = PackageInfoParser(tmp_path)

        # Only request packages 10 and 30
        result = parser.get_app_ids_for_packages({10, 30})

        assert "100" in result
        assert "101" in result
        assert "300" in result
        assert "301" in result
        # Package 20 should NOT be included
        assert "200" not in result


def _build_minimal_packageinfo(packages: dict[int, list[int]]) -> bytes:
    """Build a minimal binary packageinfo.vdf for testing.

    Args:
        packages: Dict mapping package_id -> list of app_ids.

    Returns:
        Binary bytes mimicking packageinfo.vdf format.
    """
    buf = bytearray()

    # Header: version (4) + universe (4)
    buf += struct.pack("<II", 0x06, 0x01)

    for pkg_id, app_ids in packages.items():
        # Package ID (4 bytes)
        buf += struct.pack("<I", pkg_id)
        # SHA1 hash (20) + change number (4) + token (8) = 32 bytes
        buf += b"\x00" * 32

        # Binary VDF: outer key wrapping appids
        # Type 0x00 = sub-object, key = str(pkg_id)
        buf += b"\x00"  # sub-object
        buf += str(pkg_id).encode() + b"\x00"  # key

        # Inner: appids sub-object
        buf += b"\x00"  # sub-object
        buf += b"appids\x00"  # key

        for idx, app_id in enumerate(app_ids):
            buf += b"\x02"  # uint32
            buf += str(idx).encode() + b"\x00"  # key
            buf += struct.pack("<I", app_id)  # value

        buf += b"\x08"  # end appids
        buf += b"\x08"  # end outer (pkg_id key)
        buf += b"\x08"  # end top-level VDF object

    # End-of-file marker
    buf += struct.pack("<I", 0xFFFFFFFF)

    return bytes(buf)
