"""
Steam Login Dialog - Clean & i18n-ready
Speichern als: src/ui/steam_login_dialog.py
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QMessageBox
)
from PyQt6.QtCore import Qt, QUrl, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QDesktopServices
from typing import Optional
import requests
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import urllib.parse
from src.utils.i18n import t


class SteamOpenIDHandler(BaseHTTPRequestHandler):
    """Handler für OpenID Callback"""

    steam_id = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if 'openid.claimed_id' in params:
            claimed_id = params['openid.claimed_id'][0]
            if '/id/' in claimed_id:
                steam_id = claimed_id.split('/id/')[-1]
                SteamOpenIDHandler.steam_id = steam_id

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        # HTML jetzt auch übersetzbar
        html = f"""
        <html>
        <head><title>{t('ui.login.html_success_title')}</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>{t('ui.login.html_success_header')}</h1>
            <p>{t('ui.login.html_success_body')}</p>
            <script>window.close();</script>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        pass


class SteamLoginDialog(QDialog):
    """Steam Login Dialog mit OpenID"""

    login_successful = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(t('ui.login.window_title_emoji'))
        self.setMinimumWidth(400)
        self.setModal(True)

        self.steam_id = None
        self.server = None
        self.server_thread = None

        self._create_ui()

    def _create_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel(t('ui.login.window_title_emoji'))
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        info = QLabel(t('ui.login.info'))
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        login_btn = QPushButton(t('ui.login.button'))
        login_btn.setMinimumHeight(50)
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
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _start_login(self):
        self.status_label.setText(t('ui.login.status_waiting'))

        try:
            self.server = HTTPServer(('localhost', 8080), SteamOpenIDHandler)
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()

            return_url = "http://localhost:8080/auth/steam/callback"
            realm = "http://localhost:8080"

            openid_params = {
                'openid.ns': 'http://specs.openid.net/auth/2.0',
                'openid.mode': 'checkid_setup',
                'openid.return_to': return_url,
                'openid.realm': realm,
                'openid.identity': 'http://specs.openid.net/auth/2.0/identifier_select',
                'openid.claimed_id': 'http://specs.openid.net/auth/2.0/identifier_select'
            }

            steam_login_url = 'https://steamcommunity.com/openid/login?' + urllib.parse.urlencode(openid_params)

            self.status_label.setText(t('ui.login.status_browser'))
            webbrowser.open(steam_login_url)

            self.check_timer = QTimer()
            self.check_timer.timeout.connect(self._check_login)
            self.check_timer.start(500)

        except Exception as e:
            QMessageBox.critical(self, t('ui.login.error_title'), t('ui.login.error_msg', error=e))
            self.status_label.setText(t('ui.login.status_failed'))

    def _run_server(self):
        try:
            self.server.handle_request()
        except Exception as e:
            print(f"Server error: {e}")

    def _check_login(self):
        if SteamOpenIDHandler.steam_id:
            self.steam_id = SteamOpenIDHandler.steam_id
            self.check_timer.stop()

            self.status_label.setText(t('ui.login.status_success', id=self.steam_id))
            self.login_successful.emit(self.steam_id)
            QTimer.singleShot(1000, self.accept)

    def get_steam_id(self) -> Optional[str]:
        return self.steam_id

    def closeEvent(self, event):
        if self.check_timer:
            self.check_timer.stop()
        if self.server:
            try:
                self.server.shutdown()
            except:
                pass
        super().closeEvent(event)