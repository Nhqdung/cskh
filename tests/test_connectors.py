"""
Unit tests for Discord, Meta, and Webhook connectors.
Verifies permission handling, token error reporting, and webhook signatures.
"""

import hmac
import hashlib
from unittest.mock import patch, MagicMock
from connectors.discord_connector import DiscordConnector
from connectors.meta_connector import MetaConnector
from connectors.webhook_server import verify_meta_signature


def test_discord_unconfigured_error():
    conn = DiscordConnector(bot_token="", employee_user_id="")
    res = conn.test_connection()
    assert res["success"] is False
    assert "Thiếu Discord Bot Token" in res["error"]


def test_meta_unconfigured_error():
    conn = MetaConnector(page_id="", page_access_token="")
    res = conn.test_connection()
    assert res["success"] is False
    assert "Chưa cấu hình Meta Page ID" in res["error"]


def test_meta_api_error_handling():
    conn = MetaConnector(page_id="12345", page_access_token="expired_token")
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {
        "error": {
            "message": "Session has expired or token is invalid",
            "type": "OAuthException",
            "code": 190,
        }
    }

    with patch("httpx.Client.get", return_value=mock_resp):
        res = conn.test_connection()
        assert res["success"] is False
        assert "Session has expired" in res["error"]
        assert "190" in res["error"]


def test_meta_webhook_hmac_signature():
    secret = "my_app_secret_123"
    payload = b'{"object":"page","entry":[]}'
    
    # Generate valid signature
    valid_hash = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    sig_header = f"sha256={valid_hash}"

    # Valid
    assert verify_meta_signature(payload, sig_header, secret) is True

    # Invalid header prefix
    assert verify_meta_signature(payload, valid_hash, secret) is False

    # Tampered payload
    tampered = b'{"object":"tampered"}'
    assert verify_meta_signature(tampered, sig_header, secret) is False

    # Wrong secret
    assert verify_meta_signature(payload, sig_header, "wrong_secret") is False
