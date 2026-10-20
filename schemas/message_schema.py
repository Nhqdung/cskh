"""
Schemas for normalized messages and platform events.
Ensures consistent handling across Discord, Meta Messenger, and Meta Comments.
"""

import datetime
from typing import Optional
from pydantic import BaseModel, Field


class NormalizedMessageSchema(BaseModel):
    """Platform-agnostic normalized representation of an incoming or backfilled message."""
    platform: str # "discord" | "meta_messenger" | "meta_comment"
    platform_message_id: str
    platform_conversation_id: Optional[str] = None
    server_id: Optional[str] = None
    channel_id: Optional[str] = None
    author_id: str
    author_name: Optional[str] = None
    author_is_employee: bool = False
    is_bot: bool = False
    content: str
    timestamp_utc: datetime.datetime
    timestamp_local: Optional[datetime.datetime] = None
    reference_message_id: Optional[str] = None
    is_reply_to_customer: bool = False
    verification_status: str = "unverified" # "verified" | "unverified" | "unverified_agent" | "manual_review"
    shift_date: Optional[str] = None
    shift_num: Optional[int] = None
