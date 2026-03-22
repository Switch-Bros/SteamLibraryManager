#
# steam_library_manager/core/token_store.py
# Secure token storage for Steam authentication credentials
#
# Copyright © 2025-2026 SwitchBros
# Licensed under the MIT License. See LICENSE for details.
#

import base64
import getpass
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import requests

from steam_library_manager.config import config
from steam_library_manager.utils.i18n import t
from steam_library_manager.utils.timeouts import HTTP_TIMEOUT

logger = logging.getLogger("steamlibmgr.token_store")

__all__ = ["StoredTokens", "TokenStore"]

# Sentinel returned by refresh_access_token() when Steam responds with HTTP 200
# but does not issue a new token - meaning the stored access token is still valid.
_REFRESH_NOT_NEEDED = "__refresh_not_needed__"


@dataclass(frozen=True)
class StoredTokens:
    """Immutable container for persisted authentication tokens."""

    access_token: str
    refresh_token: str
    steam_id: str
    timestamp: float


class TokenStore:
    """Manages secure storage, retrieval, and refresh of Steam auth tokens.
    Uses AES-GCM on disk or the system keyring when available."""

    _KEYRING_SERVICE = "steamlibmgr"
    _KEYRING_USERNAME = "steam_tokens"

    def __init__(self, data_dir=None):
        self.token_file = (data_dir or config.DATA_DIR) / "tokens.enc"
        self._keyring_available = self._check_keyring()

    @staticmethod
    def _check_keyring():
        # check if keyring backend is available and functional
        try:
            import keyring  # noqa: F811

            keyring.get_keyring()
            return True
        except (ImportError, RuntimeError, OSError):
            return False

    # -- public API --

    def save_tokens(self, access_token, refresh_token, steam_id):
        # persist authentication tokens securely
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

    def load_tokens(self):
        # load tokens from secure storage
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

    def clear_tokens(self):
        # remove all stored tokens from disk and keyring
        try:
            if self._keyring_available:
                self._clear_keyring()
            if self.token_file.exists():
                self.token_file.unlink()
            logger.info(t("logs.auth.token_cleared"))
        except Exception as e:
            logger.error(t("logs.auth.token_clear_failed", error=str(e)))

    @staticmethod
    def refresh_access_token(refresh_token, steam_id="", max_retries=3):
        # obtain a new access token using a refresh token via Steam's protobuf endpoint
        if not steam_id:
            logger.warning("Cannot refresh token without steam_id")
            return None

        url = "https://api.steampowered.com/IAuthenticationService/GenerateAccessTokenForApp/v1/"
        proto_body = TokenStore._encode_refresh_proto(refresh_token, steam_id)
        post_data = {
            "input_protobuf_encoded": base64.b64encode(proto_body).decode("ascii"),
        }

        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.post(url, data=post_data, timeout=HTTP_TIMEOUT)
                resp.raise_for_status()

                new_token = None
                ctype = resp.headers.get("Content-Type", "")

                if "json" in ctype or (resp.text and resp.text.startswith("{")):
                    result = resp.json().get("response", {})
                    new_token = result.get("access_token")
                elif resp.content:
                    new_token = TokenStore._decode_string_field(resp.content, field_number=1)

                if new_token:
                    logger.info(t("logs.auth.token_refresh_success"))
                    return new_token

                # Steam returned HTTP 200 but no new token - stored token still valid
                logger.info("Token refresh: Steam returned no new token, stored token still valid")
                return _REFRESH_NOT_NEEDED

            except (requests.RequestException, ValueError, KeyError) as e:
                if attempt < max_retries:
                    logger.warning(
                        t(
                            "logs.auth.token_refresh_retry",
                            attempt=attempt,
                            max_attempts=max_retries,
                        )
                    )
                    time.sleep(attempt * 2)  # Backoff: 2s, 4s
                else:
                    logger.error(t("logs.auth.token_refresh_failed", error=str(e)))

        return None

    @staticmethod
    def validate_access_token(access_token, steam_id=""):
        # check whether an access token is still accepted by Steam
        try:
            url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
            params = {
                "access_token": access_token,
                "include_appinfo": 0,
                "format": "json",
            }
            if steam_id:
                params["steamid"] = steam_id
            resp = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    @staticmethod
    def get_steamid_from_token(access_token):
        # extract SteamID64 by calling GetOwnedGames or decoding the JWT
        try:
            url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
            params = {"access_token": access_token, "include_appinfo": 0, "format": "json"}

            resp = requests.get(url, params=params, timeout=HTTP_TIMEOUT)

            if resp.status_code == 200:
                data = resp.json()
                steam_id = data.get("response", {}).get("steamid")
                if steam_id:
                    logger.info(t("logs.auth.steamid_resolved"))
                    return str(steam_id)

                if "response" in data:
                    logger.info(t("logs.auth.steamid_missing"))
            else:
                logger.info(t("logs.auth.get_owned_games_status", status=resp.status_code))

        except Exception as e:
            # sanitize error message to avoid leaking access token in logs
            if isinstance(e, requests.HTTPError) and e.response is not None:
                safe_msg = "HTTP %s" % e.response.status_code
            else:
                safe_msg = type(e).__name__
            logger.error(t("logs.auth.steamid_from_token_error", error=safe_msg))

        # fallback - decode JWT token
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

    # -- protobuf helpers --

    @staticmethod
    def _encode_refresh_proto(refresh_token, steam_id=""):
        # manually encode GenerateAccessTokenForApp request as protobuf
        buf = bytearray()

        # Field 1: refresh_token (string, field number 1, wire type 2)
        tok_bytes = refresh_token.encode("utf-8")
        buf.append(0x0A)  # tag: (1 << 3) | 2
        TokenStore._write_varint(buf, len(tok_bytes))
        buf.extend(tok_bytes)

        # Field 2: steamid (fixed64, field number 2, wire type 1)
        if steam_id:
            buf.append(0x11)  # tag: (2 << 3) | 1
            buf.extend(int(steam_id).to_bytes(8, byteorder="little"))

        return bytes(buf)

    @staticmethod
    def _decode_string_field(data, field_number):
        # extract a string field from raw protobuf bytes
        pos = 0
        while pos < len(data):
            if pos >= len(data):
                break
            tag_byte = data[pos]
            wire_type = tag_byte & 0x07
            field_num = tag_byte >> 3
            pos += 1

            if wire_type == 2:  # length-delimited (string, bytes)
                length, pos = TokenStore._read_varint(data, pos)
                value = data[pos : pos + length]
                pos += length
                if field_num == field_number:
                    return value.decode("utf-8")
            elif wire_type == 0:  # varint
                _, pos = TokenStore._read_varint(data, pos)
            elif wire_type == 1:  # 64-bit
                pos += 8
            elif wire_type == 5:  # 32-bit
                pos += 4
            else:
                break
        return None

    @staticmethod
    def _read_varint(data, pos):
        # read a varint from bytes at the given position
        result = 0
        shift = 0
        while pos < len(data):
            byte = data[pos]
            pos += 1
            result |= (byte & 0x7F) << shift
            if not (byte & 0x80):
                break
            shift += 7
        return result, pos

    @staticmethod
    def _write_varint(buf, value):
        # write a varint-encoded integer to a byte buffer
        while value > 0x7F:
            buf.append((value & 0x7F) | 0x80)
            value >>= 7
        buf.append(value & 0x7F)

    # -- keyring backend --

    def _save_to_keyring(self, data):
        # store token data in the system keyring
        import keyring  # noqa: F811

        keyring.set_password(self._KEYRING_SERVICE, self._KEYRING_USERNAME, json.dumps(data))
        logger.info(t("logs.auth.token_saved"))
        return True

    def _load_from_keyring(self):
        # load token data from the system keyring
        import keyring  # noqa: F811

        raw = keyring.get_password(self._KEYRING_SERVICE, self._KEYRING_USERNAME)
        if raw is None:
            return None
        return json.loads(raw)

    def _clear_keyring(self):
        # remove tokens from the system keyring
        try:
            import keyring  # noqa: F811

            keyring.delete_password(self._KEYRING_SERVICE, self._KEYRING_USERNAME)
        except (ImportError, RuntimeError, OSError):
            pass  # key may not exist or keyring unavailable

    # -- file-based encrypted backend --

    def _save_to_file(self, data):
        # encrypt and save token data to file using AES-GCM
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
        self.token_file.chmod(0o600)

        logger.info(t("logs.auth.token_saved"))
        return True

    def _load_from_file(self):
        # load and decrypt token data from file
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
    def _get_machine_key():
        # derive a machine-specific key seed from system identity
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
        return "%s:%s" % (machine_id, username)
