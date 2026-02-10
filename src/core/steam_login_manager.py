# src/core/steam_login_manager.py

"""
Complete Steam Login Manager with QR Code + Username/Password support.

This module provides the COMPLETE Steam login experience:
- QR Code login (scan with Steam Mobile App)
- Username/Password login with 2FA support
- Session cookies for API access
- NO API KEY NEEDED!

Uses the modern Steam IAuthenticationService API.
"""

import time
from typing import Optional, Dict
from urllib.parse import quote

import requests
from PyQt6.QtCore import QObject, pyqtSignal, QThread

try:
    import steam.webauth as wa
    WEBAUTH_AVAILABLE = True
except ImportError:
    WEBAUTH_AVAILABLE = False
    wa = None  # Define in except block to satisfy PyCharm
    print("Warning: steam.webauth not available")


class QRCodeLoginThread(QThread):
    """
    Thread for QR code login to avoid blocking UI.

    Signals:
        qr_ready (str): QR code URL ready to display
        login_success (dict): Login succeeded with tokens
        login_error (str): Login failed with error message
        polling_update (str): Status update during polling
    """

    qr_ready = pyqtSignal(str)  # QR code data URL
    login_success = pyqtSignal(dict)  # {steam_id, access_token, refresh_token, ...}
    login_error = pyqtSignal(str)  # error message
    polling_update = pyqtSignal(str)  # status message

    def __init__(self, device_name: str = "SteamLibraryManager"):
        """
        Initialize QR code login thread.

        Args:
            device_name (str): Friendly name shown in Steam Mobile App
        """
        super().__init__()
        self.device_name = device_name
        self._stop_requested = False

    def run(self):
        """Execute QR code login workflow."""
        try:
            # Step 1: Start authentication session
            self.polling_update.emit("Starting Steam authentication...")

            client_id, request_id, challenge_url, poll_interval = self._start_qr_session()

            if not challenge_url:
                self.login_error.emit("Failed to start QR session!")
                return

            # Step 2: Generate and emit QR code
            qr_url = self._generate_qr_image_url(challenge_url)
            self.qr_ready.emit(qr_url)

            self.polling_update.emit("Scan QR code with Steam Mobile App...")

            # Step 3: Poll for completion
            result = self._poll_for_completion(
                client_id,
                request_id,
                poll_interval or 5.0,
                timeout=300.0  # 5 minutes
            )

            if result:
                self.login_success.emit(result)
            else:
                if not self._stop_requested:
                    self.login_error.emit("Login timeout or canceled!")

        except Exception as e:
            self.login_error.emit(f"QR login failed: {str(e)}")

    def stop(self):
        """Request thread to stop polling."""
        self._stop_requested = True

    def _start_qr_session(self):
        """
        Start Steam QR authentication session.

        Returns:
            Tuple: (client_id, request_id, challenge_url, poll_interval)
        """
        url = "https://api.steampowered.com/IAuthenticationService/BeginAuthSessionViaQR/v1/"

        data = {
            'device_friendly_name': self.device_name,
            'platform_type': 2,  # Web browser
        }

        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()

            result = response.json().get('response', {})

            return (
                result.get('client_id'),
                result.get('request_id'),
                result.get('challenge_url'),
                result.get('interval', 5.0)
            )

        except Exception as e:
            print(f"Error starting QR session: {e}")
            return None, None, None, None

    @staticmethod
    def _generate_qr_image_url(challenge_url: str) -> str:
        """
        Generate QR code image URL from challenge URL.

        Args:
            challenge_url (str): Steam challenge URL

        Returns:
            str: URL to QR code image (via api.qrserver.com)
        """
        encoded_url = quote(challenge_url, safe='')
        return f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded_url}"

    def _poll_for_completion(self, client_id: str, request_id: str,
                             interval: float, timeout: float) -> Optional[Dict]:
        """
        Poll Steam server until user approves login or timeout.

        Args:
            client_id (str): Client ID from BeginAuthSessionViaQR
            request_id (str): Request ID from BeginAuthSessionViaQR
            interval (float): Polling interval in seconds
            timeout (float): Maximum time to wait in seconds

        Returns:
            Optional[Dict]: Login result with tokens, or None if failed
        """
        url = "https://api.steampowered.com/IAuthenticationService/PollAuthSessionStatus/v1/"

        start_time = time.time()

        while not self._stop_requested and (time.time() - start_time) < timeout:
            try:
                data = {
                    'client_id': client_id,
                    'request_id': request_id,
                }

                response = requests.post(url, data=data, timeout=10)
                response.raise_for_status()

                result = response.json().get('response', {})

                # Check if login was approved
                if result.get('had_remote_interaction'):
                    # User scanned QR code!
                    self.polling_update.emit("QR code scanned! Waiting for approval...")

                if result.get('access_token'):
                    # SUCCESS!
                    return {
                        'steam_id': result.get('steamid', result.get('account_name')),
                        'access_token': result.get('access_token'),
                        'refresh_token': result.get('refresh_token'),
                        'account_name': result.get('account_name'),
                    }

                # Wait before next poll
                time.sleep(interval)

            except (requests.RequestException, ValueError, KeyError) as e:
                print(f"Poll error: {e}")
                time.sleep(interval)

        return None


class UsernamePasswordLoginThread(QThread):
    """
    Thread for username/password login with 2FA support.

    Signals:
        login_success (dict): Login succeeded with session
        login_error (str): Login failed
        captcha_required (str): CAPTCHA URL needed
        email_code_required (): Email verification code needed
        twofactor_required (): 2FA code needed (Steam Mobile App)
    """

    login_success = pyqtSignal(dict)  # {session, steam_id}
    login_error = pyqtSignal(str)
    captcha_required = pyqtSignal(str)  # captcha_url
    email_code_required = pyqtSignal()
    twofactor_required = pyqtSignal()

    def __init__(self, username: str, password: str):
        """
        Initialize login thread.

        Args:
            username (str): Steam username
            password (str): Steam password
        """
        super().__init__()
        self.username = username
        self.password = password
        self.user: Optional[wa.WebAuth] = None
        self.captcha_text: Optional[str] = None
        self.email_code: Optional[str] = None
        self.twofactor_code: Optional[str] = None

    def run(self):
        """Execute username/password login."""
        if not WEBAUTH_AVAILABLE:
            self.login_error.emit("steam.webauth not available!")
            return

        try:
            self.user = wa.WebAuth(self.username)
            self._attempt_login()

        except Exception as e:
            self.login_error.emit(f"Login failed: {str(e)}")

    def _attempt_login(self):
        """Attempt login with current credentials."""
        try:
            self.user.login(
                password=self.password,
                captcha=self.captcha_text,
                email_code=self.email_code,
                twofactor_code=self.twofactor_code
            )

            # SUCCESS!
            self._handle_success()

        except wa.CaptchaRequired:
            self.captcha_required.emit(self.user.captcha_url)

        except wa.EmailCodeRequired:
            self.email_code_required.emit()

        except wa.TwoFactorCodeRequired:
            self.twofactor_required.emit()

        except wa.LoginIncorrect:
            self.login_error.emit("Incorrect username or password!")

        except Exception as e:
            self.login_error.emit(f"Login error: {str(e)}")

    def submit_captcha(self, captcha: str):
        """Submit CAPTCHA solution."""
        self.captcha_text = captcha
        self._attempt_login()

    def submit_email_code(self, code: str):
        """Submit email verification code."""
        self.email_code = code
        self._attempt_login()

    def submit_twofactor_code(self, code: str):
        """Submit 2FA code."""
        self.twofactor_code = code
        self._attempt_login()

    def _handle_success(self):
        """Extract session and SteamID after successful login."""
        if not self.user or not self.user.session:
            self.login_error.emit("Login succeeded but no session!")
            return

        # Extract SteamID from session cookies
        steam_id = None
        for cookie in self.user.session.cookies:
            if cookie.name == 'steamLoginSecure':
                value = cookie.value
                if '||' in value:
                    steam_id = value.split('||')[0]
                    break

        if not steam_id:
            # Fallback: Try to get from profile
            try:
                response = self.user.session.get('https://steamcommunity.com/my/profile', timeout=5)
                if '/profiles/' in response.url:
                    steam_id = response.url.split('/profiles/')[-1].rstrip('/')
            except (KeyError, ValueError, TypeError, AttributeError):
                pass

        if not steam_id:
            self.login_error.emit("Could not extract SteamID!")
            return

        self.login_success.emit({
            'session': self.user.session,
            'steam_id': steam_id,
        })


class SteamLoginManager(QObject):
    """
    Complete Steam Login Manager.

    Handles both QR code login and username/password login with full 2FA support.

    Signals:
        login_success (dict): Successful login with session/tokens
        login_error (str): Login failed
        qr_ready (str): QR code ready to display
        status_update (str): Status message during login
        captcha_required (str): CAPTCHA needed (URL)
        email_code_required (): Email code needed
        twofactor_required (): 2FA code needed
    """

    login_success = pyqtSignal(dict)
    login_error = pyqtSignal(str)
    qr_ready = pyqtSignal(str)
    status_update = pyqtSignal(str)
    captcha_required = pyqtSignal(str)
    email_code_required = pyqtSignal()
    twofactor_required = pyqtSignal()

    def __init__(self):
        """Initialize login manager."""
        super().__init__()
        self.qr_thread: Optional[QRCodeLoginThread] = None
        self.pwd_thread: Optional[UsernamePasswordLoginThread] = None

    def start_qr_login(self, device_name: str = "SteamLibraryManager"):
        """
        Start QR code login flow.

        Args:
            device_name (str): Device name shown in Steam Mobile App
        """
        self.status_update.emit("Starting QR code login...")

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
        """
        Start username/password login flow.

        Args:
            username (str): Steam username
            password (str): Steam password
        """
        self.status_update.emit("Logging in with username/password...")

        self.pwd_thread = UsernamePasswordLoginThread(username, password)
        # noinspection PyUnresolvedReferences
        self.pwd_thread.login_success.connect(self._on_pwd_success)
        # noinspection PyUnresolvedReferences
        self.pwd_thread.login_error.connect(self.login_error.emit)
        # noinspection PyUnresolvedReferences
        self.pwd_thread.captcha_required.connect(self.captcha_required.emit)
        # noinspection PyUnresolvedReferences
        self.pwd_thread.email_code_required.connect(self.email_code_required.emit)
        # noinspection PyUnresolvedReferences
        self.pwd_thread.twofactor_required.connect(self.twofactor_required.emit)
        self.pwd_thread.start()

    def submit_captcha(self, captcha_text: str):
        """Submit CAPTCHA solution for password login."""
        if self.pwd_thread:
            self.pwd_thread.submit_captcha(captcha_text)

    def submit_email_code(self, code: str):
        """Submit email verification code for password login."""
        if self.pwd_thread:
            self.pwd_thread.submit_email_code(code)

    def submit_twofactor_code(self, code: str):
        """Submit 2FA code for password login."""
        if self.pwd_thread:
            self.pwd_thread.submit_twofactor_code(code)

    def cancel_login(self):
        """Cancel ongoing login attempt."""
        if self.qr_thread:
            self.qr_thread.stop()
            self.qr_thread.wait()

        if self.pwd_thread:
            self.pwd_thread.terminate()
            self.pwd_thread.wait()

        self.status_update.emit("Login canceled")

    def _on_qr_success(self, result: Dict):
        """Handle successful QR login."""
        self.status_update.emit("QR login successful!")
        self.login_success.emit({
            'method': 'qr',
            'steam_id': result['steam_id'],
            'access_token': result['access_token'],
            'refresh_token': result['refresh_token'],
            'account_name': result.get('account_name'),
        })

    def _on_pwd_success(self, result: Dict):
        """Handle successful password login."""
        self.status_update.emit("Password login successful!")
        self.login_success.emit({
            'method': 'password',
            'steam_id': result['steam_id'],
            'session': result['session'],
        })

    @staticmethod
    def get_owned_games(session_or_token, steam_id: str) -> Optional[Dict]:
        """
        Get owned games using session cookies or access token.

        Args:
            session_or_token: requests.Session object or access token string
            steam_id (str): SteamID64

        Returns:
            Optional[Dict]: Games data or None on failure
        """
        url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
        params = {
            'steamid': steam_id,
            'include_appinfo': 1,
            'include_played_free_games': 1,
            'format': 'json'
        }

        try:
            if isinstance(session_or_token, str):
                # Access token
                headers = {'Authorization': f'Bearer {session_or_token}'}
                response = requests.get(url, params=params, headers=headers, timeout=10)
            else:
                # Session object
                response = session_or_token.get(url, params=params, timeout=10)

            response.raise_for_status()
            return response.json().get('response', {})

        except Exception as e:
            print(f"Error fetching owned games: {e}")
            return None