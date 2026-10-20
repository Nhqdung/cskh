"""
SQLAlchemy ORM Models for Personal CSKH Reporting Assistant.
Defines schemas for all 12 core tables:
1. settings
2. work_shifts
3. messages
4. conversations
5. platform_events
6. tickets
7. ai_classifications
8. daily_metrics
9. shift_checklists
10. shift_reports
11. sync_runs
12. audit_logs
"""

import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass


class Setting(Base):
    """Stores key-value settings, configurations, and state."""
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at_utc: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow
    )


class WorkShift(Base):
    """Stores work shift configurations (Ca 1, Ca 2, Ca 3)."""
    __tablename__ = "work_shifts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shift_num: Mapped[int] = mapped_column(Integer, unique=True, nullable=False) # 1, 2, 3
    name: Mapped[str] = mapped_column(String(50), nullable=False) # e.g. "Ca 1"
    start_time: Mapped[str] = mapped_column(String(5), nullable=False) # HH:MM e.g. "07:00"
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)   # HH:MM e.g. "15:00"
    crosses_midnight: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Conversation(Base):
    """Tracks customer conversations, threads, and ticket channels."""
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(30), nullable=False) # 'discord' | 'meta'
    platform_conversation_id: Mapped[str] = mapped_column(String(150), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="open") # open | closed | pending
    customer_identifier: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # anonymized
    first_activity_utc: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_utc: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    first_response_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True) # SLA calculation

    __table_args__ = (
        UniqueConstraint("platform", "platform_conversation_id", name="uq_platform_conv"),
        Index("idx_conv_platform_id", "platform", "platform_conversation_id"),
    )

    messages: Mapped[List["Message"]] = relationship("Message", back_populates="conversation")


class Message(Base):
    """Stores normalized messages from Discord and Meta."""
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(30), nullable=False) # 'discord' | 'meta_messenger' | 'meta_comment'
    platform_message_id: Mapped[str] = mapped_column(String(150), nullable=False)
    platform_conversation_id: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    server_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    channel_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    author_id: Mapped[str] = mapped_column(String(100), nullable=False)
    author_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # anonymized customer or employee
    author_is_employee: Mapped[bool] = mapped_column(Boolean, default=False)
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    timestamp_utc: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timestamp_local: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    reference_message_id: Mapped[Optional[str]] = mapped_column(String(150), nullable=True) # in-reply-to
    is_reply_to_customer: Mapped[bool] = mapped_column(Boolean, default=False)
    
    verification_status: Mapped[str] = mapped_column(String(30), default="unverified") # verified | unverified | unverified_agent | manual_review
    shift_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True) # YYYY-MM-DD in local time
    shift_num: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)     # 1, 2, 3
    
    conversation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("conversations.id"), nullable=True)
    conversation: Mapped[Optional["Conversation"]] = relationship("Conversation", back_populates="messages")
    ai_classification: Mapped[Optional["AIClassification"]] = relationship("AIClassification", back_populates="message", uselist=False)

    __table_args__ = (
        UniqueConstraint("platform", "platform_message_id", name="uq_platform_msg"),
        Index("idx_msg_shift", "shift_date", "shift_num"),
        Index("idx_msg_timestamp", "timestamp_utc"),
        Index("idx_msg_author_emp", "author_is_employee", "verification_status"),
    )


class PlatformEvent(Base):
    """Raw or normalized platform event audit log (webhooks, edits, deletions)."""
    __tablename__ = "platform_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(30), nullable=False) # 'discord' | 'meta'
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_id: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    received_at_utc: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.utcnow)

    __table_args__ = (
        Index("idx_event_platform_type", "platform", "event_type"),
    )


class Ticket(Base):
    """Ticket state tracking (Discord tickets, Meta conversations marked as tickets)."""
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(30), nullable=False)
    platform_ticket_id: Mapped[str] = mapped_column(String(150), nullable=False)
    channel_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="open") # open | closed | pending | escalated
    opened_at_utc: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at_utc: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_employee: Mapped[bool] = mapped_column(Boolean, default=False)
    last_customer_message_utc: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_pending_over_12h: Mapped[bool] = mapped_column(Boolean, default=False)
    shift_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    shift_num: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        UniqueConstraint("platform", "platform_ticket_id", name="uq_platform_ticket"),
        Index("idx_ticket_status_shift", "status", "shift_date", "shift_num"),
    )


class AIClassification(Base):
    """Structured Gemini AI classification and extracted entities for conversations/messages."""
    __tablename__ = "ai_classifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[Optional[int]] = mapped_column(ForeignKey("messages.id"), nullable=True)
    conversation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("conversations.id"), nullable=True)
    
    # Specific CSKH Labels required by prompt
    slow_network_report: Mapped[bool] = mapped_column(Boolean, default=False)
    device_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # e.g. "PC-04", "May 12"
    device_tested: Mapped[bool] = mapped_column(Boolean, default=False) # Khách đã thực sự test máy
    feedback_received: Mapped[bool] = mapped_column(Boolean, default=False) # Đã nhận được feedback sau test
    positive_feedback: Mapped[bool] = mapped_column(Boolean, default=False)
    ticket_opened: Mapped[bool] = mapped_column(Boolean, default=False)
    ticket_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_owner: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # "Dương" | "Tùng"
    escalation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    needs_follow_up: Mapped[bool] = mapped_column(Boolean, default=False)
    follow_up_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pending_case: Mapped[bool] = mapped_column(Boolean, default=False)
    pending_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    needs_manager_review: Mapped[bool] = mapped_column(Boolean, default=False)
    manager_review_desc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    evidence_message_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # JSON list of IDs
    needs_manual_review: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    
    raw_ai_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_modified: Mapped[bool] = mapped_column(Boolean, default=False)
    user_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at_utc: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.utcnow)

    message: Mapped[Optional["Message"]] = relationship("Message", back_populates="ai_classification")

    __table_args__ = (
        Index("idx_ai_class_msg", "message_id"),
        Index("idx_ai_class_conv", "conversation_id"),
    )


class DailyMetric(Base):
    """Calculated and human-reviewed statistics for a specific shift."""
    __tablename__ = "daily_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_str: Mapped[str] = mapped_column(String(10), nullable=False) # YYYY-MM-DD
    shift_num: Mapped[int] = mapped_column(Integer, nullable=False)   # 1, 2, 3
    
    messages_replied: Mapped[int] = mapped_column(Integer, default=0)
    slow_network_count: Mapped[int] = mapped_column(Integer, default=0)
    slow_network_devices: Mapped[Optional[str]] = mapped_column(Text, default="") # "PC-01, PC-02"
    customers_tested: Mapped[int] = mapped_column(Integer, default=0)
    feedback_count: Mapped[int] = mapped_column(Integer, default=0)
    tickets_opened: Mapped[int] = mapped_column(Integer, default=0)
    tickets_closed: Mapped[int] = mapped_column(Integer, default=0)
    escalate_count: Mapped[int] = mapped_column(Integer, default=0)
    escalate_details: Mapped[Optional[str]] = mapped_column(Text, default="")
    
    pending_cases_desc: Mapped[Optional[str]] = mapped_column(Text, default="")
    follow_up_count: Mapped[int] = mapped_column(Integer, default=0)
    follow_up_desc: Mapped[Optional[str]] = mapped_column(Text, default="")
    
    # Extra for Shift 3
    best_positive_feedback: Mapped[Optional[str]] = mapped_column(Text, default="")
    manager_review_issues: Mapped[Optional[str]] = mapped_column(Text, default="")

    unverified_count: Mapped[int] = mapped_column(Integer, default=0)
    is_user_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    computed_at_utc: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("date_str", "shift_num", name="uq_daily_metric_date_shift"),
        Index("idx_metric_date_shift", "date_str", "shift_num"),
    )


class ShiftChecklist(Base):
    """Checklist items status per shift."""
    __tablename__ = "shift_checklists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_str: Mapped[str] = mapped_column(String(10), nullable=False) # YYYY-MM-DD
    shift_num: Mapped[int] = mapped_column(Integer, nullable=False)   # 1, 2, 3
    item_key: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="not_checked") # completed | incomplete | not_applicable | not_checked
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # if incomplete
    evidence_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at_utc: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("date_str", "shift_num", "item_key", name="uq_shift_checklist_item"),
        Index("idx_checklist_date_shift", "date_str", "shift_num"),
    )


class ShiftReport(Base):
    """Saved historical shift reports."""
    __tablename__ = "shift_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_str: Mapped[str] = mapped_column(String(10), nullable=False) # YYYY-MM-DD
    shift_num: Mapped[int] = mapped_column(Integer, nullable=False)   # 1, 2, 3
    employee_name: Mapped[str] = mapped_column(String(100), nullable=False)
    report_content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="finalized") # draft | finalized
    created_at_utc: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at_utc: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.utcnow)

    __table_args__ = (
        Index("idx_report_date_shift", "date_str", "shift_num"),
    )


class SyncRun(Base):
    """Records execution status and count of synchronization jobs."""
    __tablename__ = "sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(30), nullable=False) # 'discord' | 'meta' | 'all'
    sync_type: Mapped[str] = mapped_column(String(50), nullable=False) # 'live_event' | 'historical_backfill' | 'manual'
    status: Mapped[str] = mapped_column(String(30), default="running") # running | success | failed | partial
    records_synced: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at_utc: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    finished_at_utc: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    """Audit log for user actions, credential changes, data purges."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp_utc: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=datetime.datetime.utcnow)
