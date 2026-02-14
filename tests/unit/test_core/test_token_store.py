# tests/unit/test_core/test_token_store.py

"""Unit tests for TokenStore."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


class TestStoredTokens:
    """Tests for the StoredTokens frozen dataclass."""

    def test_stored_tokens_creation(self):
        """StoredTokens should be creatable with all required fields."""
        from src.core.token_store import StoredTokens

        tokens = StoredTokens(
            access_token="access_123",
            refresh_token="refresh_456",
            steam_id="76561198000000000",
            timestamp=1700000000.0,
        )

        assert tokens.access_token == "access_123"
        assert tokens.refresh_token == "refresh_456"
        assert tokens.steam_id == "76561198000000000"
        assert tokens.timestamp == 1700000000.0

    def test_stored_tokens_is_frozen(self):
        """StoredTokens should be immutable."""
        from src.core.token_store import StoredTokens

        tokens = StoredTokens(
            access_token="a",
            refresh_token="r",
            steam_id="123",
            timestamp=0.0,
        )

        with pytest.raises(AttributeError):
            tokens.access_token = "modified"  # type: ignore[misc]


class TestTokenStoreFileBased:
    """Tests for TokenStore file-based encryption backend."""

    def test_save_and_load_roundtrip(self, tmp_path: Path):
        """Tokens saved to file should be loadable and identical."""
        from src.core.token_store import TokenStore

        store = TokenStore(data_dir=tmp_path)
        # Force file-based backend
        store._keyring_available = False

        store.save_tokens("access_abc", "refresh_xyz", "76561198000000000")

        loaded = store.load_tokens()
        assert loaded is not None
        assert loaded.access_token == "access_abc"
        assert loaded.refresh_token == "refresh_xyz"
        assert loaded.steam_id == "76561198000000000"
        assert loaded.timestamp > 0

    def test_load_tokens_returns_none_when_no_file(self, tmp_path: Path):
        """Loading when no token file exists should return None."""
        from src.core.token_store import TokenStore

        store = TokenStore(data_dir=tmp_path)
        store._keyring_available = False

        result = store.load_tokens()
        assert result is None

    def test_clear_tokens_removes_file(self, tmp_path: Path):
        """Clearing tokens should delete the encrypted file."""
        from src.core.token_store import TokenStore

        store = TokenStore(data_dir=tmp_path)
        store._keyring_available = False

        store.save_tokens("a", "r", "123")
        assert store.token_file.exists()

        store.clear_tokens()
        assert not store.token_file.exists()

    def test_clear_tokens_no_file_no_error(self, tmp_path: Path):
        """Clearing when no file exists should not raise."""
        from src.core.token_store import TokenStore

        store = TokenStore(data_dir=tmp_path)
        store._keyring_available = False

        store.clear_tokens()  # Should not raise

    def test_encrypted_file_is_not_plaintext(self, tmp_path: Path):
        """The token file should not contain plaintext tokens."""
        from src.core.token_store import TokenStore

        store = TokenStore(data_dir=tmp_path)
        store._keyring_available = False

        store.save_tokens("secret_access_token", "secret_refresh_token", "123")

        content = store.token_file.read_text()
        assert "secret_access_token" not in content
        assert "secret_refresh_token" not in content

    def test_tampered_file_fails_to_load(self, tmp_path: Path):
        """A modified encrypted file should fail authentication."""
        from src.core.token_store import TokenStore

        store = TokenStore(data_dir=tmp_path)
        store._keyring_available = False

        store.save_tokens("a", "r", "123")

        # Tamper with the ciphertext
        with open(store.token_file, "r") as f:
            envelope = json.load(f)
        envelope["ciphertext"] = "AAAA" + envelope["ciphertext"][4:]
        with open(store.token_file, "w") as f:
            json.dump(envelope, f)

        result = store.load_tokens()
        assert result is None  # Should fail gracefully


class TestTokenStoreRefresh:
    """Tests for TokenStore.refresh_access_token()."""

    @patch("src.core.token_store.requests.post")
    def test_refresh_success_json_response(self, mock_post: MagicMock):
        """Successful refresh with JSON response should return new access token."""
        from src.core.token_store import TokenStore

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = '{"response":{"access_token":"new_token"}}'
        mock_response.json.return_value = {"response": {"access_token": "new_token"}}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = TokenStore.refresh_access_token("old_refresh", "76561198000000000")

        assert result == "new_token"
        mock_post.assert_called_once()
        # Verify input_protobuf_encoded is used
        call_kwargs = mock_post.call_args
        assert "input_protobuf_encoded" in call_kwargs.kwargs.get("data", call_kwargs[1].get("data", {}))

    @patch("src.core.token_store.requests.post")
    def test_refresh_success_protobuf_response(self, mock_post: MagicMock):
        """Successful refresh with protobuf response should decode access token."""
        from src.core.token_store import TokenStore

        # Build a minimal protobuf response: field 1 (string) = "fresh_token"
        token_bytes = b"fresh_token"
        proto_response = bytes([0x0A, len(token_bytes)]) + token_bytes

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/x-protobuf"}
        mock_response.text = ""
        mock_response.content = proto_response
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = TokenStore.refresh_access_token("old_refresh", "76561198000000000")

        assert result == "fresh_token"

    @patch("src.core.token_store.requests.post")
    def test_refresh_no_new_token_returns_sentinel(self, mock_post: MagicMock):
        """When Steam returns 200 but no new token, return sentinel (not None)."""
        from src.core.token_store import TokenStore, _REFRESH_NOT_NEEDED

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.text = '{"response":{}}'
        mock_response.json.return_value = {"response": {}}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = TokenStore.refresh_access_token("refresh_tok", "76561198000000000")

        assert result == _REFRESH_NOT_NEEDED

    @patch("src.core.token_store.requests.post")
    def test_refresh_failure_returns_none(self, mock_post: MagicMock):
        """Failed refresh (network error) should return None."""
        import requests as req

        from src.core.token_store import TokenStore

        mock_post.side_effect = req.RequestException("Network error")

        result = TokenStore.refresh_access_token("bad_refresh", "76561198000000000")

        assert result is None

    def test_refresh_without_steam_id_returns_none(self):
        """Refresh without steam_id should return None immediately."""
        from src.core.token_store import TokenStore

        result = TokenStore.refresh_access_token("some_refresh", "")

        assert result is None

    @patch("src.core.token_store.time.sleep")
    @patch("src.core.token_store.requests.post")
    def test_refresh_retries_on_network_error(self, mock_post: MagicMock, mock_sleep: MagicMock):
        """Refresh should retry on transient network errors."""
        import requests as req

        from src.core.token_store import TokenStore

        # First two calls fail, third succeeds
        mock_success = MagicMock()
        mock_success.status_code = 200
        mock_success.headers = {"Content-Type": "application/json"}
        mock_success.text = '{"response":{"access_token":"recovered_token"}}'
        mock_success.json.return_value = {"response": {"access_token": "recovered_token"}}
        mock_success.raise_for_status = MagicMock()

        mock_post.side_effect = [
            req.RequestException("timeout"),
            req.RequestException("connection reset"),
            mock_success,
        ]

        result = TokenStore.refresh_access_token("refresh_tok", "76561198000000000", max_retries=3)

        assert result == "recovered_token"
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2  # 2 retries with sleep

    @patch("src.core.token_store.time.sleep")
    @patch("src.core.token_store.requests.post")
    def test_refresh_exhausts_retries(self, mock_post: MagicMock, mock_sleep: MagicMock):
        """Refresh should return None after exhausting all retries."""
        import requests as req

        from src.core.token_store import TokenStore

        mock_post.side_effect = req.RequestException("persistent failure")

        result = TokenStore.refresh_access_token("refresh_tok", "76561198000000000", max_retries=2)

        assert result is None
        assert mock_post.call_count == 2
        assert mock_sleep.call_count == 1  # Only between attempts

    @patch("src.core.token_store.requests.get")
    def test_validate_access_token_valid(self, mock_get: MagicMock):
        """Valid token should return True."""
        from src.core.token_store import TokenStore

        mock_get.return_value = MagicMock(status_code=200)

        assert TokenStore.validate_access_token("valid_token") is True

    @patch("src.core.token_store.requests.get")
    def test_validate_access_token_expired(self, mock_get: MagicMock):
        """Expired token should return False (HTTP 401)."""
        from src.core.token_store import TokenStore

        mock_get.return_value = MagicMock(status_code=401)

        assert TokenStore.validate_access_token("expired_token") is False

    @patch("src.core.token_store.requests.get")
    def test_validate_access_token_network_error(self, mock_get: MagicMock):
        """Network error during validation should return False."""
        import requests as req

        from src.core.token_store import TokenStore

        mock_get.side_effect = req.RequestException("offline")

        assert TokenStore.validate_access_token("any_token") is False


class TestProtobufHelpers:
    """Tests for manual protobuf encoding/decoding helpers."""

    def test_encode_refresh_proto_with_steamid(self):
        """Encoding should produce valid protobuf with refresh_token and steamid."""
        from src.core.token_store import TokenStore

        result = TokenStore._encode_refresh_proto("mytoken", "76561198000000000")

        # Field 1: tag 0x0A, varint 7, "mytoken"
        assert result[0] == 0x0A
        assert b"mytoken" in result
        # Field 2: tag 0x11, followed by 8 bytes LE
        assert 0x11 in result

    def test_encode_refresh_proto_without_steamid(self):
        """Encoding without steamid should only include refresh_token field."""
        from src.core.token_store import TokenStore

        result = TokenStore._encode_refresh_proto("mytoken", "")

        assert result[0] == 0x0A
        assert b"mytoken" in result
        assert 0x11 not in result

    def test_decode_string_field_roundtrip(self):
        """Decoding should extract the string encoded by our encoder."""
        from src.core.token_store import TokenStore

        # Encode a simple protobuf with field 1 = "hello"
        buf = bytearray()
        buf.append(0x0A)  # field 1, wire type 2
        buf.append(5)  # length
        buf.extend(b"hello")

        result = TokenStore._decode_string_field(bytes(buf), field_number=1)
        assert result == "hello"

    def test_decode_string_field_not_found(self):
        """Decoding a non-existent field should return None."""
        from src.core.token_store import TokenStore

        buf = bytearray()
        buf.append(0x0A)  # field 1, wire type 2
        buf.append(3)
        buf.extend(b"abc")

        result = TokenStore._decode_string_field(bytes(buf), field_number=99)
        assert result is None


class TestTokenStoreGetSteamId:
    """Tests for TokenStore.get_steamid_from_token()."""

    @patch("src.core.token_store.requests.get")
    def test_steamid_from_api(self, mock_get: MagicMock):
        """Should extract SteamID from GetOwnedGames API response."""
        from src.core.token_store import TokenStore

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": {"steamid": "76561198000000000"}}
        mock_get.return_value = mock_response

        result = TokenStore.get_steamid_from_token("valid_token")

        assert result == "76561198000000000"

    @patch("src.core.token_store.requests.get")
    def test_steamid_from_jwt_fallback(self, mock_get: MagicMock):
        """Should fall back to JWT decode when API fails."""
        import base64

        from src.core.token_store import TokenStore

        # Mock API failure
        mock_get.side_effect = Exception("API down")

        # Create a fake JWT with sub claim
        header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
        payload = base64.urlsafe_b64encode(b'{"sub":"76561198000000001"}').decode().rstrip("=")
        fake_jwt = f"{header}.{payload}.signature"

        result = TokenStore.get_steamid_from_token(fake_jwt)

        assert result == "76561198000000001"

    @patch("src.core.token_store.requests.get")
    def test_invalid_token_returns_none(self, mock_get: MagicMock):
        """Completely invalid token should return None."""
        from src.core.token_store import TokenStore

        mock_get.side_effect = Exception("API error")

        result = TokenStore.get_steamid_from_token("not-a-token")

        assert result is None
