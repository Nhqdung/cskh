"""
Data cleanup and retention service.
Purges old messages, platform events, and sync runs older than configured retention period.
Preserves audit logs and finalized reports.
"""

import datetime
from sqlalchemy import delete
from database.connection import db_manager
from models.orm import Message, PlatformEvent, SyncRun, AuditLog


def purge_old_data(retention_days: int = 60) -> dict:
    """Purge records older than retention_days.
    
    Returns a dictionary of deleted row counts.
    """
    cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=retention_days)
    deleted_counts = {}

    with db_manager.get_session() as session:
        # 1. Old platform events
        res_events = session.execute(
            delete(PlatformEvent).where(PlatformEvent.received_at_utc < cutoff_date)
        )
        deleted_counts["platform_events"] = res_events.rowcount

        # 2. Old sync runs
        res_sync = session.execute(
            delete(SyncRun).where(SyncRun.started_at_utc < cutoff_date)
        )
        deleted_counts["sync_runs"] = res_sync.rowcount

        # 3. Old messages
        res_msg = session.execute(
            delete(Message).where(Message.timestamp_utc < cutoff_date)
        )
        deleted_counts["messages"] = res_msg.rowcount

        # Record audit log
        session.add(
            AuditLog(
                action="PURGE_OLD_DATA",
                details=f"Purged records older than {retention_days} days ({cutoff_date.isoformat()}): {deleted_counts}",
            )
        )
        session.commit()

    return deleted_counts
