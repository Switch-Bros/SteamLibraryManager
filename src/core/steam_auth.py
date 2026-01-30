# src/core/steam_auth.py

"""
Manages Steam authentication via OpenID.

This module uses pywebview to display the Steam login page in an embedded window.
It provides a QObject-based manager that can be integrated into PyQt6 applications
to handle Steam login via OpenID.
"""
import threading
import webbrowser
from urllib.parse import urlencode, urlparse, parse_qs

from flask import Flask, request
# noinspection PyPackageRequirements
from werkzeug.serving import make_server

from PyQt6.QtCore import QObject, pyqtSignal
from src.utils.i18n import t

# pywebview for embedded login window
try:
    import webview
    HAS_WEBVIEW = True
except ImportError:
    webview = None
    HAS_WEBVIEW = False


class SteamAuthManager(QObject):
    """
    Manages Steam authentication via OpenID with embedded webview window.

    This class opens a pywebview window for Steam login and monitors URL changes
    to detect successful authentication. Falls back to browser if pywebview is
    not available.

    Signals:
        auth_success (str): Emitted when authentication succeeds, passes the SteamID64.
        auth_error (str): Emitted when an error occurs during authentication.
    """

    auth_success = pyqtSignal(str)  # Returns SteamID64
    auth_error = pyqtSignal(str)

    def __init__(self):
        """
        Initializes the SteamAuthManager.

        Sets up the Flask app for fallback browser auth and configures callback route.
        """
        super().__init__()
        self.server = None
        self.server_thread = None
        self.webview_window = None
        self._auth_completed = False
        self.app = Flask(__name__)
        self.port = 5000

        # Steam prefers "localhost" over "127.0.0.1" for redirects
        # noinspection HttpUrlsUsage
        self.redirect_uri = f"http://localhost:{self.port}/auth"

        # Register Flask route for fallback browser auth
        self.app.add_url_rule('/auth', 'auth', self._handle_auth)

    def start_login(self):
        """
        Starts the Steam OpenID authentication process.

        Uses pywebview for embedded login window if available,
        otherwise falls back to browser with Flask callback server.
        """
        print(t('logs.auth.starting'))
        self._auth_completed = False

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

        if HAS_WEBVIEW and webview:
            # Use embedded webview window
            threading.Thread(target=lambda: self._open_webview(auth_url), daemon=True).start()
        else:
            # Fallback to browser with Flask server
            self._start_flask_server()
            webbrowser.open(auth_url)

    def _open_webview(self, url: str):
        """
        Opens the Steam login page in an embedded webview window.

        The window monitors URL changes to detect when Steam redirects back
        to the callback URL after successful authentication.

        Args:
            url: The Steam OpenID login URL.
        """
        try:
            # Create window with URL change monitoring
            self.webview_window = webview.create_window(
                title=t('ui.login.webview_title'),
                url=url,
                width=500,
                height=700,
                resizable=True,
                on_top=True
            )

            # Start webview with URL change handler
            webview.start(self._on_webview_loaded, debug=False)

        except Exception as e:
            print(f"Webview error: {e}, falling back to browser")
            self._start_flask_server()
            webbrowser.open(url)

    def _on_webview_loaded(self):
        """
        Called when webview is ready. Sets up URL monitoring.
        """
        if not self.webview_window:
            return

        # Monitor URL changes by polling
        def check_url():
            import time
            while self.webview_window and not self._auth_completed:
                try:
                    current_url = self.webview_window.get_current_url()
                    if current_url and 'localhost' in current_url and '/auth' in current_url:
                        # Callback URL detected - extract Steam ID
                        self._handle_webview_callback(current_url)
                        break
                except Exception:
                    pass
                time.sleep(0.3)

        threading.Thread(target=check_url, daemon=True).start()

    def _handle_webview_callback(self, callback_url: str):
        """
        Handles the OpenID callback URL from the webview.

        Extracts the Steam ID from the callback URL and closes the webview.

        Args:
            callback_url: The callback URL with OpenID parameters.
        """
        if self._auth_completed:
            return

        self._auth_completed = True

        try:
            parsed = urlparse(callback_url)
            params = parse_qs(parsed.query)

            claimed_id = params.get('openid.claimed_id', [None])[0]

            if claimed_id and '/id/' in claimed_id:
                steam_id_64 = claimed_id.split('/id/')[-1]

                # Show success message in webview before closing
                if self.webview_window:
                    success_html = f"""
                    <html>
                    <body style="background-color:#1b2838; color:white; font-family:sans-serif;
                                 text-align:center; padding-top:100px;">
                        <h1 style="color:#66c0f4;">{t('ui.login.html_success_header')}</h1>
                        <p style="font-size:18px; margin-top:20px;">{t('ui.login.html_success_msg')}</p>
                        <p style="color:#888; margin-top:30px;">{t('ui.login.webview_closing')}</p>
                    </body>
                    </html>
                    """
                    try:
                        self.webview_window.load_html(success_html)
                    except Exception:
                        pass

                # Emit success signal
                self.auth_success.emit(steam_id_64)

                # Close webview after short delay
                def close_window():
                    import time
                    time.sleep(1.5)
                    if self.webview_window:
                        try:
                            self.webview_window.destroy()
                        except Exception:
                            pass
                    self.webview_window = None

                threading.Thread(target=close_window, daemon=True).start()

            else:
                self.auth_error.emit(t('ui.login.error_no_steam_id'))

        except Exception as e:
            self.auth_error.emit(str(e))

    def _start_flask_server(self):
        """Starts the Flask server for browser-based fallback authentication."""
        self.server_thread = threading.Thread(target=self._run_flask, daemon=True)
        self.server_thread.start()

    def _run_flask(self):
        """
        Runs the Flask server in a background thread.

        Used for fallback browser authentication when pywebview is not available.
        """
        try:
            self.server = make_server('localhost', self.port, self.app)
            self.server.serve_forever()
        except OSError as e:
            self.auth_error.emit(str(e))

    def _handle_auth(self):
        """
        Handles the OpenID callback from Steam (browser fallback).

        Returns:
            str: An HTML response to display in the browser.
        """
        claimed_id = request.args.get('openid.claimed_id')

        if claimed_id:
            steam_id_64 = claimed_id.split('/')[-1]
            self.auth_success.emit(steam_id_64)

            if self.server:
                threading.Thread(target=self.server.shutdown, daemon=True).start()

            return f"""
            <html>
            <body style="background-color:#1b2838; color:white; font-family:sans-serif; text-align:center; padding-top:50px;">
                <h1>{t('ui.login.html_success_header')}</h1>
                <p>{t('ui.login.html_success_msg')}</p>
                <script>window.setTimeout(function(){{ window.close(); }}, 2000);</script>
            </body>
            </html>
            """
        else:
            return t('ui.login.error_no_steam_id')
