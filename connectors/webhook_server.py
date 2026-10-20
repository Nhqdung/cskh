"""
Meta Webhook Server and Signature Verifier.
Receives real-time events from Meta Webhooks (Messenger, Comments).
Features:
- GET verification challenge handler (hub.verify_token / hub.challenge).
- POST payload processing with HMAC-SHA256 signature verification (x-hub-signature-256).
- Audit event logging into platform_events table.
"""

import hmac
import hashlib
import json
import logging
from typing import Optional, Tuple
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from database.connection import db_manager
from models.orm import PlatformEvent
from services.security_service import SecurityService

logger = logging.getLogger("CSKHAssistant.Webhook")


def verify_meta_signature(payload_bytes: bytes, signature_header: Optional[str], app_secret: str) -> bool:
    """Verifies that the webhook payload was actually sent by Meta using HMAC-SHA256."""
    if not signature_header or not app_secret:
        return False

    if not signature_header.startswith("sha256="):
        return False

    expected_sig = signature_header[len("sha256="):]
    mac = hmac.new(app_secret.encode("utf-8"), msg=payload_bytes, digestmod=hashlib.sha256)
    computed_sig = mac.hexdigest()

    return hmac.compare_digest(computed_sig, expected_sig)


class MetaWebhookHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Meta Webhook events."""

    verify_token = SecurityService.get_credential("META_WEBHOOK_VERIFY_TOKEN", "default_verify_token")
    app_secret = SecurityService.get_credential("META_APP_SECRET", "")

    def do_GET(self):
        """Handle Meta Webhook verification handshake."""
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        mode = params.get("hub.mode", [None])[0]
        token = params.get("hub.verify_token", [None])[0]
        challenge = params.get("hub.challenge", [None])[0]

        if mode == "subscribe" and token == self.verify_token:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write((challenge or "").encode("utf-8"))
            logger.info("Meta webhook verified successfully.")
        else:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Verification failed")

    def do_POST(self):
        """Receive and log webhook event payload."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        sig = self.headers.get("x-hub-signature-256")
        if self.app_secret and not verify_meta_signature(body, sig, self.app_secret):
            logger.warning("Invalid webhook signature rejected.")
            self.send_response(403)
            self.end_headers()
            return

        try:
            payload = json.loads(body.decode("utf-8"))
            event_type = payload.get("object", "unknown")

            with db_manager.get_session() as session:
                event_record = PlatformEvent(
                    platform="meta",
                    event_type=f"webhook_{event_type}",
                    payload_json=json.dumps(payload),
                )
                session.add(event_record)
                session.commit()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"received"}')

        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            self.send_response(500)
            self.end_headers()

    def log_message(self, format, *args):
        # Override to suppress raw server logs containing sensitive paths
        pass
