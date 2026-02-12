# src/core/token_store.py

"""Secure token storage for Steam authentication credentials.

Provides encrypted persistence of access and refresh tokens using
AES-GCM encryption with keys derived from machine identity.
Falls back to system keyring when available.
"""

from __future__ import annotations

import base64
import getpass
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from src.config import config
from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.token_store")

__all__ = ["StoredTokens", "TokenStore"]


@dataclass(frozen=True)
class StoredTokens:
    """Immutable container for persisted authentication tokens.

    Attributes:
        access_token: Steam OAuth2 access token.
        refresh_token: Steam OAuth2 refresh token.
        steam_id: SteamID64 of the authenticated user.
        timestamp: Unix timestamp when tokens were stored.
    """

    access_token: str
    refresh_token: str
    steam_id: str
    timestamp: float


class TokenStore:
    """Manages secure storage, retrieval, and refresh of Steam auth tokens.

    Tokens are stored encrypted on disk using AES-GCM.  The encryption key
    is derived from the machine ID and OS username via PBKDF2.  When the
    ``keyring`` package is available, tokens are stored there instead.

    Attributes:
        token_file: Path to the encrypted token file on disk.
    """

    _KEYRING_SERVICE = "steamlibmgr"
    _KEYRING_USERNAME = "steam_tokens"

    def __init__(self, data_dir: Path | None = None) -> None:
        """Initialize the token store.

        Args:
            data_dir: Directory for storing the encrypted token file.
                      Defaults to config.DATA_DIR.
        """
        self.token_file: Path = (data_dir or config.DATA_DIR) / "tokens.enc"
        self._keyring_available: bool = self._check_keyring()

    @staticmethod
    def _check_keyring() -> bool:
        """Check if keyring backend is available and functional."""
        try:
            import keyring

            keyring.get_keyring()
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save_tokens(self, access_token: str, refresh_token: str, steam_id: str) -> bool:
        """Persist authentication tokens securely.

        Args:
            access_token: Steam OAuth2 access token.
            refresh_token: Steam OAuth2 refresh token.
            steam_id: SteamID64 of the authenticated user.

        Returns:
            True if tokens were saved successfully.
        """
        token_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "steam_id": steam_id,
            "timestamp": time.time(),
        }

        try:
            if self._keyring_available:
                return self._save_to_keyring(token_data)
            return self._save_to_file(token_data)
        except Exception as e:
            logger.error(t("logs.auth.token_save_failed", error=str(e)))
            return False

    def load_tokens(self) -> StoredTokens | None:
        """Load tokens from secure storage.

        Returns:
            StoredTokens if found and valid, None otherwise.
        """
        try:
            if self._keyring_available:
                data = self._load_from_keyring()
            else:
                data = self._load_from_file()

            if data is None:
                return None

            logger.info(t("logs.auth.token_loaded"))
            return StoredTokens(
                access_token=data["access_token"],
                refresh_token=data["refresh_token"],
                steam_id=data["steam_id"],
                timestamp=data["timestamp"],
            )
        except Exception as e:
            logger.error(t("logs.auth.token_load_failed", error=str(e)))
            return None

    def clear_tokens(self) -> None:
        """Remove all stored tokens from disk and keyring."""
        try:
            if self._keyring_available:
                self._clear_keyring()
            if self.token_file.exists():
                self.token_file.unlink()
            logger.info(t("logs.auth.token_cleared"))
        except Exception as e:
            logger.error(t("logs.auth.token_clear_failed", error=str(e)))

    @staticmethod
    def refresh_access_token(refresh_token: str, steam_id: str = "") -> str | None:
        """Obtain a new access token using a refresh token.

        Args:
            refresh_token: The Steam refresh token.
            steam_id: SteamID64 of the user (may be required by Steam API).

        Returns:
            New access token, or None on failure.
        """
        url = "https://api.steampowered.com/IAuthenticationService/GenerateAccessTokenForApp/v1/"
        post_data: dict[str, str] = {"refresh_token": refresh_token}
        if steam_id:
            post_data["steamid"] = steam_id
        try:
            response = requests.post(url, data=post_data, timeout=10)
            response.raise_for_status()
            result = response.json().get("response", {})
            new_token = result.get("access_token")
            if new_token:
                logger.info(t("logs.auth.token_refresh_success"))
                return new_token
        except (requests.RequestException, ValueError, KeyError) as e:
            logger.error(t("logs.auth.token_refresh_failed", error=str(e)))
        return None

    @staticmethod
    def get_steamid_from_token(access_token: str) -> str | None:
        """Extract SteamID64 by calling GetOwnedGames with the access token.

        The GetOwnedGames API returns the SteamID of the authenticated user
        even without a steamid parameter.

        Args:
            access_token: The Steam access token.

        Returns:
            SteamID64 as string, or None if failed.
        """
        # Method 1: Try GetOwnedGames API
        try:
            url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
            headers = {"Authorization": f"Bearer {access_token}"}
            params = {"include_appinfo": 0, "format": "json"}

            response = requests.get(url, params=params, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                steam_id = data.get("response", {}).get("steamid")
                if steam_id:
                    logger.info(t("logs.auth.steamid_resolved"))
                    return str(steam_id)

                if "response" in data:
                    logger.info(t("logs.auth.steamid_missing"))
            else:
                logger.info(t("logs.auth.get_owned_games_status", status=response.status_code))

        except Exception as e:
            logger.error(t("logs.auth.steamid_from_token_error", error=str(e)))

        # Method 2: Fallback — decode JWT token
        try:
            parts = access_token.split(".")
            if len(parts) >= 2:
                payload = parts[1]
                payload += "=" * (4 - len(payload) % 4)
                decoded = base64.urlsafe_b64decode(payload)
                data = json.loads(decoded)

                steam_id = data.get("sub") or data.get("steamid") or data.get("steam_id")
                if steam_id:
                    logger.info(t("logs.auth.steamid_from_jwt"))
                    return str(steam_id)

        except Exception as e:
            logger.error(t("logs.auth.jwt_decode_failed", error=str(e)))

        return None

    # ------------------------------------------------------------------
    # Keyring backend
    # ------------------------------------------------------------------

    def _save_to_keyring(self, data: dict[str, Any]) -> bool:
        """Store token data in the system keyring."""
        import keyring

        keyring.set_password(self._KEYRING_SERVICE, self._KEYRING_USERNAME, json.dumps(data))
        logger.info(t("logs.auth.token_saved"))
        return True

    def _load_from_keyring(self) -> dict[str, Any] | None:
        """Load token data from the system keyring."""
        import keyring

        raw = keyring.get_password(self._KEYRING_SERVICE, self._KEYRING_USERNAME)
        if raw is None:
            return None
        return json.loads(raw)

    def _clear_keyring(self) -> None:
        """Remove tokens from the system keyring."""
        try:
            import keyring

            keyring.delete_password(self._KEYRING_SERVICE, self._KEYRING_USERNAME)
        except Exception:
            pass  # Key may not exist

    # ------------------------------------------------------------------
    # File-based encrypted backend
    # ------------------------------------------------------------------

    def _save_to_file(self, data: dict[str, Any]) -> bool:
        """Encrypt and save token data to file using AES-GCM."""
        from Cryptodome.Cipher import AES
        from Cryptodome.Protocol.KDF import PBKDF2
        from Cryptodome.Random import get_random_bytes

        plaintext = json.dumps(data).encode("utf-8")
        salt = get_random_bytes(16)
        key = PBKDF2(self._get_machine_key(), salt, dkLen=32, count=100_000)

        cipher = AES.new(key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(plaintext)

        envelope = {
            "salt": base64.b64encode(salt).decode(),
            "nonce": base64.b64encode(cipher.nonce).decode(),
            "tag": base64.b64encode(tag).decode(),
            "ciphertext": base64.b64encode(ciphertext).decode(),
        }

        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_file, "w", encoding="utf-8") as f:
            json.dump(envelope, f)

        logger.info(t("logs.auth.token_saved"))
        return True

    def _load_from_file(self) -> dict[str, Any] | None:
        """Load and decrypt token data from file."""
        if not self.token_file.exists():
            return None

        from Cryptodome.Cipher import AES
        from Cryptodome.Protocol.KDF import PBKDF2

        with open(self.token_file, "r", encoding="utf-8") as f:
            envelope = json.load(f)

        salt = base64.b64decode(envelope["salt"])
        nonce = base64.b64decode(envelope["nonce"])
        tag = base64.b64decode(envelope["tag"])
        ciphertext = base64.b64decode(envelope["ciphertext"])

        key = PBKDF2(self._get_machine_key(), salt, dkLen=32, count=100_000)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        plaintext = cipher.decrypt_and_verify(ciphertext, tag)

        return json.loads(plaintext.decode("utf-8"))

    @staticmethod
    def _get_machine_key() -> str:
        """Derive a machine-specific key seed from system identity.

        Combines /etc/machine-id (Linux) or hostname fallback with the
        OS username to produce a deterministic but machine-bound seed.
        """
        machine_id = ""
        for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
            try:
                machine_id = Path(path).read_text().strip()
                if machine_id:
                    break
            except OSError:
                continue

        if not machine_id:
            import socket

            machine_id = socket.gethostname()

        username = getpass.getuser()
        return f"{machine_id}:{username}"
