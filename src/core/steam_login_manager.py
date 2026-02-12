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

from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.login_manager")


__all__ = ["SteamLoginManager", "QRCodeLoginThread", "UsernamePasswordLoginThread"]

try:
    import steam.webauth as wa

    WEBAUTH_AVAILABLE = True
except ImportError:
    WEBAUTH_AVAILABLE = False
    wa = None  # steam.webauth not available, using new IAuthenticationService API


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
            self.polling_update.emit(t("ui.login.status_starting_auth"))

            # Step 1: Start auth session
            client_id, request_id, challenge_url, interval = self._start_qr_session()

            if not challenge_url:
                self.login_error.emit(t("ui.login.error_start_qr_session"))
                return

            # Step 2: Emit REAL challenge URL (no qrserver!)
            self.qr_ready.emit(challenge_url)  # THIS IS THE REAL URL!

            self.polling_update.emit(t("ui.login.status_scan_qr"))

            # Step 3: Poll for completion
            result = self._poll_for_completion(client_id, request_id, interval or 5.0, timeout=300.0)

            if result:
                self.login_success.emit(result)
            else:
                if not self._stop_requested:
                    # Could be timeout OR failed to get steam_id
                    self.login_error.emit(t("ui.login.error_no_steam_id"))

        except Exception as e:
            self.login_error.emit(t("ui.login.error_qr_failed", error=str(e)))

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

    def _poll_for_completion(self, client_id: str, request_id: str, interval: float, timeout: float) -> dict | None:
        """Poll until user approves or timeout."""
        url = "https://api.steampowered.com/IAuthenticationService/PollAuthSessionStatus/v1/"

        start_time = time.time()

        while not self._stop_requested and (time.time() - start_time) < timeout:
            try:
                data = {
                    "client_id": client_id,
                    "request_id": request_id,
                }

                response = requests.post(url, data=data, timeout=10)
                response.raise_for_status()

                result = response.json().get("response", {})

                if result.get("had_remote_interaction"):
                    self.polling_update.emit(t("ui.login.status_waiting_approval"))

                if result.get("access_token"):
                    # SUCCESS! But we need to get the actual SteamID64!
                    access_token = result.get("access_token")
                    logger.info(t("logs.auth.qr_challenge_approved"))

                    # Get SteamID64 using the access token
                    steam_id_64 = SteamLoginManager.get_steamid_from_token(access_token)

                    if not steam_id_64:
                        # CRITICAL: Cannot proceed without valid SteamID64
                        logger.info(t("logs.auth.could_not_resolve_steamid"))
                        # Return None to trigger error in run() method
                        return None

                    return {
                        "steam_id": steam_id_64,
                        "access_token": access_token,
                        "refresh_token": result.get("refresh_token"),
                        "account_name": result.get("account_name"),
                    }

                time.sleep(interval)

            except (requests.RequestException, ValueError, KeyError):
                # Poll error - retry after interval
                time.sleep(interval)

        return None


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
            self.login_error.emit(t("ui.login.error_login_failed", error=str(e)))

    def _login_with_credentials(self):
        """
        Login with username/password using NEW Steam API.

        This triggers PUSH NOTIFICATION to Steam Mobile App!
        """
        url = "https://api.steampowered.com/IAuthenticationService/BeginAuthSessionViaCredentials/v1/"

        data = {
            "account_name": self.username,
            "encrypted_password": self._encrypt_password(self.password),
            "encryption_timestamp": str(int(time.time())),
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
                self.waiting_for_approval.emit(t("ui.login.status_check_mobile"))

                # Poll for approval
                client_id = result.get("client_id")
                request_id = result.get("request_id")

                if client_id and request_id:
                    final_result = self._poll_for_credentials_approval(client_id, request_id)
                    if final_result:
                        self.login_success.emit(final_result)
                    else:
                        self.login_error.emit(t("ui.login.error_mobile_timeout"))
                else:
                    self.login_error.emit(t("ui.login.error_no_session_ids"))
            else:
                # Direct success (no 2FA)
                self.login_success.emit(
                    {
                        "method": "password",
                        "steam_id": result.get("steamid"),
                        "access_token": result.get("access_token"),
                        "refresh_token": result.get("refresh_token"),
                    }
                )

        except (requests.RequestException, ValueError, KeyError) as e:
            self.login_error.emit(t("ui.login.error_login_generic", error=str(e)))

    def _poll_for_credentials_approval(self, client_id: str, request_id: str) -> dict | None:
        """Poll for mobile approval."""
        url = "https://api.steampowered.com/IAuthenticationService/PollAuthSessionStatus/v1/"

        start_time = time.time()
        timeout = 120.0  # 2 minutes for approval

        while not self._stop_requested and (time.time() - start_time) < timeout:
            try:
                data = {
                    "client_id": client_id,
                    "request_id": request_id,
                }

                response = requests.post(url, data=data, timeout=10)
                response.raise_for_status()

                result = response.json().get("response", {})

                if result.get("access_token"):
                    return {
                        "method": "password",
                        "steam_id": result.get("steamid") or result.get("account_name"),
                        "access_token": result.get("access_token"),
                        "refresh_token": result.get("refresh_token"),
                    }

                time.sleep(5.0)

            except (requests.RequestException, ValueError, KeyError):
                time.sleep(5.0)

        return None

    @staticmethod
    def _encrypt_password(password: str) -> str:
        """Encrypt password for Steam API.

        .. warning::
            SECURITY: This is a Base64 placeholder, NOT real encryption!
            Steam requires RSA encryption using a per-session public key
            fetched from ``IAuthenticationService/GetPasswordRSAPublicKey``.
            Must be replaced in Phase 2 (Auth Hardening).

        Args:
            password: The plaintext password.

        Returns:
            Base64-encoded password (insecure placeholder).
        """
        # FIXME(phase-2): Replace with proper RSA encryption via
        # IAuthenticationService/GetPasswordRSAPublicKey
        import base64

        return base64.b64encode(password.encode()).decode()

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
        self.status_update.emit(t("ui.login.status_starting_qr"))

        self.qr_thread = QRCodeLoginThread(device_name)
        # noinspection PyUnresolvedReferences
        self.qr_thread.qr_ready.connect(self.qr_ready.emit)
        # noinspection PyUnresolvedReferences
        self.qr_thread.login_success.connect(self._on_qr_success)
        # noinspection PyUnresolvedReferences
        self.qr_thread.login_error.connect(self.login_error.emit)
        # noinspection PyUnresolvedReferences
        self.qr_thread.polling_update.connect(self.status_update.emit)
        self.qr_thread.start()

    def start_password_login(self, username: str, password: str):
        """Start username/password login with Push Notifications."""
        self.status_update.emit(t("ui.login.status_logging_in"))

        self.pwd_thread = UsernamePasswordLoginThread(username, password)
        # noinspection PyUnresolvedReferences
        self.pwd_thread.login_success.connect(self._on_pwd_success)
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

    def _on_qr_success(self, result: dict):
        """Handle QR success."""
        self.status_update.emit(t("ui.login.status_success"))
        self.login_success.emit(
            {
                "method": "qr",
                "steam_id": result["steam_id"],
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
                "account_name": result.get("account_name"),
            }
        )

    def _on_pwd_success(self, result: dict):
        """Handle password success."""
        self.status_update.emit(t("ui.login.status_success"))
        self.login_success.emit(result)

    @staticmethod
    def get_steamid_from_token(access_token: str) -> str | None:
        """Extract SteamID64 by calling GetOwnedGames with the access token.

        The GetOwnedGames API will return the SteamID of the authenticated user
        even if we don't provide a steamid parameter!

        Args:
            access_token: The Steam access token

        Returns:
            SteamID64 as string, or None if failed
        """
        # Method 1: Try GetOwnedGames
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

        # Method 2: FALLBACK - Try to decode JWT token
        # Steam access tokens are JWTs that contain the steam_id!
        try:
            import base64
            import json

            # JWT format: header.payload.signature
            parts = access_token.split(".")
            if len(parts) >= 2:
                # Decode payload (add padding if needed)
                payload = parts[1]
                payload += "=" * (4 - len(payload) % 4)
                decoded = base64.urlsafe_b64decode(payload)
                data = json.loads(decoded)

                # Check for steam_id in various fields
                steam_id = data.get("sub") or data.get("steamid") or data.get("steam_id")
                if steam_id:
                    logger.info(t("logs.auth.steamid_from_jwt"))
                    return str(steam_id)

        except Exception as e:
            logger.error(t("logs.auth.jwt_decode_failed", error=str(e)))

        return None

    @staticmethod
    def _get_steamid_from_account_name(account_name: str) -> str | None:
        """Convert account name to SteamID64 using Steam Community API.

        Args:
            account_name: Steam account name (login name)

        Returns:
            SteamID64 as string, or None if failed
        """
        try:
            # Try ResolveVanityURL API
            url = "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/"
            params = {"key": "YOUR_API_KEY_HERE", "vanityurl": account_name}  # This won't work without API key

            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                steam_id = data.get("response", {}).get("steamid")
                if steam_id:
                    logger.info(t("logs.auth.account_name_resolved"))
                    return str(steam_id)

        except Exception as e:
            logger.error(t("logs.auth.account_name_resolve_error", error=str(e)))

        return None

    @staticmethod
    def get_owned_games(session_or_token, steam_id: str) -> dict | None:
        """Get owned games using token."""
        url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
        params = {"steamid": steam_id, "include_appinfo": 1, "include_played_free_games": 1, "format": "json"}

        try:
            if isinstance(session_or_token, str):
                # Access token
                headers = {"Authorization": f"Bearer {session_or_token}"}
                response = requests.get(url, params=params, headers=headers, timeout=10)
            else:
                # Session
                response = session_or_token.get(url, params=params, timeout=10)

            response.raise_for_status()
            return response.json().get("response", {})

        except (requests.RequestException, ValueError, KeyError):
            # Error fetching games - return None to signal failure
            return None
