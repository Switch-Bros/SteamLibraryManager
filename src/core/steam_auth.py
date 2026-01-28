# src/core/steam_auth.py

"""
Manages Steam authentication via OpenID.

This module uses Flask to handle the OAuth callback securely. It provides a
QObject-based manager that can be integrated into PyQt6 applications to handle
Steam login via OpenID.
"""
import threading
import webbrowser
from urllib.parse import urlencode

from flask import Flask, request
# noinspection PyPackageRequirements
from werkzeug.serving import make_server

from PyQt6.QtCore import QObject, pyqtSignal
from src.utils.i18n import t

# Optional: PyWebview for a better-looking window
try:
    import webview
    HAS_WEBVIEW = True
except ImportError:
    webview = None
    HAS_WEBVIEW = False


class SteamAuthManager(QObject):
    """
    Manages Steam authentication via OpenID with Flask callback server.

    This class starts a local Flask server to handle the OpenID callback from
    Steam, opens the Steam login page in a browser (or webview), and emits
    signals when authentication succeeds or fails.

    Signals:
        auth_success (str): Emitted when authentication succeeds, passes the SteamID64.
        auth_error (str): Emitted when an error occurs during authentication.
    """

    auth_success = pyqtSignal(str)  # Returns SteamID64
    auth_error = pyqtSignal(str)

    def __init__(self):
        """
        Initializes the SteamAuthManager.

        Sets up the Flask app and configures the OpenID callback route.
        """
        super().__init__()
        self.server = None
        self.server_thread = None
        self.app = Flask(__name__)
        self.port = 5000

        # Steam prefers "localhost" over "127.0.0.1" for redirects
        # noinspection HttpUrlsUsage
        self.redirect_uri = f"http://localhost:{self.port}/auth"

        # Register Flask route
        self.app.add_url_rule('/auth', 'auth', self._handle_auth)

    def start_login(self):
        """
        Starts the Steam OpenID authentication process.

        This method:
        1. Starts a Flask server in a background thread to handle the callback
        2. Builds the Steam OpenID URL
        3. Opens the URL in a browser (or webview if available)
        """
        # 1. Start server in thread
        self.server_thread = threading.Thread(target=self._run_flask)
        self.server_thread.daemon = True
        self.server_thread.start()

        print(t('logs.auth.starting'))

        # 2. Build OpenID URL (Standard)
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

        # 3. Open browser
        if HAS_WEBVIEW and webview:
            threading.Thread(target=lambda: self._open_webview(auth_url)).start()
        else:
            webbrowser.open(auth_url)

    @staticmethod
    def _open_webview(url):
        """
        Opens the Steam login page in a native webview window.

        This method is used when the pywebview library is available. It provides
        a better user experience than opening the default browser.

        Args:
            url (str): The Steam OpenID login URL.
        """
        try:
            webview.create_window('Steam Login', url, width=800, height=800, resizable=False)
            webview.start()
        except Exception as e:
            print(f"Webview error: {e}")
            webbrowser.open(url)

    def _run_flask(self):
        """
        Runs the Flask server in a background thread.

        This method starts the Flask server and keeps it running until the
        authentication callback is received or an error occurs.
        """
        try:
            # Threaded server setup
            self.server = make_server('localhost', self.port, self.app)
            self.server.serve_forever()
        except OSError as e:
            self.auth_error.emit(str(e))

    def _handle_auth(self):
        """
        Handles the OpenID callback from Steam.

        This method is called when Steam redirects the user back to the local
        server after authentication. It extracts the SteamID64 from the callback
        parameters and emits the auth_success signal.

        Returns:
            str: An HTML response to display in the browser.
        """
        # Steam sends the ID in the 'openid.claimed_id' parameter
        claimed_id = request.args.get('openid.claimed_id')

        if claimed_id:
            # Format is: https://steamcommunity.com/openid/id/7656119xxxxxxxxxx
            steam_id_64 = claimed_id.split('/')[-1]

            self.auth_success.emit(steam_id_64)

            # Shutdown server cleanly in a separate thread to not block response
            if self.server:
                threading.Thread(target=self.server.shutdown).start()

            # Close webview (if active) - Hacky exit for webview
            if HAS_WEBVIEW and webview:
                # Webview needs to be closed from main thread usually,
                # but sending a window.close() script helps
                pass

            # HTML Response
            return f"""
            <html>
            <body style="background-color:#1b2838; color:white; font-family:sans-serif; text-align:center; padding-top:50px;">
                <h1>{t('ui.login.html_success_header')}</h1>
                <p>{t('ui.login.html_success_msg')}</p>
                <script>
                    window.setTimeout(function(){{ window.close(); }}, 3000);
                </script>
            </body>
            </html>
            """
        else:
            return "Login failed or cancelled."
