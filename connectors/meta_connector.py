"""
Official Meta Graph API Connector for Facebook Fanpage & Messenger.
Handles:
- Meta Graph API calls via httpx.
- Connection & permission testing (pages_messaging, pages_read_engagement).
- Fetching conversations and comments within a time window.
- Respecting Meta API agent ambiguity: marks Page replies as 'unverified_agent'
  requiring human audit, rather than fabricating employee identity.
"""

import os
import datetime
import logging
from typing import Optional, List, Dict, Any
import httpx

from schemas.message_schema import NormalizedMessageSchema
from services.security_service import SecurityService
from services.shift_service import ShiftService

logger = logging.getLogger("CSKHAssistant.Meta")


class MetaConnector:
    """Interfaces with Meta Graph API."""

    def __init__(
        self,
        page_id: Optional[str] = None,
        page_access_token: Optional[str] = None,
        api_version: str = "v20.0",
    ):
        self.page_id = page_id or SecurityService.get_credential("META_PAGE_ID")
        self.page_access_token = page_access_token or SecurityService.get_credential("META_PAGE_ACCESS_TOKEN")
        self.api_version = api_version or os.getenv("META_GRAPH_API_VERSION", "v20.0")
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    def is_configured(self) -> bool:
        """Check if Page ID and Access Token are configured."""
        return bool(
            self.page_id
            and not self.page_id.startswith("your_")
            and self.page_access_token
            and not self.page_access_token.startswith("your_")
        )

    def test_connection(self) -> Dict[str, Any]:
        """Test connection against Meta Graph API and check Page details & permissions."""
        if not self.is_configured():
            return {
                "success": False,
                "error": "Chưa cấu hình Meta Page ID hoặc Meta Page Access Token.",
                "details": None,
            }

        url = f"{self.base_url}/{self.page_id}"
        params = {
            "fields": "id,name,category,tasks",
            "access_token": self.page_access_token,
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, params=params)
                data = resp.json()

                if resp.status_code == 200:
                    return {
                        "success": True,
                        "error": None,
                        "details": {
                            "page_id": data.get("id"),
                            "page_name": data.get("name"),
                            "category": data.get("category"),
                            "tasks": data.get("tasks", []),
                        },
                    }
                else:
                    err_msg = data.get("error", {}).get("message", "Lỗi Graph API không xác định")
                    code = data.get("error", {}).get("code")
                    return {
                        "success": False,
                        "error": f"Meta Graph API trả về lỗi ({code}): {err_msg}",
                        "details": data.get("error"),
                    }
        except httpx.RequestError as ex:
            return {
                "success": False,
                "error": f"Lỗi mạng khi kết nối tới Meta: {ex}",
                "details": None,
            }

    def fetch_messenger_conversations(
        self,
        start_utc: datetime.datetime,
        end_utc: datetime.datetime,
    ) -> List[NormalizedMessageSchema]:
        """Fetches Messenger messages within the shift window."""
        if not self.is_configured():
            return []

        messages: List[NormalizedMessageSchema] = []
        url = f"{self.base_url}/{self.page_id}/conversations"
        params = {
            "fields": "id,updated_time,messages{id,created_time,from,message}",
            "access_token": self.page_access_token,
            "limit": 25,
        }

        try:
            with httpx.Client(timeout=20.0) as client:
                resp = client.get(url, params=params)
                if resp.status_code != 200:
                    logger.warning(f"Failed to fetch conversations: {resp.text}")
                    return []

                data = resp.json().get("data", [])
                for conv in data:
                    conv_id = conv.get("id")
                    raw_msgs = conv.get("messages", {}).get("data", [])
                    for m in raw_msgs:
                        created_str = m.get("created_time")
                        if not created_str:
                            continue

                        # Parse ISO 8601 UTC
                        dt_utc = datetime.datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                        if not (start_utc <= dt_utc < end_utc):
                            continue

                        author_info = m.get("from", {})
                        author_id = author_info.get("id", "unknown")
                        is_page_author = (author_id == self.page_id)

                        dt_local = ShiftService.utc_to_local(dt_utc)
                        shift_date, shift_num = ShiftService.resolve_shift_for_timestamp(dt_utc)

                        # META LIMITATION:
                        # Graph API attributes all replies to Page ID.
                        # It cannot prove which individual staff sent it.
                        # We mark as 'unverified_agent' so it does NOT falsely inflate verified stats.
                        if is_page_author:
                            verification = "unverified_agent"
                            author_name = "Page Representative"
                            is_emp = False # Must be manually verified
                            is_reply = True
                        else:
                            verification = "unverified"
                            author_name = SecurityService.sanitize_customer_identifier(author_id, "meta")
                            is_emp = False
                            is_reply = False

                        messages.append(
                            NormalizedMessageSchema(
                                platform="meta_messenger",
                                platform_message_id=m.get("id"),
                                platform_conversation_id=conv_id,
                                author_id=author_id,
                                author_name=author_name,
                                author_is_employee=is_emp,
                                is_bot=False,
                                content=m.get("message", "") or "",
                                timestamp_utc=dt_utc,
                                timestamp_local=dt_local,
                                reference_message_id=None,
                                is_reply_to_customer=is_reply,
                                verification_status=verification,
                                shift_date=shift_date,
                                shift_num=shift_num,
                            )
                        )
        except Exception as e:
            logger.error(f"Error fetching Meta messages: {SecurityService.scrub_log_message(str(e))}")

        return messages
