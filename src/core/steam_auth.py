"""
Steam Authentication Manager
Uses Flask to handle the OAuth callback securely.
"""
import threading
import webbrowser
from urllib.parse import urlencode

# Diese Imports verursachten die roten Fehler - nach 'pip install flask' sind sie weg
from flask import Flask, request
# noinspection PyPackageRequirements
from werkzeug.serving import make_server

from PyQt6.QtCore import QObject, pyqtSignal
from src.utils.i18n import t

# Optional: PyWebview für schöneres Fenster
try:
    import webview

    HAS_WEBVIEW = True
except ImportError:
    webview = None
    HAS_WEBVIEW = False


class SteamAuthManager(QObject):
    auth_success = pyqtSignal(str)  # Returns SteamID64
    auth_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.server = None
        self.server_thread = None
        self.app = Flask(__name__)
        self.port = 5000

        # Steam mag "localhost" lieber als "127.0.0.1" bei Redirects
        # noinspection HttpUrlsUsage
        self.redirect_uri = f"http://localhost:{self.port}/auth"

        # Flask Route registrieren
        self.app.add_url_rule('/auth', 'auth', self._handle_auth)

    def start_login(self):
        """Starts the OpenID process"""
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
        """Opens native window (if webview installed)"""
        try:
            webview.create_window('Steam Login', url, width=800, height=800, resizable=False)
            webview.start()
        except Exception as e:
            print(f"Webview error: {e}")
            webbrowser.open(url)

    def _run_flask(self):
        """Runs the Flask server."""
        try:
            # Threaded server setup
            self.server = make_server('localhost', self.port, self.app)
            self.server.serve_forever()
        except OSError as e:
            self.auth_error.emit(str(e))

    def _handle_auth(self):
        """Callback for OpenID"""
        # Steam sendet die ID im Parameter 'openid.claimed_id'
        claimed_id = request.args.get('openid.claimed_id')

        if claimed_id:
            # Format ist: https://steamcommunity.com/openid/id/7656119xxxxxxxxxx
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