"""
Unit tests for database deduplication, sync resilience, and data cleanup.
"""

import datetime
from sqlalchemy import select, func
from models.orm import Message, PlatformEvent, SyncRun
from schemas.message_schema import NormalizedMessageSchema
from services.sync_service import SyncService
from database.cleanup import purge_old_data


def test_message_upsert_anti_duplicate(test_db):
    sync_svc = SyncService()
    now_utc = datetime.datetime.utcnow()

    norm1 = NormalizedMessageSchema(
        platform="discord",
        platform_message_id="uniq_msg_100",
        author_id="user_1",
        content="Nội dung ban đầu",
        timestamp_utc=now_utc,
        shift_date="2026-10-20",
        shift_num=1,
    )

    # First insert
    is_new1, msg1 = sync_svc.upsert_normalized_message(norm1)
    assert is_new1 is True
    assert msg1.content == "Nội dung ban đầu"

    # Second insert with same message ID but modified content (upsert)
    norm2 = NormalizedMessageSchema(
        platform="discord",
        platform_message_id="uniq_msg_100",
        author_id="user_1",
        content="Nội dung đã được chỉnh sửa",
        timestamp_utc=now_utc,
        shift_date="2026-10-20",
        shift_num=1,
    )

    is_new2, msg2 = sync_svc.upsert_normalized_message(norm2)
    assert is_new2 is False # NOT new, was updated!

    with test_db.get_session() as session:
        count = session.execute(
            select(func.count(Message.id)).where(Message.platform_message_id == "uniq_msg_100")
        ).scalar()
        assert count == 1 # Anti-duplicate guaranteed!

        updated = session.execute(
            select(Message).where(Message.platform_message_id == "uniq_msg_100")
        ).scalar_one()
        assert updated.content == "Nội dung đã được chỉnh sửa"


def test_sync_failure_does_not_delete_old_data(test_db):
    sync_svc = SyncService()
    now_utc = datetime.datetime.utcnow()

    # Pre-existing message
    norm = NormalizedMessageSchema(
        platform="discord",
        platform_message_id="existing_msg",
        author_id="user_1",
        content="Tin nhắn cũ",
        timestamp_utc=now_utc,
        shift_date="2026-10-20",
        shift_num=1,
    )
    sync_svc.upsert_normalized_message(norm)

    # Trigger sync with unconfigured connectors (fails)
    res = sync_svc.sync_shift_history("2026-10-20", 1)
    assert res["status"] in ("failed", "partial")

    # Verify old data is completely preserved
    with test_db.get_session() as session:
        existing = session.execute(
            select(Message).where(Message.platform_message_id == "existing_msg")
        ).scalar_one_or_none()
        assert existing is not None
        assert existing.content == "Tin nhắn cũ"


def test_data_retention_purge(test_db):
    with test_db.get_session() as session:
        # Old message from 90 days ago
        old_time = datetime.datetime.utcnow() - datetime.timedelta(days=90)
        session.add(
            Message(
                platform="discord",
                platform_message_id="old_msg_to_purge",
                author_id="u1",
                content="Tin quá hạn",
                timestamp_utc=old_time,
                timestamp_local=old_time,
                shift_date="2026-07-01",
                shift_num=1,
            )
        )
        # Recent message from today
        recent_time = datetime.datetime.utcnow()
        session.add(
            Message(
                platform="discord",
                platform_message_id="recent_msg_to_keep",
                author_id="u2",
                content="Tin mới hôm nay",
                timestamp_utc=recent_time,
                timestamp_local=recent_time,
                shift_date="2026-10-20",
                shift_num=1,
            )
        )
        session.commit()

    # Purge records older than 60 days
    deleted = purge_old_data(retention_days=60)
    assert deleted["messages"] >= 1

    with test_db.get_session() as session:
        old_check = session.execute(
            select(Message).where(Message.platform_message_id == "old_msg_to_purge")
        ).scalar_one_or_none()
        assert old_check is None # Purged!

        recent_check = session.execute(
            select(Message).where(Message.platform_message_id == "recent_msg_to_keep")
        ).scalar_one_or_none()
        assert recent_check is not None # Kept!
