"""
Steam Login Dialog - OpenID Authentication

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


class SteamOpenIDHandler(BaseHTTPRequestHandler):
    """Handler für OpenID Callback"""

    steam_id = None

    def do_GET(self):
        """Handle GET request from Steam"""
        # Parse URL
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        # Check if we got the Steam ID
        if 'openid.claimed_id' in params:
            claimed_id = params['openid.claimed_id'][0]
            # Extract Steam ID from URL
            # Format: https://steamcommunity.com/openid/id/76561198004190954
            if '/id/' in claimed_id:
                steam_id = claimed_id.split('/id/')[-1]
                SteamOpenIDHandler.steam_id = steam_id

        # Send response
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        html = """
        <html>
        <head><title>Steam Login Success</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>✅ Login Successful!</h1>
            <p>You can close this window and return to Steam Library Manager.</p>
            <script>window.close();</script>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def log_message(self, format, *args):
        """Suppress log messages"""
        pass


class SteamLoginDialog(QDialog):
    """Steam Login Dialog mit OpenID"""

    login_successful = pyqtSignal(str)  # Emits Steam ID64

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Login to Steam")
        self.setMinimumWidth(400)
        self.setModal(True)

        self.steam_id = None
        self.server = None
        self.server_thread = None

        self._create_ui()

    def _create_ui(self):
        """Create UI"""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("🎮 Login with Steam")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Info
        info = QLabel(
            "Click the button below to login with your Steam account.\n\n"
            "A browser window will open where you can login with Steam.\n"
            "After login, return to this window."
        )
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        # Login Button
        login_btn = QPushButton("🌐 Login with Steam")
        login_btn.setMinimumHeight(50)
        login_btn.clicked.connect(self._start_login)
        layout.addWidget(login_btn)

        # Status
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _start_login(self):
        """Start Steam OpenID login"""
        self.status_label.setText("⏳ Starting local server...")

        try:
            # Start local HTTP server for callback
            self.server = HTTPServer(('localhost', 8080), SteamOpenIDHandler)
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()

            # Build OpenID URL
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

            # Open browser
            self.status_label.setText("🌐 Opening browser... Login with Steam")
            webbrowser.open(steam_login_url)

            # Start checking for response
            self.check_timer = QTimer()
            self.check_timer.timeout.connect(self._check_login)
            self.check_timer.start(500)  # Check every 500ms

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start login: {e}")
            self.status_label.setText("❌ Login failed")

    def _run_server(self):
        """Run HTTP server"""
        try:
            self.server.handle_request()  # Handle one request
        except Exception as e:
            print(f"Server error: {e}")

    def _check_login(self):
        """Check if login completed"""
        if SteamOpenIDHandler.steam_id:
            self.steam_id = SteamOpenIDHandler.steam_id
            self.check_timer.stop()

            self.status_label.setText(f"✅ Login successful! Steam ID: {self.steam_id}")

            # Emit signal
            self.login_successful.emit(self.steam_id)

            # Close dialog
            QTimer.singleShot(1000, self.accept)

    def get_steam_id(self) -> Optional[str]:
        """Get Steam ID (None if login failed)"""
        return self.steam_id

    def closeEvent(self, event):
        """Clean up on close"""
        if self.check_timer:
            self.check_timer.stop()
        if self.server:
            try:
                self.server.shutdown()
            except:
                pass
        super().closeEvent(event)