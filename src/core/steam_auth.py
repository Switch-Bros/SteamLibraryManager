"""
Steam Authentication Manager - Clean Localized Strings
Speichern als: src/core/steam_auth.py
"""
import threading
import sys
from flask import Flask, request
from werkzeug.serving import make_server
from PyQt6.QtCore import QObject, pyqtSignal
from src.config import config
from src.utils.i18n import t

try:
    import webview

    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False
    print(t('logs.auth.webview_missing'))  # Localized log
    import webbrowser


class SteamAuthManager(QObject):
    auth_success = pyqtSignal(str)
    auth_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.server = None
        self.server_thread = None
        self.app = Flask(__name__)
        self.port = 5000
        self.redirect_uri = f"http://localhost:{self.port}/auth"

        self.app.add_url_rule('/auth', 'auth', self._handle_auth)

    def start_login(self):
        if not config.STEAM_CLIENT_ID:
            print(t('logs.auth.client_id_missing'))  # Localized log

        self.server_thread = threading.Thread(target=self._run_flask)
        self.server_thread.daemon = True
        self.server_thread.start()

        auth_url = (
            "https://steamcommunity.com/oauth/login?"
            "response_type=code&"
            f"client_id={config.STEAM_CLIENT_ID}&"
            "state=steam_library_manager_login&"
            f"redirect_uri={self.redirect_uri}"
        )

        print(t('logs.auth.starting'))  # Localized log

        if HAS_WEBVIEW:
            # Title jetzt aus locale
            t_thread = threading.Thread(
                target=lambda: webview.create_window(t('ui.auth.window_title'), auth_url, width=800, height=600))
            t_thread.start()
        else:
            import webbrowser
            webbrowser.open(auth_url)

    def _run_flask(self):
        try:
            self.server = make_server('localhost', self.port, self.app)
            print(t('logs.auth.server_started', port=self.port))
            self.server.serve_forever()
        except Exception as e:
            self.auth_error.emit(str(e))

    def _handle_auth(self):
        code = request.args.get('code')

        if code:
            self.auth_success.emit(code)
            threading.Thread(target=self.server.shutdown).start()

            # Localized HTML Response
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
            error_msg = t('ui.auth.error_no_code')
            self.auth_error.emit(error_msg)
            return t('ui.auth.browser_error')