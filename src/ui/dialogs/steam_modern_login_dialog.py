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

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QFrame,
    QWidget,
    QProgressBar,
)

from src.core.steam_login_manager import SteamLoginManager
from src.ui.widgets.ui_helper import UIHelper
from src.utils.i18n import t

logger = logging.getLogger("steamlibmgr.login_dialog")


class ModernSteamLoginDialog(QDialog):
    """
    Modern Steam login dialog with QR code + Username/Password.

    Signals:
        login_success (dict): Emitted when login succeeds with session/tokens

    Attributes:
        steam_id_64: The SteamID64 as integer (for profile_setup_dialog)
        display_name: The Steam display name (for profile_setup_dialog)
    """

    login_success = pyqtSignal(dict)

    # Type hints for attributes
    steam_id_64: int | None
    display_name: str | None

    def __init__(self, parent=None):
        """Initialize the dialog."""
        super().__init__(parent)

        self.login_manager = SteamLoginManager()

        # Store login result for profile_setup_dialog
        self.steam_id_64: int | None = None
        self.display_name: str | None = None
        self.login_result: dict | None = None

        self._setup_ui()
        self._connect_signals()

        # Auto-start QR code generation
        self.start_qr_login()

    def _setup_ui(self):
        """Setup the complete UI."""
        self.setWindowTitle(f"{t('emoji.lock')} {t('steam.login.steam_login_title')}")
        self.setMinimumSize(800, 700)
        self.resize(800, 700)

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
        self.status_bar = QLabel(t("steam.login.status_ready"))
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

        self.cancel_btn = QPushButton(t("common.cancel"))
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

        title = QLabel(t("steam.login.sign_in_steam"))
        title.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel(t("steam.login.choose_method"))
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
        title = QLabel(t("steam.login.password_method"))
        title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # Simple login form (no multi-step, just username/password)
        login_layout = QVBoxLayout()
        login_layout.setSpacing(15)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(t("steam.login.username"))
        login_layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText(t("steam.login.password"))
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.returnPressed.connect(self.on_password_login)
        login_layout.addWidget(self.password_input)

        self.pwd_login_btn = QPushButton(t("steam.login.sign_in"))
        self.pwd_login_btn.setMinimumHeight(40)
        self.pwd_login_btn.clicked.connect(self.on_password_login)
        login_layout.addWidget(self.pwd_login_btn)

        # Info label for push notification
        info_label = QLabel(t("steam.login.password_info"))
        info_label.setStyleSheet("color: #8f98a0; font-size: 11px;")
        info_label.setWordWrap(True)
        login_layout.addWidget(info_label)

        login_layout.addStretch()

        layout.addLayout(login_layout)

        return panel

    def _create_qr_panel(self) -> QWidget:
        """Create right panel with QR code."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Title
        title = QLabel(t("steam.login.qr_method"))
        title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # Instructions
        instructions = QLabel(t("steam.login.qr_instructions"))
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
        self.qr_label.setText(t("steam.login.generating_qr"))
        layout.addWidget(self.qr_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Hint
        hint = QLabel(t("steam.login.qr_hint"))
        hint.setStyleSheet("color: #8f98a0; font-size: 12px;")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        layout.addStretch()

        return panel

    def _connect_signals(self):
        """Connect login manager signals."""
        self.login_manager.login_success.connect(self.on_login_success)
        self.login_manager.login_error.connect(self.on_login_error)
        self.login_manager.qr_ready.connect(self.on_qr_ready)
        self.login_manager.status_update.connect(self.on_status_update)
        # NEW: Mobile approval waiting signal (for password login)
        if hasattr(self.login_manager, "waiting_for_approval"):
            self.login_manager.waiting_for_approval.connect(self.on_waiting_for_approval)

    def start_qr_login(self):
        """Start QR code generation."""
        self.show_progress()
        self.login_manager.start_qr_login("SteamLibraryManager")

    def on_password_login(self):
        """Handle password login button click."""
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self.on_status_update(t("steam.login.enter_credentials"))
            return

        self.show_progress()
        self.pwd_login_btn.setEnabled(False)
        self.login_manager.start_password_login(username, password)

    def on_qr_ready(self, qr_url: str):
        """Handle QR code ready."""
        self.hide_progress()
        self.load_qr_image(qr_url)

    def on_login_success(self, result: dict):
        """Handle successful login."""
        self.hide_progress()

        # Get SteamID64 (may be string or int)
        steam_id_value = result.get("steam_id") or result.get("steamid")

        if steam_id_value:
            try:
                # Convert to int (works for both str and int input)
                self.steam_id_64 = int(steam_id_value)

                # Fetch proper display name from Steam Community API
                from src.core.steam_account_scanner import fetch_steam_display_name

                self.display_name = fetch_steam_display_name(self.steam_id_64)

            except (ValueError, TypeError) as e:
                # Conversion failed - set to None
                logger.error(t("logs.auth.steamid_conversion_error", value=steam_id_value, error=e))
                self.steam_id_64 = None
                self.display_name = None
        else:
            # No steam_id in result
            self.steam_id_64 = None
            self.display_name = None

        self.login_result = result
        self.on_status_update(t("steam.login.status_success"))
        self.login_success.emit(result)
        self.accept()

    def on_login_error(self, error: str):
        """Handle login error."""
        self.hide_progress()
        self.pwd_login_btn.setEnabled(True)
        UIHelper.show_error(self, error)

    def on_status_update(self, message: str):
        """Update status bar."""
        self.status_bar.setText(message)

    def on_waiting_for_approval(self, message: str):
        """Show waiting for mobile approval message."""
        self.hide_progress()
        self.on_status_update(message)
        # Show message in password section
        UIHelper.show_info(self, message, title=t("steam.login.waiting_approval_title"))

    def load_qr_image(self, challenge_url: str):
        """Generate and display QR code from Steam challenge URL with optional logo."""
        try:
            import qrcode
            from io import BytesIO
            from PIL import Image, ImageDraw, ImageFont

            # Generate QR code with HIGHER error correction (allows logo overlay)
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,  # HIGH = 30% can be damaged
                box_size=15,  # Bigger box = higher resolution (was 10)
                border=4,  # Smaller border for better use of space
            )
            qr.add_data(challenge_url)
            qr.make(fit=True)

            # Create high-quality image
            img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

            # OPTIONAL: Add "SLM" logo in center (if space allows)
            try:
                # Calculate center position for logo
                img_width, img_height = img.size
                logo_size = img_width // 6  # Logo is 20% of QR code size
                logo_pos = ((img_width - logo_size) // 2, (img_height - logo_size) // 2)

                # Create logo: white rounded square with "SLM" text
                logo = Image.new("RGB", (logo_size, logo_size), "white")
                draw = ImageDraw.Draw(logo)

                # Draw black border
                draw.rectangle([0, 0, logo_size - 1, logo_size - 1], outline="black", width=3)

                # Try to use a font, fallback to default if not available
                try:
                    font_size = int(logo_size * 0.45)
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
                except (OSError, IOError):
                    font = ImageFont.load_default()

                # Draw "SLM" text centered
                text = "SLM"
                # Get text bounding box (for PIL >= 8.0.0)
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                # Center text with slight vertical adjustment for better balance
                text_x = (logo_size - text_width) // 2
                text_y = (logo_size - text_height) // 2 - 2  # Slight upward shift
                draw.text((text_x, text_y), text, fill="black", font=font)

                # Paste logo onto QR code
                img.paste(logo, logo_pos)
            except Exception as logo_error:
                # If logo fails, continue without it (QR code still works)
                logger.error(t("logs.auth.qr_logo_error", error=logo_error))

            # Convert to QPixmap
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)

            pixmap = QPixmap()
            pixmap.loadFromData(buffer.read())

            # Scale to display size (smooth scaling for better quality)
            self.qr_label.setPixmap(
                pixmap.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )

        except ImportError:
            self.qr_label.setText("QR Code generation requires 'qrcode' package\n\n" "Install: pip install qrcode[pil]")
        except Exception as e:
            self.qr_label.setText(f"Failed to generate QR code: {e}")

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
