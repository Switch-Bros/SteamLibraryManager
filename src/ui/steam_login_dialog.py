# src/ui/steam_login_dialog.py

"""
Steam login dialog with OpenID authentication.

This module provides a dialog that handles Steam login via OpenID 2.0 protocol.
It starts a local HTTP server to receive the callback and opens the Steam login
page in the user's browser.
"""

import threading
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox
)

from src.utils.i18n import t


class SteamOpenIDHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler for Steam OpenID callbacks.

    This handler processes the OpenID callback from Steam and extracts the
    Steam ID from the response parameters.

    Attributes:
        steam_id (Optional[str]): Class variable storing the extracted Steam ID.
    """

    steam_id: Optional[str] = None

    # noinspection PyPep8Naming
    def do_GET(self):
        """
        Handles GET requests from the Steam OpenID callback.

        This method is called by the HTTP server when Steam redirects back to
        the local callback URL. It extracts the Steam ID and sends a success
        page to the browser.

        Note:
            Method name must be exactly 'do_GET' as required by BaseHTTPRequestHandler.
        """
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if 'openid.claimed_id' in params:
            claimed_id = params['openid.claimed_id'][0]
            if '/id/' in claimed_id:
                found_id = claimed_id.split('/id/')[-1]
                SteamOpenIDHandler.steam_id = found_id

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        html = f"""
        <html>
        <head><title>{t('ui.login.html_success_title')}</title></head>
        <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px; 
                     background-color: #1b2838; color: white;">
            <h1>{t('ui.login.html_success_header')}</h1>
            <p>{t('ui.login.html_success_message')}</p>
            <p style="font-size: 0.8em; color: #888;">{t('ui.login.html_close_info')}</p>
            <script>window.setTimeout(function(){{ window.close(); }}, 1500);</script>
        </body>
        </html>
        """
        self.wfile.write(html.encode('utf-8'))

    # noinspection PyPep8Naming
    def log_message(self, log_format, *args):
        """
        Suppresses HTTP server log output.

        Note:
            Method name must be exactly 'log_message' as required by BaseHTTPRequestHandler.
        """
        pass


class SteamLoginDialog(QDialog):
    """
    Dialog for Steam login via OpenID authentication.

    This dialog starts a local HTTP server to handle the OpenID callback,
    opens the Steam login page in the user's browser, and waits for the
    authentication to complete.

    Signals:
        login_successful (str): Emitted when login succeeds, passes the Steam ID.

    Attributes:
        steam_id (Optional[str]): The Steam ID after successful login.
        server (Optional[HTTPServer]): The local HTTP server for callbacks.
        server_thread (Optional[threading.Thread]): Thread running the HTTP server.
        check_timer (Optional[QTimer]): Timer for checking login status.
    """

    # Signal for successful login
    login_successful = pyqtSignal(str)

    def __init__(self, parent=None):
        """
        Initializes the Steam login dialog.

        Args:
            parent: Parent widget. Defaults to None.
        """
        super().__init__(parent)

        self.setWindowTitle(t('ui.login.window_title_emoji'))
        self.setMinimumWidth(400)
        self.setModal(True)

        self.steam_id: Optional[str] = None
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None
        self.check_timer: Optional[QTimer] = None

        self._create_ui()

    def _create_ui(self):
        """Creates the user interface for the dialog."""
        layout = QVBoxLayout(self)

        title = QLabel(t('ui.login.window_title_emoji'))
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        info = QLabel(t('ui.login.info'))
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        login_btn = QPushButton(t('ui.login.btn_login'))
        login_btn.setMinimumHeight(50)
        # noinspection PyUnresolvedReferences
        login_btn.clicked.connect(self._start_login)
        layout.addWidget(login_btn)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton(t('ui.dialogs.cancel'))
        # noinspection PyUnresolvedReferences
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _start_login(self):
        """
        Starts the Steam login process.

        This method starts a local HTTP server, constructs the OpenID URL,
        and opens it in the user's default browser.
        """
        self.status_label.setText(t('ui.login.status_waiting'))

        try:
            # HTTPServer expects the class as callable - PyCharm Type-Check Issue
            # noinspection PyTypeChecker
            self.server = HTTPServer(('127.0.0.1', 8080), SteamOpenIDHandler)

            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()

            # OpenID 2.0 requires http:// for localhost callbacks
            # noinspection HttpUrlsUsage
            return_url = "http://127.0.0.1:8080/auth/callback"
            # noinspection HttpUrlsUsage
            realm = "http://127.0.0.1:8080"

            # noinspection HttpUrlsUsage
            openid_params = {
                'openid.ns': 'http://specs.openid.net/auth/2.0',
                'openid.mode': 'checkid_setup',
                'openid.return_to': return_url,
                'openid.realm': realm,
                'openid.identity': 'http://specs.openid.net/auth/2.0/identifier_select',
                'openid.claimed_id': 'http://specs.openid.net/auth/2.0/identifier_select'
            }

            # The actual Steam login happens securely via HTTPS
            steam_url = 'https://steamcommunity.com/openid/login?' + urllib.parse.urlencode(openid_params)

            self.status_label.setText(t('ui.login.status_browser'))
            webbrowser.open(steam_url)

            self.check_timer = QTimer()
            # noinspection PyUnresolvedReferences
            self.check_timer.timeout.connect(self._check_login)
            self.check_timer.start(500)

        except OSError as e:
            QMessageBox.critical(self, t('ui.login.error_title'), t('ui.login.error_msg', error=str(e)))
            self.status_label.setText(t('ui.login.status_failed'))

    def _run_server(self):
        """
        Runs the HTTP server in a background thread.

        This method handles a single HTTP request (the OpenID callback).
        """
        if self.server:
            try:
                self.server.handle_request()
            except (OSError, ValueError):
                pass

    def _check_login(self):
        """
        Checks if the login has completed successfully.

        This method is called periodically by a timer to check if the Steam ID
        has been extracted from the callback. If successful, it emits the
        login_successful signal and closes the dialog.
        """
        if SteamOpenIDHandler.steam_id:
            self.steam_id = SteamOpenIDHandler.steam_id
            if self.check_timer:
                self.check_timer.stop()

            self.status_label.setText(t('ui.login.status_success', id=self.steam_id))

            # noinspection PyUnresolvedReferences
            self.login_successful.emit(self.steam_id)

            QTimer.singleShot(1000, self.accept)

    def get_steam_id(self) -> Optional[str]:
        """
        Gets the Steam ID after successful login.

        Returns:
            Optional[str]: The Steam ID, or None if login has not completed.
        """
        return self.steam_id

    def closeEvent(self, event):
        """
        Handles the dialog close event.

        This method cleans up the timer and HTTP server when the dialog is closed.

        Args:
            event: The close event.
        """
        if self.check_timer:
            self.check_timer.stop()
        if self.server:
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        super().closeEvent(event)
