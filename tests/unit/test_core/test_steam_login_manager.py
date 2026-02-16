# tests/unit/test_core/test_steam_login_manager.py

"""Unit tests for SteamLoginManager, QRCodeLoginThread, and UsernamePasswordLoginThread."""

from unittest.mock import MagicMock, patch


class TestQRCodeLoginThread:
    """Tests for QRCodeLoginThread."""

    @patch("src.core.steam_login_manager.requests.post")
    def test_start_qr_session_success(self, mock_post: MagicMock):
        """Successful QR session start should return challenge URL and IDs."""
        from src.core.steam_login_manager import QRCodeLoginThread

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "client_id": "abc123",
                "request_id": "req456",
                "challenge_url": "https://s.team/q/1/2",
                "interval": 5.0,
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        thread = QRCodeLoginThread("TestDevice")
        client_id, request_id, challenge_url, interval = thread._start_qr_session()

        assert client_id == "abc123"
        assert request_id == "req456"
        assert challenge_url == "https://s.team/q/1/2"
        assert interval == 5.0

    @patch("src.core.steam_login_manager.requests.post")
    def test_start_qr_session_network_error(self, mock_post: MagicMock):
        """Network error should return None tuple."""
        import requests as req

        from src.core.steam_login_manager import QRCodeLoginThread

        mock_post.side_effect = req.RequestException("offline")

        thread = QRCodeLoginThread()
        client_id, request_id, challenge_url, interval = thread._start_qr_session()

        assert client_id is None
        assert challenge_url is None

    @patch("src.core.steam_login_manager.time.sleep")
    @patch("src.core.steam_login_manager.requests.post")
    def test_poll_for_completion_success(self, mock_post: MagicMock, mock_sleep: MagicMock):
        """Successful poll should return token dict with steam_id."""
        from src.core.steam_login_manager import QRCodeLoginThread

        # First poll: no token yet. Second poll: success
        no_token = MagicMock()
        no_token.status_code = 200
        no_token.json.return_value = {"response": {}}
        no_token.raise_for_status = MagicMock()

        with_token = MagicMock()
        with_token.status_code = 200
        with_token.json.return_value = {
            "response": {
                "access_token": "at_123",
                "refresh_token": "rt_456",
                "account_name": "testuser",
            }
        }
        with_token.raise_for_status = MagicMock()

        mock_post.side_effect = [no_token, with_token]

        thread = QRCodeLoginThread()

        with patch("src.core.steam_login_manager.TokenStore.get_steamid_from_token", return_value="76561198000000000"):
            result = thread._poll_for_completion("client1", "req1", interval=0.01, timeout=5.0)

        assert result is not None
        assert result["access_token"] == "at_123"
        assert result["steam_id"] == "76561198000000000"

    @patch("src.core.steam_login_manager.time.sleep")
    @patch("src.core.steam_login_manager.requests.post")
    def test_poll_for_completion_timeout(self, mock_post: MagicMock, mock_sleep: MagicMock):
        """Polling past timeout should return None."""
        from src.core.steam_login_manager import QRCodeLoginThread

        no_token = MagicMock()
        no_token.status_code = 200
        no_token.json.return_value = {"response": {}}
        no_token.raise_for_status = MagicMock()
        mock_post.return_value = no_token

        thread = QRCodeLoginThread()
        # Very short timeout to trigger immediately
        result = thread._poll_for_completion("client1", "req1", interval=0.01, timeout=0.0)

        assert result is None

    @patch("src.core.steam_login_manager.time.sleep")
    @patch("src.core.steam_login_manager.requests.post")
    def test_poll_stop_requested(self, mock_post: MagicMock, mock_sleep: MagicMock):
        """Setting stop flag should abort polling."""
        from src.core.steam_login_manager import QRCodeLoginThread

        no_token = MagicMock()
        no_token.status_code = 200
        no_token.json.return_value = {"response": {}}
        no_token.raise_for_status = MagicMock()
        mock_post.return_value = no_token

        thread = QRCodeLoginThread()
        thread._stop_requested = True

        result = thread._poll_for_completion("client1", "req1", interval=0.01, timeout=300.0)

        assert result is None

    @patch("src.core.steam_login_manager.time.sleep")
    @patch("src.core.steam_login_manager.requests.post")
    def test_poll_no_steamid_returns_none(self, mock_post: MagicMock, mock_sleep: MagicMock):
        """Token received but no SteamID resolvable should return None."""
        from src.core.steam_login_manager import QRCodeLoginThread

        with_token = MagicMock()
        with_token.status_code = 200
        with_token.json.return_value = {
            "response": {
                "access_token": "at_123",
                "refresh_token": "rt_456",
            }
        }
        with_token.raise_for_status = MagicMock()
        mock_post.return_value = with_token

        thread = QRCodeLoginThread()

        with patch("src.core.steam_login_manager.TokenStore.get_steamid_from_token", return_value=None):
            result = thread._poll_for_completion("client1", "req1", interval=0.01, timeout=5.0)

        assert result is None


class TestUsernamePasswordLoginThread:
    """Tests for UsernamePasswordLoginThread."""

    @patch("src.core.steam_login_manager.requests.post")
    @patch("src.core.steam_login_manager.requests.get")
    def test_fetch_rsa_key_success(self, mock_get: MagicMock, mock_post: MagicMock):
        """Successful RSA key fetch returns (mod, exp, timestamp)."""
        from src.core.steam_login_manager import UsernamePasswordLoginThread

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "publickey_mod": "abc123",
                "publickey_exp": "010001",
                "timestamp": "1234567890",
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = UsernamePasswordLoginThread._fetch_rsa_key("testuser")

        assert result is not None
        mod, exp, ts = result
        assert mod == "abc123"
        assert exp == "010001"
        assert ts == "1234567890"

    @patch("src.core.steam_login_manager.requests.get")
    def test_fetch_rsa_key_network_error(self, mock_get: MagicMock):
        """Network error during RSA fetch should return None."""
        import requests as req

        from src.core.steam_login_manager import UsernamePasswordLoginThread

        mock_get.side_effect = req.RequestException("offline")

        result = UsernamePasswordLoginThread._fetch_rsa_key("testuser")

        assert result is None

    @patch("src.core.steam_login_manager.requests.get")
    def test_fetch_rsa_key_incomplete_response(self, mock_get: MagicMock):
        """Incomplete RSA response (missing fields) should return None."""
        from src.core.steam_login_manager import UsernamePasswordLoginThread

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": {"publickey_mod": "abc123"}}
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = UsernamePasswordLoginThread._fetch_rsa_key("testuser")

        assert result is None

    @patch("src.core.steam_login_manager.time.sleep")
    @patch("src.core.steam_login_manager.requests.post")
    def test_poll_credentials_approval_success(self, mock_post: MagicMock, mock_sleep: MagicMock):
        """Successful mobile approval should return token dict."""
        from src.core.steam_login_manager import UsernamePasswordLoginThread

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": {
                "access_token": "at_pwd_123",
                "refresh_token": "rt_pwd_456",
                "steamid": "76561198000000002",
            }
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        thread = UsernamePasswordLoginThread("user", "pass")
        result = thread._poll_for_credentials_approval("client1", "req1")

        assert result is not None
        assert result["access_token"] == "at_pwd_123"
        assert result["steam_id"] == "76561198000000002"

    @patch("src.core.steam_login_manager.time.sleep")
    @patch("src.core.steam_login_manager.requests.post")
    def test_poll_credentials_approval_timeout(self, mock_post: MagicMock, mock_sleep: MagicMock):
        """Setting stop flag should abort credential approval polling."""
        from src.core.steam_login_manager import UsernamePasswordLoginThread

        no_token = MagicMock()
        no_token.status_code = 200
        no_token.json.return_value = {"response": {}}
        no_token.raise_for_status = MagicMock()
        mock_post.return_value = no_token

        thread = UsernamePasswordLoginThread("user", "pass")
        # Set stop before calling so the loop exits immediately
        thread._stop_requested = True
        result = thread._poll_for_credentials_approval("client1", "req1")

        assert result is None


class TestSteamLoginManager:
    """Tests for the SteamLoginManager orchestrator."""

    def test_cancel_login_no_threads(self):
        """Cancelling when no threads are running should not crash."""
        from src.core.steam_login_manager import SteamLoginManager

        manager = SteamLoginManager()
        manager.cancel_login()  # Should not raise

    def test_on_qr_success_emits_login_success(self, qtbot):
        """QR success handler should emit login_success with correct dict."""
        from src.core.steam_login_manager import SteamLoginManager

        manager = SteamLoginManager()
        received = []
        manager.login_success.connect(lambda d: received.append(d))

        manager._on_qr_success(
            {
                "steam_id": "76561198000000000",
                "access_token": "at_qr",
                "refresh_token": "rt_qr",
                "account_name": "testuser",
            }
        )

        assert len(received) == 1
        assert received[0]["method"] == "qr"
        assert received[0]["steam_id"] == "76561198000000000"
        assert received[0]["access_token"] == "at_qr"

    def test_on_pwd_success_emits_login_success(self, qtbot):
        """Password success handler should forward the result dict."""
        from src.core.steam_login_manager import SteamLoginManager

        manager = SteamLoginManager()
        received = []
        manager.login_success.connect(lambda d: received.append(d))

        manager._on_pwd_success(
            {
                "method": "password",
                "steam_id": "76561198000000001",
                "access_token": "at_pwd",
                "refresh_token": "rt_pwd",
            }
        )

        assert len(received) == 1
        assert received[0]["method"] == "password"
        assert received[0]["steam_id"] == "76561198000000001"
