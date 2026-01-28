"""
Steam Authentication Manager
Handles the OAuth login flow via system browser and local callback server.
"""
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtNetwork import QTcpServer

from src.utils.i18n import t


class SteamAuthManager(QObject):
    """
    Manages Steam OpenID login process.
    Starts a local TCP server to listen for the Steam callback.
    """
    auth_success = pyqtSignal(str)  # Emits SteamID64
    auth_error = pyqtSignal(str)  # Emits Error Message

    def __init__(self):
        super().__init__()
        self.server: Optional[QTcpServer] = None
        self.port = 8888
        self._is_running = False

    def start_login(self) -> None:
        """Starts the login process: opens browser and starts listener."""
        if self._is_running:
            return

        try:
            self._start_server()

            print(t('logs.auth.starting'))

            # noinspection HttpUrlsUsage
            callback_url = f"http://127.0.0.1:{self.port}/callback"

            # noinspection HttpUrlsUsage
            steam_openid_url = (
                "https://steamcommunity.com/openid/login"
                "?openid.ns=http://specs.openid.net/auth/2.0"
                "&openid.mode=checkid_setup"
                f"&openid.return_to={callback_url}"
                f"&openid.realm={callback_url}"
                "&openid.identity=http://specs.openid.net/auth/2.0/identifier_select"
                "&openid.claimed_id=http://specs.openid.net/auth/2.0/identifier_select"
            )

            QDesktopServices.openUrl(QUrl(steam_openid_url))

        except OSError as e:
            self.auth_error.emit(t('logs.auth.error', error=str(e)))
            self._stop_server()

    def _start_server(self) -> None:
        """Starts local TCP server to catch the redirect."""
        self.server = QTcpServer()
        # noinspection PyUnresolvedReferences
        self.server.newConnection.connect(self._handle_connection)

        if not self.server.listen(port=self.port):
            raise OSError(f"Could not start local server on port {self.port}")

        self._is_running = True

    def _handle_connection(self) -> None:
        """Handles incoming HTTP request from browser redirect."""
        if not self.server: return

        client_connection = self.server.nextPendingConnection()
        if not client_connection: return

        # Wait for data (simplified)
        client_connection.waitForReadyRead(1000)
        request_data = client_connection.readAll().data().decode('utf-8', errors='ignore')

        steam_id = self._extract_steam_id(request_data)

        response_body = "<h1>Login Successful!</h1><p>You can close this window and return to the app.</p>"
        if not steam_id:
            response_body = "<h1>Login Failed</h1><p>Could not verify SteamID.</p>"

        # noinspection HttpUrlsUsage
        http_response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/html\r\n"
            "Connection: close\r\n"
            f"Content-Length: {len(response_body)}\r\n"
            "\r\n"
            f"{response_body}"
        )

        client_connection.write(http_response.encode('utf-8'))
        client_connection.flush()
        client_connection.disconnectFromHost()

        self._stop_server()

        if steam_id:
            self.auth_success.emit(steam_id)
        else:
            self.auth_error.emit(t('logs.auth.error', error="Invalid OpenID response"))

    def _stop_server(self) -> None:
        """Stops the local server."""
        if self.server:
            self.server.close()
            self.server = None
        self._is_running = False

    @staticmethod
    def _extract_steam_id(request_data: str) -> Optional[str]:
        """Parses the SteamID64 from the HTTP GET request."""
        try:
            if "openid.claimed_id" not in request_data:
                return None

            import re
            match = re.search(r"openid/id/(\d{17})", request_data)
            if match:
                return match.group(1)
        except Exception as e:
            print(f"Error parsing SteamID: {e}")
        return None