# src/ui/steam_modern_login_dialog.py

"""
Modern Steam Login Dialog with QR Code + Username/Password.

Features:
- Split view: Left = Username/Password, Right = QR Code
- Automatic QR code loading
- 2FA support (Steam Mobile App confirmation)
- CAPTCHA support
- Email verification support
- Beautiful modern design
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QFrame, QStackedWidget, QWidget, QMessageBox,
    QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from src.core.steam_login_manager import SteamLoginManager
from src.utils.i18n import t


class ModernSteamLoginDialog(QDialog):
    """
    Modern Steam login dialog with QR code + Username/Password.

    Signals:
        login_success (dict): Emitted when login succeeds with session/tokens
    """

    login_success = pyqtSignal(dict)

    def __init__(self, parent=None):
        """Initialize the dialog."""
        super().__init__(parent)

        self.login_manager = SteamLoginManager()
        self.network_manager = QNetworkAccessManager(self)

        self._setup_ui()
        self._connect_signals()

        # Auto-start QR code generation
        self.start_qr_login()

    def _setup_ui(self):
        """Setup the complete UI."""
        self.setWindowTitle(t('ui.login.steam_login_title'))
        self.setMinimumSize(800, 600)
        self.resize(800, 600)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = self._create_header()
        main_layout.addWidget(header)

        # Content (Split view)
        content = self._create_content()
        main_layout.addWidget(content, stretch=1)

        # Status bar
        self.status_bar = QLabel(t('ui.login.status_ready'))
        self.status_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_bar.setStyleSheet("""
            QLabel {
                background: #1b2838;
                color: #c7d5e0;
                padding: 10px;
                border-top: 1px solid #16202d;
            }
        """)
        main_layout.addWidget(self.status_bar)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximumHeight(3)
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(20, 10, 20, 20)
        button_layout.addStretch()

        self.cancel_btn = QPushButton(t('common.cancel'))
        self.cancel_btn.setMinimumWidth(120)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        main_layout.addLayout(button_layout)

        # Apply dark Steam-like theme
        self.setStyleSheet("""
            QDialog {
                background: #1b2838;
            }
            QPushButton {
                background: #5c7e10;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #699d11;
            }
            QPushButton:pressed {
                background: #4a6609;
            }
            QPushButton:disabled {
                background: #3d3d3d;
                color: #777;
            }
            QLineEdit {
                background: #32444e;
                color: white;
                border: 1px solid #16202d;
                padding: 10px;
                border-radius: 3px;
            }
            QLineEdit:focus {
                border: 1px solid #5c7e10;
            }
        """)

    def _create_header(self) -> QWidget:  # noqa: Method can't be static (uses t())
        """Create header with logo and title."""
        header = QFrame()
        header.setFrameShape(QFrame.Shape.StyledPanel)
        header.setStyleSheet("""
            QFrame {
                background: #171a21;
                border-bottom: 2px solid #5c7e10;
            }
        """)

        layout = QVBoxLayout(header)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel(t('ui.login.sign_in_steam'))
        title.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel(t('ui.login.choose_method'))
        subtitle.setStyleSheet("color: #c7d5e0; font-size: 14px;")
        layout.addWidget(subtitle, alignment=Qt.AlignmentFlag.AlignCenter)

        return header

    def _create_content(self) -> QWidget:
        """Create split view content (QR + Username/Password)."""
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # LEFT SIDE: Username/Password
        left_side = self._create_password_panel()
        container_layout.addWidget(left_side, stretch=1)

        # DIVIDER
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setStyleSheet("background: #16202d;")
        divider.setFixedWidth(2)
        container_layout.addWidget(divider)

        # RIGHT SIDE: QR Code
        right_side = self._create_qr_panel()
        container_layout.addWidget(right_side, stretch=1)

        return container

    def _create_password_panel(self) -> QWidget:
        """Create left panel with username/password fields."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Title
        title = QLabel(t('ui.login.password_method'))
        title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # Stack for different states (login, 2FA, email, captcha)
        self.pwd_stack = QStackedWidget()

        # LOGIN PAGE
        login_page = QWidget()
        login_layout = QVBoxLayout(login_page)
        login_layout.setSpacing(15)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(t('ui.login.username'))
        login_layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText(t('ui.login.password'))
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self.on_password_login)
        login_layout.addWidget(self.password_input)

        self.pwd_login_btn = QPushButton(t('ui.login.sign_in'))
        self.pwd_login_btn.setMinimumHeight(40)
        self.pwd_login_btn.clicked.connect(self.on_password_login)
        login_layout.addWidget(self.pwd_login_btn)

        login_layout.addStretch()

        self.pwd_stack.addWidget(login_page)

        # 2FA PAGE
        twofa_page = QWidget()
        twofa_layout = QVBoxLayout(twofa_page)
        twofa_layout.setSpacing(15)

        twofa_label = QLabel(t('ui.login.enter_2fa_code'))
        twofa_label.setStyleSheet("color: #c7d5e0;")
        twofa_label.setWordWrap(True)
        twofa_layout.addWidget(twofa_label)

        self.twofa_input = QLineEdit()
        self.twofa_input.setPlaceholderText(t('ui.login.2fa_code'))
        self.twofa_input.returnPressed.connect(self.on_submit_2fa)
        twofa_layout.addWidget(self.twofa_input)

        submit_2fa_btn = QPushButton(t('ui.login.submit'))
        submit_2fa_btn.clicked.connect(self.on_submit_2fa)
        twofa_layout.addWidget(submit_2fa_btn)

        twofa_layout.addStretch()

        self.pwd_stack.addWidget(twofa_page)

        # EMAIL CODE PAGE
        email_page = QWidget()
        email_layout = QVBoxLayout(email_page)
        email_layout.setSpacing(15)

        email_label = QLabel(t('ui.login.enter_email_code'))
        email_label.setStyleSheet("color: #c7d5e0;")
        email_label.setWordWrap(True)
        email_layout.addWidget(email_label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText(t('ui.login.email_code'))
        self.email_input.returnPressed.connect(self.on_submit_email)
        email_layout.addWidget(self.email_input)

        submit_email_btn = QPushButton(t('ui.login.submit'))
        submit_email_btn.clicked.connect(self.on_submit_email)
        email_layout.addWidget(submit_email_btn)

        email_layout.addStretch()

        self.pwd_stack.addWidget(email_page)

        # CAPTCHA PAGE
        captcha_page = QWidget()
        captcha_layout = QVBoxLayout(captcha_page)
        captcha_layout.setSpacing(15)

        captcha_label = QLabel(t('ui.login.solve_captcha'))
        captcha_label.setStyleSheet("color: #c7d5e0;")
        captcha_layout.addWidget(captcha_label)

        self.captcha_image = QLabel()
        self.captcha_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.captcha_image.setStyleSheet("background: #32444e; border: 1px solid #16202d;")
        self.captcha_image.setMinimumHeight(150)
        captcha_layout.addWidget(self.captcha_image)

        self.captcha_input = QLineEdit()
        self.captcha_input.setPlaceholderText(t('ui.login.captcha_text'))
        self.captcha_input.returnPressed.connect(self.on_submit_captcha)
        captcha_layout.addWidget(self.captcha_input)

        submit_captcha_btn = QPushButton(t('ui.login.submit'))
        submit_captcha_btn.clicked.connect(self.on_submit_captcha)
        captcha_layout.addWidget(submit_captcha_btn)

        captcha_layout.addStretch()

        self.pwd_stack.addWidget(captcha_page)

        layout.addWidget(self.pwd_stack)

        return panel

    def _create_qr_panel(self) -> QWidget:
        """Create right panel with QR code."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Title
        title = QLabel(t('ui.login.qr_method'))
        title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # Instructions
        instructions = QLabel(t('ui.login.qr_instructions'))
        instructions.setStyleSheet("color: #c7d5e0;")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # QR Code
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setStyleSheet("""
            QLabel {
                background: white;
                border: 2px solid #5c7e10;
                border-radius: 5px;
                padding: 20px;
            }
        """)
        self.qr_label.setMinimumSize(300, 300)
        self.qr_label.setText(t('ui.login.generating_qr'))
        layout.addWidget(self.qr_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Hint
        hint = QLabel(t('ui.login.qr_hint'))
        hint.setStyleSheet("color: #8f98a0; font-size: 12px;")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        layout.addStretch()

        return panel

    def _connect_signals(self):
        """Connect login manager signals."""
        # noinspection PyUnresolvedReferences
        self.login_manager.login_success.connect(self.on_login_success)
        # noinspection PyUnresolvedReferences
        self.login_manager.login_error.connect(self.on_login_error)
        # noinspection PyUnresolvedReferences
        self.login_manager.qr_ready.connect(self.on_qr_ready)
        # noinspection PyUnresolvedReferences
        self.login_manager.status_update.connect(self.on_status_update)
        # noinspection PyUnresolvedReferences
        self.login_manager.captcha_required.connect(self.on_captcha_required)
        # noinspection PyUnresolvedReferences
        self.login_manager.email_code_required.connect(self.on_email_required)
        # noinspection PyUnresolvedReferences
        self.login_manager.twofactor_required.connect(self.on_2fa_required)

    def start_qr_login(self):
        """Start QR code generation."""
        self.show_progress()
        self.login_manager.start_qr_login("SteamLibraryManager")

    def on_password_login(self):
        """Handle password login button click."""
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self.on_status_update(t('ui.login.enter_credentials'))
            return

        self.show_progress()
        self.pwd_login_btn.setEnabled(False)
        self.login_manager.start_password_login(username, password)

    def on_submit_2fa(self):
        """Submit 2FA code."""
        code = self.twofa_input.text().strip()
        if code:
            self.show_progress()
            self.login_manager.submit_twofactor_code(code)

    def on_submit_email(self):
        """Submit email verification code."""
        code = self.email_input.text().strip()
        if code:
            self.show_progress()
            self.login_manager.submit_email_code(code)

    def on_submit_captcha(self):
        """Submit CAPTCHA solution."""
        text = self.captcha_input.text().strip()
        if text:
            self.show_progress()
            self.login_manager.submit_captcha(text)

    def on_qr_ready(self, qr_url: str):
        """Handle QR code ready."""
        self.hide_progress()
        self.load_qr_image(qr_url)

    def on_login_success(self, result: dict):
        """Handle successful login."""
        self.hide_progress()
        self.on_status_update(t('ui.login.success'))
        self.login_success.emit(result)
        self.accept()

    def on_login_error(self, error: str):
        """Handle login error."""
        self.hide_progress()
        self.pwd_login_btn.setEnabled(True)
        QMessageBox.critical(self, t('common.error'), error)

    def on_status_update(self, message: str):
        """Update status bar."""
        self.status_bar.setText(message)

    def on_captcha_required(self, captcha_url: str):
        """Show CAPTCHA page."""
        self.hide_progress()
        self.pwd_stack.setCurrentIndex(3)  # Captcha page
        self.load_captcha_image(captcha_url)

    def on_email_required(self):
        """Show email code page."""
        self.hide_progress()
        self.pwd_stack.setCurrentIndex(2)  # Email page

    def on_2fa_required(self):
        """Show 2FA page."""
        self.hide_progress()
        self.pwd_stack.setCurrentIndex(1)  # 2FA page

    def load_qr_image(self, url: str):
        """Load QR code image from URL."""
        request = QNetworkRequest(QUrl(url))
        reply = self.network_manager.get(request)
        # noinspection PyUnresolvedReferences
        reply.finished.connect(lambda: self._on_qr_loaded(reply))

    def _on_qr_loaded(self, reply: QNetworkReply):
        """Handle QR image loaded."""
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            self.qr_label.setPixmap(pixmap.scaled(
                300, 300,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            self.qr_label.setText(t('ui.login.qr_load_failed'))
        reply.deleteLater()

    def load_captcha_image(self, url: str):
        """Load CAPTCHA image from URL."""
        request = QNetworkRequest(QUrl(url))
        reply = self.network_manager.get(request)
        # noinspection PyUnresolvedReferences
        reply.finished.connect(lambda: self._on_captcha_loaded(reply))

    def _on_captcha_loaded(self, reply: QNetworkReply):
        """Handle CAPTCHA image loaded."""
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            self.captcha_image.setPixmap(pixmap.scaled(
                400, 150,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        reply.deleteLater()

    def show_progress(self):
        """Show progress bar."""
        self.progress_bar.show()

    def hide_progress(self):
        """Hide progress bar."""
        self.progress_bar.hide()

    def reject(self):
        """Handle dialog cancel."""
        self.login_manager.cancel_login()
        super().reject()