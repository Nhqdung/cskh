"""
Unit tests for SecurityService and PII scrubbing.
"""

import logging
from services.security_service import SecurityService, SensitiveDataFilter


def test_sanitize_phone_numbers():
    text1 = "Khách hàng số đt 0912345678 cần hỗ trợ gấp"
    cleaned1 = SecurityService.sanitize_text(text1)
    assert "0912345678" not in cleaned1
    assert "[SỐ ĐIỆN THOẠI ĐÃ ẨN]" in cleaned1

    text2 = "Liên hệ qua +84 987 654 321 hoặc 0903-123-456"
    cleaned2 = SecurityService.sanitize_text(text2)
    assert "+84" not in cleaned2
    assert "0903" not in cleaned2


def test_sanitize_emails():
    text = "Gửi hóa đơn về email customer.vip@gmail.com giúp tôi"
    cleaned = SecurityService.sanitize_text(text)
    assert "customer.vip@gmail.com" not in cleaned
    assert "[EMAIL ĐÃ ẨN]" in cleaned


def test_sanitize_tokens():
    text = "Sử dụng token Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9 để gọi API"
    cleaned = SecurityService.sanitize_text(text)
    assert "eyJhbGciOiJIUzI1Ni" not in cleaned


def test_sanitize_customer_identifier():
    cid = SecurityService.sanitize_customer_identifier("user_987654321", "discord")
    assert cid == "Khach_4321"
    assert "987654321" not in cid

    cid_empty = SecurityService.sanitize_customer_identifier("", "meta")
    assert cid_empty == "Khach_AnDanh"


def test_log_filter_scrubs_secrets():
    log_filter = SensitiveDataFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Error connecting with token AIzaSyD3x9ExampleKey1234567890ABCDEF",
        args=(),
        exc_info=None,
    )
    log_filter.filter(record)
    assert "AIzaSyD3x9ExampleKey" not in record.msg
    assert "[REDACTED_SECRET]" in record.msg
