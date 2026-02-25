"""Parser for Steam's encrypted licensecache file.

Steam stores all owned licenses in an encrypted Protobuf file at
``userdata/{steam32_id}/config/licensecache``. Decrypting this and
cross-referencing with ``packageinfo.vdf`` gives us the definitive
list of every AppID the user owns — including games that the
GetOwnedGames API misses.

Follows the same pattern as ``manifest.py`` for Protobuf handling.

Algorithm: Valve's custom PRNG-based XOR cipher (from Depressurizer).
Credits: Depressurizer (GPLv3), wynick27/steam-missing-covers-downloader,
         SteamDatabase/Protobufs.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from src.utils.i18n import t

try:
    from .licensecache_pb2 import CMsgClientLicenseList
except ImportError:
    from licensecache_pb2 import CMsgClientLicenseList

from google.protobuf.message import DecodeError

logger = logging.getLogger("steamlibmgr.license_cache")

__all__ = ["LicenseCacheParser", "LicenseInfo"]


@dataclass(frozen=True)
class LicenseInfo:
    """A single Steam license entry.

    Attributes:
        package_id: The Steam package ID.
        time_created: Unix timestamp when the license was acquired.
    """

    package_id: int
    time_created: int = 0


class _RandomStream:
    """Valve's PRNG for licensecache XOR encryption.

    Direct port of Depressurizer's RandomStream (C#).
    Constants: IA=16807, IM=2147483647, IQ=127773, IR=2836, NTAB=32.
    """

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
        """Initialize the PRNG with a seed value.

        Args:
            seed: The seed (Steam32 account ID).
        """
        self._idum = -seed if seed >= 0 else seed
        self._iy = 0
        self._iv = [0] * self._NTAB

    def _generate(self) -> int:
        """Generate the next random number.

        Returns:
            Random integer in [1, IM-1].
        """
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
        """Generate random int in [low, high] inclusive.

        Args:
            low: Lower bound.
            high: Upper bound.

        Returns:
            Random integer in the range [low, high].
        """
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
        """Decrypt data using XOR with PRNG stream.

        Args:
            key: Decryption key (Steam32 account ID).
            data: Encrypted bytes from licensecache file.

        Returns:
            Decrypted bytes.
        """
        self._set_seed(key)
        result = bytearray(len(data))
        for i in range(len(data)):
            result[i] = data[i] ^ self._random_int(32, 126)
        return bytes(result)


class LicenseCacheParser:
    """Parses Steam's encrypted licensecache to extract owned PackageIDs.

    The licensecache file is an XOR-encrypted Protobuf containing every
    license (package) the user owns. Combined with PackageInfoParser,
    this gives the definitive list of all owned AppIDs.

    Attributes:
        _path: Path to the licensecache file.
        _steam32_id: User's Steam32 account ID (decryption key).
    """

    def __init__(self, steam_path: Path, steam32_id: int) -> None:
        """Initializes the parser.

        Args:
            steam_path: Path to the Steam installation directory.
            steam32_id: User's 32-bit Steam account ID (decryption key).
        """
        self._path = steam_path / "userdata" / str(steam32_id) / "config" / "licensecache"
        self._steam32_id = steam32_id

    def get_owned_package_ids(self) -> set[int]:
        """Returns all owned PackageIDs from the licensecache.

        This is the primary method — call this, then pass the result
        to PackageInfoParser.get_app_ids_for_packages().

        Returns:
            Set of owned PackageIDs. Empty set if file missing or parse fails.
        """
        licenses = self.parse()
        return {lic.package_id for lic in licenses}

    def parse(self) -> list[LicenseInfo]:
        """Decrypts and parses the licensecache file.

        Returns:
            List of LicenseInfo entries. Empty list if file missing or parse fails.
        """
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
        """Parse decrypted Protobuf data into LicenseInfo entries.

        Uses the generated CMsgClientLicenseList from licensecache_pb2.py,
        following the same pattern as manifest.py uses for depot manifests.

        Args:
            data: Decrypted Protobuf bytes (checksum already stripped).

        Returns:
            List of parsed LicenseInfo entries.
        """
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
