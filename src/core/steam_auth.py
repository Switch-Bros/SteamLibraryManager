# src/core/steam_auth.py

"""
Manages Steam authentication via OpenID.

This module provides Steam OpenID authentication using an embedded QWebEngineView
dialog. The login happens entirely within the application.
"""
from urllib.parse import urlencode, urlparse, parse_qs

from PyQt6.QtCore import QObject, pyqtSignal, QUrl
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QHBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView

from src.utils.i18n import t


class SteamLoginDialog(QDialog):
    """Embedded Steam login dialog using QWebEngineView."""

    login_success = pyqtSignal(str)  # Emits SteamID64

    def __init__(self, auth_url: str, redirect_uri: str, parent=None):
        super().__init__(parent)
        self.redirect_uri = redirect_uri
        self.steam_id = None

        self.setWindowTitle(t('ui.login.webview_title'))
        self.setMinimumSize(500, 700)
        self.resize(500, 700)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # WebEngine View
        self.web_view = QWebEngineView()
        self.web_view.urlChanged.connect(self._on_url_changed)
        self.web_view.load(QUrl(auth_url))
        layout.addWidget(self.web_view)

        # Cancel button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        cancel_btn = QPushButton(t('ui.dialogs.cancel'))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        btn_layout.setContentsMargins(10, 5, 10, 10)
        layout.addLayout(btn_layout)

    def _on_url_changed(self, url: QUrl):
        """Monitors URL changes to detect the callback."""
        url_str = url.toString()

        if 'localhost' in url_str and '/auth' in url_str:
            # Callback URL detected - extract Steam ID
            parsed = urlparse(url_str)
            params = parse_qs(parsed.query)

            claimed_id = params.get('openid.claimed_id', [None])[0]

            if claimed_id and '/id/' in claimed_id:
                self.steam_id = claimed_id.split('/id/')[-1]
                self.login_success.emit(self.steam_id)
                self.accept()


class SteamAuthManager(QObject):
    """
    Manages Steam authentication via OpenID with embedded login dialog.

    Signals:
        auth_success (str): Emitted when authentication succeeds, passes the SteamID64.
        auth_error (str): Emitted when an error occurs during authentication.
    """

    auth_success = pyqtSignal(str)  # Returns SteamID64
    auth_error = pyqtSignal(str)

    def __init__(self):
        """Initializes the SteamAuthManager."""
        super().__init__()
        self.login_dialog = None
        self.port = 5000

        # noinspection HttpUrlsUsage
        self.redirect_uri = f"http://localhost:{self.port}/auth"

    def start_login(self, parent=None):
        """Starts the Steam OpenID authentication process with embedded dialog."""
        print(t('logs.auth.starting'))

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

        # Create and show login dialog
        self.login_dialog = SteamLoginDialog(auth_url, self.redirect_uri, parent)
        self.login_dialog.login_success.connect(self._on_login_success)
        self.login_dialog.rejected.connect(self._on_login_canceled)
        self.login_dialog.show()

    def _on_login_success(self, steam_id: str):
        """Handles successful login from the dialog."""
        self.auth_success.emit(steam_id)

    def _on_login_canceled(self):
        """Handles login cancellation."""
        pass  # User canceled, no action needed
