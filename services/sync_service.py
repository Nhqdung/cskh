"""
Synchronization Orchestration Service.
Coordinates fetching from Discord Bot and Meta Graph API, persists messages into SQLite,
guarantees deduplication via upsert, and links sync execution records in sync_runs table.
"""

import datetime
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select, and_

from database.connection import db_manager
from models.orm import Message, Conversation, SyncRun, AIClassification
from schemas.message_schema import NormalizedMessageSchema
from connectors.discord_connector import DiscordConnector
from connectors.meta_connector import MetaConnector
from services.classification_service import ClassificationService
from services.shift_service import ShiftService

logger = logging.getLogger("CSKHAssistant.Sync")


class SyncService:
    """Coordinates multi-platform sync into SQLite database."""

    def __init__(
        self,
        discord_connector: Optional[DiscordConnector] = None,
        meta_connector: Optional[MetaConnector] = None,
        classification_service: Optional[ClassificationService] = None,
    ):
        self.discord = discord_connector or DiscordConnector()
        self.meta = meta_connector or MetaConnector()
        self.ai = classification_service or ClassificationService()

    def upsert_normalized_message(self, norm: NormalizedMessageSchema) -> Tuple[bool, Message]:
        """Insert or update a message record cleanly, avoiding duplicates.
        
        Returns:
            (is_new, Message_instance)
        """
        with db_manager.get_session() as session:
            # 1. Upsert Conversation if needed
            conv_id_fk = None
            if norm.platform_conversation_id:
                conv = session.execute(
                    select(Conversation).where(
                        and_(
                            Conversation.platform == norm.platform,
                            Conversation.platform_conversation_id == norm.platform_conversation_id,
                        )
                    )
                ).scalar_one_or_none()
                if not conv:
                    conv = Conversation(
                        platform=norm.platform,
                        platform_conversation_id=norm.platform_conversation_id,
                        customer_identifier=norm.author_name if not norm.author_is_employee else "Unknown_Customer",
                        first_activity_utc=norm.timestamp_utc,
                        last_activity_utc=norm.timestamp_utc,
                    )
                    session.add(conv)
                    session.flush()
                else:
                    conv.last_activity_utc = max(conv.last_activity_utc or norm.timestamp_utc, norm.timestamp_utc)
                conv_id_fk = conv.id

            # 2. Check if message already exists
            existing = session.execute(
                select(Message).where(
                    and_(
                        Message.platform == norm.platform,
                        Message.platform_message_id == norm.platform_message_id,
                    )
                )
            ).scalar_one_or_none()

            if existing:
                # Update attributes if needed
                existing.content = norm.content
                existing.shift_date = norm.shift_date
                existing.shift_num = norm.shift_num
                if norm.reference_message_id:
                    existing.reference_message_id = norm.reference_message_id
                session.commit()
                return False, existing
            else:
                msg = Message(
                    platform=norm.platform,
                    platform_message_id=norm.platform_message_id,
                    platform_conversation_id=norm.platform_conversation_id,
                    server_id=norm.server_id,
                    channel_id=norm.channel_id,
                    author_id=norm.author_id,
                    author_name=norm.author_name,
                    author_is_employee=norm.author_is_employee,
                    is_bot=norm.is_bot,
                    content=norm.content,
                    timestamp_utc=norm.timestamp_utc,
                    timestamp_local=norm.timestamp_local or ShiftService.utc_to_local(norm.timestamp_utc),
                    reference_message_id=norm.reference_message_id,
                    is_reply_to_customer=norm.is_reply_to_customer,
                    verification_status=norm.verification_status,
                    shift_date=norm.shift_date,
                    shift_num=norm.shift_num,
                    conversation_id=conv_id_fk,
                )
                session.add(msg)
                session.commit()
                return True, msg

    def sync_shift_history(self, date_str: str, shift_num: int) -> Dict[str, Any]:
        """Runs backfill sync for the entire time window of a specific shift.
        
        Returns summary dictionary.
        """
        shift_window = ShiftService.get_shift_window(date_str, shift_num)
        start_utc = shift_window.start_utc
        end_utc = shift_window.end_utc

        # Record SyncRun in DB
        sync_run_id = None
        with db_manager.get_session() as session:
            sr = SyncRun(
                platform="all",
                sync_type="shift_backfill",
                status="running",
                started_at_utc=datetime.datetime.utcnow(),
            )
            session.add(sr)
            session.flush()
            sync_run_id = sr.id
            session.commit()

        synced_count = 0
        errors: List[str] = []

        # 1. Sync Discord
        if self.discord.is_configured():
            try:
                import asyncio
                discord_msgs = asyncio.run(self.discord.fetch_history_for_window(start_utc, end_utc))
                for dm in discord_msgs:
                    is_new, _ = self.upsert_normalized_message(dm)
                    if is_new:
                        synced_count += 1
            except Exception as e:
                errors.append(f"Discord sync: {e}")
        else:
            errors.append("Discord chưa được cấu hình credentials.")

        # 2. Sync Meta
        if self.meta.is_configured():
            try:
                meta_msgs = self.meta.fetch_messenger_conversations(start_utc, end_utc)
                for mm in meta_msgs:
                    is_new, _ = self.upsert_normalized_message(mm)
                    if is_new:
                        synced_count += 1
            except Exception as e:
                errors.append(f"Meta sync: {e}")
        else:
            errors.append("Meta chưa được cấu hình credentials.")

        # Update SyncRun status
        final_status = "success" if not errors else ("partial" if synced_count > 0 else "failed")
        with db_manager.get_session() as session:
            sr = session.get(SyncRun, sync_run_id)
            if sr:
                sr.status = final_status
                sr.records_synced = synced_count
                sr.error_message = "; ".join(errors) if errors else None
                sr.finished_at_utc = datetime.datetime.utcnow()
                session.commit()

        return {
            "status": final_status,
            "records_synced": synced_count,
            "errors": errors,
            "window": {
                "date_str": date_str,
                "shift_num": shift_num,
                "start_local": shift_window.start_local.isoformat(),
                "end_local": shift_window.end_local.isoformat(),
            },
        }

    def manual_verify_message(self, message_id: int, is_verified: bool, mark_as_reply: bool = True) -> bool:
        """Allows human agent to confirm or reject a message in human-in-the-loop audit."""
        with db_manager.get_session() as session:
            msg = session.get(Message, message_id)
            if not msg:
                return False
            msg.verification_status = "verified" if is_verified else "unverified"
            if is_verified:
                msg.author_is_employee = True
                msg.is_reply_to_customer = mark_as_reply
            session.commit()
            return True
