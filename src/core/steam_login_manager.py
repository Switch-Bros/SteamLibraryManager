# src/core/steam_login_manager_FIXED.py

"""
FIXED Steam Login Manager with REAL QR Code + Push Notifications.

This is the CORRECT implementation that:
- Generates REAL Steam challenge URLs (not qrserver.com!)
- Supports Push Notifications (not manual 2FA codes!)
- Uses the NEW Steam IAuthenticationService API (2022+)
"""

from __future__ import annotations

import logging
import time

import requests
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from src.core.token_store import TokenStore
from src.utils.i18n import t

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger("steamlibmgr.login_manager")


__all__ = ["SteamLoginManager", "QRCodeLoginThread", "UsernamePasswordLoginThread"]

try:
    import steam.webauth as wa

    WEBAUTH_AVAILABLE = True
except ImportError:
    WEBAUTH_AVAILABLE = False
    wa = None  # steam.webauth not available, using new IAuthenticationService API


def _poll_auth_session(
    client_id: str,
    request_id: str,
    interval: float,
    timeout: float,
    stop_check: Callable[[], bool],
    on_interaction: Callable[[], None] | None = None,
) -> dict | None:
    """Polls the Steam auth session until login completes or times out.

    Used by both QR and password login flows to wait for user approval.
    Calls ``IAuthenticationService/PollAuthSessionStatus/v1/``.

    Args:
        client_id: Steam auth client ID from session start.
        request_id: Request identifier from session start.
        interval: Seconds between poll requests.
        timeout: Maximum total wait time in seconds.
        stop_check: Returns True when polling should abort.
        on_interaction: Called once when remote interaction is detected.

    Returns:
        Dict with steam_id, access_token, refresh_token, account_name
        on success, None on timeout or failure.
    """
    url = "https://api.steampowered.com/IAuthenticationService/PollAuthSessionStatus/v1/"
    start_time = time.time()
    interaction_fired = False

    while not stop_check() and (time.time() - start_time) < timeout:
        try:
            response = requests.post(
                url,
                data={"client_id": client_id, "request_id": request_id},
                timeout=10,
            )
            response.raise_for_status()
            result = response.json().get("response", {})

            if result.get("had_remote_interaction") and on_interaction and not interaction_fired:
                on_interaction()
                interaction_fired = True

            if result.get("access_token"):
                access_token = result["access_token"]
                steam_id = result.get("steamid")
                if not steam_id:
                    steam_id = TokenStore.get_steamid_from_token(access_token)
                if not steam_id:
                    logger.warning(t("logs.auth.could_not_resolve_steamid"))
                    return None

                return {
                    "steam_id": steam_id,
                    "access_token": access_token,
                    "refresh_token": result.get("refresh_token"),
                    "account_name": result.get("account_name"),
                }

            time.sleep(interval)

        except (requests.RequestException, ValueError, KeyError):
            time.sleep(interval)

    return None


class QRCodeLoginThread(QThread):
    """
    Thread for QR code login - FIXED VERSION.

    Signals:
        qr_ready (str): REAL challenge URL (not qrserver URL!)
        login_success (dict): Login succeeded with tokens
        login_error (str): Login failed
        polling_update (str): Status update
    """

    qr_ready = pyqtSignal(str)  # REAL challenge URL
    login_success = pyqtSignal(dict)
    login_error = pyqtSignal(str)
    polling_update = pyqtSignal(str)

    def __init__(self, device_name: str = "SteamLibraryManager"):
        super().__init__()
        self.device_name = device_name
        self._stop_requested = False

    def run(self):
        """Execute QR code login with CORRECT API."""
        try:
            self.polling_update.emit(t("steam.login.status_starting_auth"))

            # Step 1: Start auth session
            client_id, request_id, challenge_url, interval = self._start_qr_session()

            if not challenge_url:
                self.login_error.emit(t("steam.login.error_start_qr_session"))
                return

            # Step 2: Emit REAL challenge URL (no qrserver!)
            self.qr_ready.emit(challenge_url)  # THIS IS THE REAL URL!

            self.polling_update.emit(t("steam.login.status_scan_qr"))

            # Step 3: Poll for completion
            result = _poll_auth_session(
                client_id,
                request_id,
                interval or 5.0,
                300.0,
                stop_check=lambda: self._stop_requested,
                on_interaction=lambda: self.polling_update.emit(t("steam.login.status_waiting_approval")),
            )

            if result:
                logger.info(t("logs.auth.qr_challenge_approved"))
                self.login_success.emit(result)
            else:
                if not self._stop_requested:
                    self.login_error.emit(t("steam.login.error_no_steam_id"))

        except Exception as e:
            self.login_error.emit(t("steam.login.error_qr_failed", error=str(e)))

    def stop(self):
        """Stop polling."""
        self._stop_requested = True

    def _start_qr_session(self):
        """
        Start QR authentication session.

        Returns:
            Tuple: (client_id, request_id, challenge_url, interval)
        """
        url = "https://api.steampowered.com/IAuthenticationService/BeginAuthSessionViaQR/v1/"

        data = {
            "device_friendly_name": self.device_name,
            "platform_type": 2,  # Web browser
        }

        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()

            result = response.json().get("response", {})

            return (
                result.get("client_id"),
                result.get("request_id"),
                result.get("challenge_url"),  # THIS IS THE REAL URL!
                result.get("interval", 5.0),
            )

        except (requests.RequestException, ValueError, KeyError):
            # Error starting QR session - will be shown to user via login_error signal
            return None, None, None, None


class UsernamePasswordLoginThread(QThread):
    """
    Thread for username/password login with Push Notifications.

    THIS IS THE FIXED VERSION that uses Push Notifications instead of manual 2FA!
    """

    login_success = pyqtSignal(dict)
    login_error = pyqtSignal(str)
    waiting_for_approval = pyqtSignal(str)  # NEW: Waiting for mobile approval

    def __init__(self, username: str, password: str):
        super().__init__()
        self.username = username
        self.password = password
        self._stop_requested = False

    def run(self):
        """Execute modern username/password login with Push Notifications."""
        try:
            # Use NEW Steam API for credentials login
            self._login_with_credentials()

        except Exception as e:
            self.login_error.emit(t("steam.login.error_login_failed", error=str(e)))

    def _login_with_credentials(self):
        """
        Login with username/password using NEW Steam API.

        This triggers PUSH NOTIFICATION to Steam Mobile App!
        """
        # Fetch RSA public key for password encryption
        rsa_result = self._fetch_rsa_key(self.username)
        if not rsa_result:
            self.login_error.emit(t("steam.login.error_login_generic"))
            return

        mod, exp, rsa_timestamp = rsa_result
        encrypted_password = self._rsa_encrypt_password(self.password, mod, exp)

        url = "https://api.steampowered.com/IAuthenticationService/BeginAuthSessionViaCredentials/v1/"

        data = {
            "account_name": self.username,
            "encrypted_password": encrypted_password,
            "encryption_timestamp": rsa_timestamp,
            "remember_login": "true",
            "platform_type": 2,  # Web
            "device_friendly_name": "SteamLibraryManager",
        }

        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()

            result = response.json().get("response", {})

            # Check if we need confirmation (Push Notification!)
            allowed_confirmations = result.get("allowed_confirmations", [])

            if any(c.get("confirmation_type") == 3 for c in allowed_confirmations):
                # Type 3 = Device confirmation (Push Notification!)
                self.waiting_for_approval.emit(t("steam.login.status_check_mobile"))

                # Poll for approval
                client_id = result.get("client_id")
                request_id = result.get("request_id")

                if client_id and request_id:
                    final_result = _poll_auth_session(
                        client_id,
                        request_id,
                        5.0,
                        120.0,
                        stop_check=lambda: self._stop_requested,
                    )
                    if final_result:
                        final_result["method"] = "password"
                        self.login_success.emit(final_result)
                    else:
                        self.login_error.emit(t("steam.login.error_mobile_timeout"))
                else:
                    self.login_error.emit(t("steam.login.error_no_session_ids"))
            else:
                # Direct success (no 2FA)
                access_token = result.get("access_token")
                steam_id = result.get("steamid")
                if not steam_id and access_token:
                    steam_id = TokenStore.get_steamid_from_token(access_token)
                if not steam_id:
                    self.login_error.emit(t("steam.login.error_no_steam_id"))
                    return

                self.login_success.emit(
                    {
                        "method": "password",
                        "steam_id": steam_id,
                        "access_token": access_token,
                        "refresh_token": result.get("refresh_token"),
                    }
                )

        except (requests.RequestException, ValueError, KeyError) as e:
            self.login_error.emit(t("steam.login.error_login_generic", error=str(e)))

    @staticmethod
    def _fetch_rsa_key(username: str) -> tuple[str, str, str] | None:
        """Fetch RSA public key from Steam for password encryption.

        Args:
            username: Steam account name.

        Returns:
            Tuple of (modulus_hex, exponent_hex, timestamp) or None on failure.
        """
        url = "https://api.steampowered.com/IAuthenticationService/GetPasswordRSAPublicKey/v1/"
        try:
            response = requests.get(url, params={"account_name": username}, timeout=10)
            response.raise_for_status()
            result = response.json().get("response", {})
            mod = result.get("publickey_mod")
            exp = result.get("publickey_exp")
            timestamp = result.get("timestamp")
            if mod and exp and timestamp:
                logger.info(t("logs.auth.rsa_key_fetched"))
                return mod, exp, str(timestamp)
        except (requests.RequestException, ValueError, KeyError) as e:
            logger.error(t("logs.auth.rsa_key_error", error=str(e)))
        return None

    @staticmethod
    def _rsa_encrypt_password(password: str, mod_hex: str, exp_hex: str) -> str:
        """Encrypt password with Steam's RSA public key.

        Args:
            password: The plaintext password.
            mod_hex: RSA modulus as hexadecimal string.
            exp_hex: RSA exponent as hexadecimal string.

        Returns:
            Base64-encoded RSA-encrypted password.
        """
        import base64

        from Cryptodome.Cipher import PKCS1_v1_5
        from Cryptodome.PublicKey import RSA

        mod = int(mod_hex, 16)
        exp = int(exp_hex, 16)
        rsa_key = RSA.construct((mod, exp))
        cipher = PKCS1_v1_5.new(rsa_key)
        encrypted = cipher.encrypt(password.encode("utf-8"))
        return base64.b64encode(encrypted).decode()

    def stop(self):
        """Stop polling."""
        self._stop_requested = True


class SteamLoginManager(QObject):
    """
    FIXED Steam Login Manager.

    Signals:
        login_success (dict): Successful login
        login_error (str): Login failed
        qr_ready (str): QR challenge URL ready
        status_update (str): Status message
        waiting_for_approval (str): Waiting for mobile approval
    """

    login_success = pyqtSignal(dict)
    login_error = pyqtSignal(str)
    qr_ready = pyqtSignal(str)
    status_update = pyqtSignal(str)
    waiting_for_approval = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.qr_thread: QRCodeLoginThread | None = None
        self.pwd_thread: UsernamePasswordLoginThread | None = None

    def start_qr_login(self, device_name: str = "SteamLibraryManager"):
        """Start QR code login."""
        self.status_update.emit(t("steam.login.status_starting_qr"))

        self.qr_thread = QRCodeLoginThread(device_name)
        # noinspection PyUnresolvedReferences
        self.qr_thread.qr_ready.connect(self.qr_ready.emit)
        # noinspection PyUnresolvedReferences
        self.qr_thread.login_success.connect(lambda r: self._on_login_success(r, "qr"))
        # noinspection PyUnresolvedReferences
        self.qr_thread.login_error.connect(self.login_error.emit)
        # noinspection PyUnresolvedReferences
        self.qr_thread.polling_update.connect(self.status_update.emit)
        self.qr_thread.start()

    def start_password_login(self, username: str, password: str):
        """Start username/password login with Push Notifications."""
        self.status_update.emit(t("steam.login.status_logging_in"))

        self.pwd_thread = UsernamePasswordLoginThread(username, password)
        # noinspection PyUnresolvedReferences
        self.pwd_thread.login_success.connect(lambda r: self._on_login_success(r, "password"))
        # noinspection PyUnresolvedReferences
        self.pwd_thread.login_error.connect(self.login_error.emit)
        # noinspection PyUnresolvedReferences
        self.pwd_thread.waiting_for_approval.connect(self.waiting_for_approval.emit)
        self.pwd_thread.start()

    def cancel_login(self):
        """Cancel login."""
        if self.qr_thread:
            self.qr_thread.stop()
            self.qr_thread.wait()

        if self.pwd_thread:
            self.pwd_thread.stop()
            self.pwd_thread.wait()

    def _on_login_success(self, result: dict, method: str) -> None:
        """Handles successful login from any method (QR or password).

        Args:
            result: Authentication result dict from ``_poll_auth_session``.
            method: Login method identifier (``"qr"`` or ``"password"``).
        """
        self.status_update.emit(t("steam.login.status_success"))
        result["method"] = method
        self.login_success.emit(result)

    @staticmethod
    def get_owned_games(session_or_token, steam_id: str) -> dict | None:
        """Get owned games using token."""
        url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
        params = {
            "steamid": steam_id,
            "include_appinfo": 1,
            "include_played_free_games": 1,
            "include_free_sub": 1,
            "skip_unvetted_apps": 0,
            "format": "json",
        }

        try:
            if isinstance(session_or_token, str):
                # Access token — pass as query parameter, not Bearer header
                params["access_token"] = session_or_token
                response = requests.get(url, params=params, timeout=10)
            else:
                # Session
                response = session_or_token.get(url, params=params, timeout=10)

            response.raise_for_status()
            return response.json().get("response", {})

        except (requests.RequestException, ValueError, KeyError):
            # Error fetching games - return None to signal failure
            return None
