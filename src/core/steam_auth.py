"""
Steam Authentication Manager - Clean Localized Strings
Speichern als: src/core/steam_auth.py
"""
import threading
from flask import Flask, request
# noinspection PyPackageRequirements
from werkzeug.serving import make_server
from PyQt6.QtCore import QObject, pyqtSignal
from src.utils.i18n import t
from urllib.parse import urlencode
import webbrowser

# Importe basierend auf requirements
try:
    import webview

    HAS_WEBVIEW = True
except ImportError:
    webview = None
    HAS_WEBVIEW = False
    print(t('logs.auth.webview_missing'))


class SteamAuthManager(QObject):
    auth_success = pyqtSignal(str)  # Gibt SteamID64 zurück
    auth_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.server = None
        self.server_thread = None
        self.app = Flask(__name__)
        self.port = 5000
        # noinspection HttpUrlsUsage
        self.redirect_uri = f"http://localhost:{self.port}/auth"

        # Flask Route
        self.app.add_url_rule('/auth', 'auth', self._handle_auth)

    def start_login(self):
        """Startet den OpenID Prozess"""
        # 1. Server starten
        self.server_thread = threading.Thread(target=self._run_flask)
        self.server_thread.daemon = True
        self.server_thread.start()

        # 2. OpenID URL bauen
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

        # 3. Browser öffnen
        if HAS_WEBVIEW and webview:
            threading.Thread(target=lambda: self._open_webview(auth_url)).start()
        else:
            webbrowser.open(auth_url)

    @staticmethod
    def _open_webview(url):
        """Öffnet ein natives Fenster (falls webview installiert)"""
        try:
            webview.create_window('Steam Login', url, width=800, height=600, resizable=False)
            webview.start()
        except Exception as e:
            print(f"Webview error: {e}")
            webbrowser.open(url)

    def _run_flask(self):
        try:
            self.server = make_server('localhost', self.port, self.app)
            print(t('logs.auth.server_started', port=self.port))
            self.server.serve_forever()
        except OSError as e:
            self.auth_error.emit(str(e))

    def _handle_auth(self):
        """Callback für OpenID"""
        # Steam sendet die ID im Parameter 'openid.claimed_id'
        claimed_id = request.args.get('openid.claimed_id')

        if claimed_id:
            # Format ist: https://steamcommunity.com/openid/id/7656119xxxxxxxxxx
            steam_id_64 = claimed_id.split('/')[-1]

            self.auth_success.emit(steam_id_64)

            # Server sauber beenden
            if self.server:
                threading.Thread(target=self.server.shutdown).start()

            # Webview schließen (falls aktiv)
            if HAS_WEBVIEW and webview:
                pass

            # HTML Response
            return f"""
            <html>
            <body style="background-color:#1b2838; color:white; font-family:sans-serif; text-align:center; padding-top:50px;">
                <h1>{t('ui.login.html_success_header')}</h1>
                <p>{t('ui.auth.success_browser')}</p>
                <script>window.setTimeout(function(){{window.close();}}, 2000);</script>
            </body>
            </html>
            """
        else:
            return "Login failed or cancelled."