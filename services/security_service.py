"""
Security, PII Scrubbing, and Credential Management Service.
- Sanitizes PII (phone numbers, emails, customer names, usernames) before sending to AI.
- Scrubs sensitive tokens/passwords from application logs.
- Manages secure credential retrieval from environment variables and keyring.
"""

import re
import os
import logging
from typing import Optional, Dict

logger = logging.getLogger("CSKHAssistant.Security")

# Regex patterns for Vietnamese and International PII
PHONE_REGEX = re.compile(r'(?:\+?84[\s.-]?|0)(?:\d[\s.-]?){8,10}\d')
EMAIL_REGEX = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
TOKEN_REGEX = re.compile(r'(Bearer\s+[A-Za-z0-9_\-\.]+)|([A-Za-z0-9_\-]{24,}\.[A-Za-z0-9_\-]{6,}\.[A-Za-z0-9_\-]+)|(AIza[0-9A-Za-z-_]{30,45})')


class SecurityService:
    """Provides PII sanitization and credential management."""

    @staticmethod
    def sanitize_text(text: str) -> str:
        """Removes or masks phone numbers, emails, and sensitive patterns from text.
        
        Preserves device names, technical issues, and CSKH context.
        """
        if not text:
            return ""

        # Mask phone numbers
        sanitized = PHONE_REGEX.sub("[SỐ ĐIỆN THOẠI ĐÃ ẨN]", text)
        # Mask emails
        sanitized = EMAIL_REGEX.sub("[EMAIL ĐÃ ẨN]", sanitized)
        # Mask token-like strings
        sanitized = TOKEN_REGEX.sub("[TOKEN ĐÃ ẨN]", sanitized)

        return sanitized

    @staticmethod
    def sanitize_customer_identifier(raw_id: str, platform: str) -> str:
        """Converts raw customer username or ID into an anonymized identifier like 'Khach_1234'."""
        if not raw_id:
            return "Khach_AnDanh"
        # Take last 4 characters of hash or id
        clean_id = re.sub(r'[^a-zA-Z0-9]', '', raw_id)
        short_suffix = clean_id[-4:] if len(clean_id) >= 4 else clean_id.zfill(4)
        return f"Khach_{short_suffix}"

    @staticmethod
    def scrub_log_message(msg: str) -> str:
        """Scrubs tokens, secrets, and PII from log strings."""
        if not msg:
            return ""
        scrubbed = TOKEN_REGEX.sub("[REDACTED_SECRET]", str(msg))
        scrubbed = PHONE_REGEX.sub("[REDACTED_PHONE]", scrubbed)
        return scrubbed

    @staticmethod
    def get_credential(key: str, default: Optional[str] = None) -> Optional[str]:
        """Safely fetch credential from environment variable or keyring fallback."""
        val = os.getenv(key)
        if val and val.strip() and not val.strip().startswith("your_"):
            return val.strip()
        
        # Check keyring if available
        try:
            import keyring
            keyring_val = keyring.get_password("PersonalCSKHAssistant", key)
            if keyring_val:
                return keyring_val.strip()
        except Exception as e:
            logger.debug(f"Keyring lookup skipped for {key}: {e}")

        return default

    @staticmethod
    def set_credential(key: str, value: str) -> bool:
        """Save credential to keyring or environment for the current process."""
        os.environ[key] = value
        try:
            import keyring
            keyring.set_password("PersonalCSKHAssistant", key, value)
            return True
        except Exception as e:
            logger.warning(f"Could not persist {key} to keyring: {e}")
            return False


class SensitiveDataFilter(logging.Filter):
    """Logging filter to automatically scrub sensitive tokens and phone numbers from logs."""
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = SecurityService.scrub_log_message(record.msg)
        return True
