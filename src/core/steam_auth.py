# src/core/steam_auth.py

"""
Manages Steam authentication via OpenID.

This module provides Steam OpenID authentication using a local Flask callback server.
It opens the Steam login page in the default browser and handles the callback.
"""
import threading
import webbrowser
from urllib.parse import urlencode

from flask import Flask, request
# noinspection PyPackageRequirements
from werkzeug.serving import make_server

from PyQt6.QtCore import QObject, pyqtSignal
from src.utils.i18n import t


class SteamAuthManager(QObject):
    """
    Manages Steam authentication via OpenID with Flask callback server.

    Opens Steam login in browser and handles the callback via local server.

    Signals:
        auth_success (str): Emitted when authentication succeeds, passes the SteamID64.
        auth_error (str): Emitted when an error occurs during authentication.
        show_waiting_dialog: Emitted to show a waiting dialog in the UI.
        hide_waiting_dialog: Emitted to hide the waiting dialog.
    """

    auth_success = pyqtSignal(str)  # Returns SteamID64
    auth_error = pyqtSignal(str)
    show_waiting_dialog = pyqtSignal()
    hide_waiting_dialog = pyqtSignal()

    def __init__(self):
        """Initializes the SteamAuthManager with Flask callback server."""
        super().__init__()
        self.server = None
        self.server_thread = None
        self.app = Flask(__name__)
        self.port = 5000

        # noinspection HttpUrlsUsage
        self.redirect_uri = f"http://localhost:{self.port}/auth"
        self.app.add_url_rule('/auth', 'auth', self._handle_auth)

    def start_login(self):
        """Starts the Steam OpenID authentication process."""
        print(t('logs.auth.starting'))

        # Start callback server
        self.server_thread = threading.Thread(target=self._run_flask, daemon=True)
        self.server_thread.start()

        # Build OpenID URL
        # noinspection HttpUrlsUsage
        params = {
            'openid.ns': 'http://specs.openid.net/auth/2.0',
            'openid.mode': 'checkid_setup',
            'openid.return_to': self.redirect_uri,
            'openid.realm': f"http://localhost:{self.port}",
            'openid.identity': 'http://specs.openid.net/auth/2.0/identifier_select',
            'openid.claimed_id': 'http://specs.openid.net/auth/2.0/identifier_select'
        }

        auth_url = 'https://steamcommunity.com/openid/login?' + urlencode(params)

        # Show waiting dialog and open browser
        self.show_waiting_dialog.emit()
        webbrowser.open(auth_url)

    def _run_flask(self):
        """Runs the Flask callback server."""
        try:
            self.server = make_server('localhost', self.port, self.app)
            self.server.serve_forever()
        except OSError as e:
            self.auth_error.emit(str(e))

    def _handle_auth(self):
        """Handles the OpenID callback from Steam."""
        claimed_id = request.args.get('openid.claimed_id')

        if claimed_id:
            steam_id_64 = claimed_id.split('/')[-1]

            # Hide waiting dialog and emit success
            self.hide_waiting_dialog.emit()
            self.auth_success.emit(steam_id_64)

            if self.server:
                threading.Thread(target=self.server.shutdown, daemon=True).start()

            return f"""
            <html>
            <body style="background-color:#1b2838; color:white; font-family:sans-serif; text-align:center; padding-top:50px;">
                <h1>{t('ui.login.html_success_header')}</h1>
                <p>{t('ui.login.html_success_msg')}</p>
                <script>window.setTimeout(function(){{ window.close(); }}, 1500);</script>
            </body>
            </html>
            """
        else:
            self.hide_waiting_dialog.emit()
            return t('ui.login.error_no_steam_id')

    def cancel_login(self):
        """Cancels the login process and stops the server."""
        self.hide_waiting_dialog.emit()
        if self.server:
            threading.Thread(target=self.server.shutdown, daemon=True).start()
