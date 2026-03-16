#
# steam_library_manager/utils/license_cache_parser.py
# Parser for Steam's encrypted licensecache file (PRNG XOR cipher)
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#
# Credits: Depressurizer (GPLv3), wynick27/steam-missing-covers-downloader,
#          SteamDatabase/Protobufs.
#

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from steam_library_manager.utils.i18n import t

try:
    from .licensecache_pb2 import CMsgClientLicenseList
except ImportError:
    from licensecache_pb2 import CMsgClientLicenseList

from google.protobuf.message import DecodeError

logger = logging.getLogger("steamlibmgr.license_cache")

__all__ = ["LicenseCacheParser", "LicenseInfo"]


@dataclass(frozen=True)
class LicenseInfo:
    """A single Steam license entry (package_id + acquisition time)."""

    package_id: int
    time_created: int = 0


class _RandomStream:
    """Valve's PRNG for licensecache XOR encryption (port of Depressurizer's RandomStream)."""

    _NTAB: int = 32
    _IA: int = 16807
    _IM: int = 2147483647
    _IQ: int = 127773
    _IR: int = 2836
    _NDIV: int = 1 + (_IM - 1) // _NTAB

    def __init__(self) -> None:
        self._idum: int = 0
        self._iy: int = 0
        self._iv: list[int] = [0] * self._NTAB

    def _set_seed(self, seed: int) -> None:
        self._idum = -seed if seed >= 0 else seed
        self._iy = 0
        self._iv = [0] * self._NTAB

    def _generate(self) -> int:
        if self._idum <= 0 or self._iy == 0:
            if -self._idum < 1:
                self._idum = 1
            else:
                self._idum = -self._idum

            for j in range(self._NTAB + 7, -1, -1):
                k = self._idum // self._IQ
                self._idum = self._IA * (self._idum - k * self._IQ) - self._IR * k
                if self._idum < 0:
                    self._idum += self._IM
                if j < self._NTAB:
                    self._iv[j] = self._idum

            self._iy = self._iv[0]

        k = self._idum // self._IQ
        self._idum = self._IA * (self._idum - k * self._IQ) - self._IR * k
        if self._idum < 0:
            self._idum += self._IM

        j = self._iy // self._NDIV
        if j >= self._NTAB or j < 0:
            j = (j % self._NTAB) & 0x7FFFFFFF

        self._iy = self._iv[j]
        self._iv[j] = self._idum
        return self._iy

    def _random_int(self, low: int, high: int) -> int:
        x = high - low + 1
        if x <= 1:
            return low
        max_acceptable = 0x7FFFFFFF - ((0x7FFFFFFF + 1) % x)
        while True:
            n = self._generate()
            if n <= max_acceptable:
                break
        return low + (n % x)

    def decrypt(self, key: int, data: bytes) -> bytes:
        """Decrypt data using XOR with PRNG stream keyed by Steam32 ID."""
        self._set_seed(key)
        result = bytearray(len(data))
        for i in range(len(data)):
            result[i] = data[i] ^ self._random_int(32, 126)
        return bytes(result)


class LicenseCacheParser:
    """Parses Steam's encrypted licensecache to extract owned PackageIDs."""

    def __init__(self, steam_path: Path, steam32_id: int) -> None:
        self._path = steam_path / "userdata" / str(steam32_id) / "config" / "licensecache"
        self._steam32_id = steam32_id

    def get_owned_package_ids(self) -> set[int]:
        """Returns all owned PackageIDs from the licensecache."""
        licenses = self.parse()
        return {lic.package_id for lic in licenses}

    def parse(self) -> list[LicenseInfo]:
        """Decrypts and parses the licensecache file."""
        if not self._path.exists():
            logger.info(t("logs.license_cache.not_found", path=str(self._path)))
            return []

        try:
            encrypted = self._path.read_bytes()
            if len(encrypted) < 8:
                logger.warning(t("logs.license_cache.too_small", size=len(encrypted)))
                return []

            decrypted = _RandomStream().decrypt(self._steam32_id, encrypted)

            # Strip last 4 bytes (checksum, per Depressurizer)
            data = decrypted[:-4]

            return self._parse_protobuf(data)

        except (OSError, IndexError, ValueError, DecodeError) as exc:
            logger.error(t("logs.license_cache.parse_error", error=str(exc)))
            return []

    def _parse_protobuf(self, data: bytes) -> list[LicenseInfo]:
        msg = CMsgClientLicenseList()
        msg.ParseFromString(data)

        licenses: list[LicenseInfo] = []
        for lic in msg.licenses:
            if lic.package_id > 0:
                licenses.append(
                    LicenseInfo(
                        package_id=lic.package_id,
                        time_created=lic.time_created,
                    )
                )

        logger.info(t("logs.license_cache.parsed", count=len(licenses)))
        return licenses
