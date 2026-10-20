"""
Independent Statistics Calculation Layer.
Computes all core CSKH metrics strictly from verified records.
Does NOT rely on Gemini for raw counters.
Collects evidence links and identifiers for human-in-the-loop audit.
"""

import json
from typing import List, Dict, Any, Tuple
from sqlalchemy import select, and_, func, or_
from database.connection import db_manager
from models.orm import Message, Conversation, Ticket, AIClassification, DailyMetric
from schemas.report_schema import MetricsDataSchema
from services.shift_service import ShiftService


class MetricsService:
    """Calculates, aggregates, and stores shift metrics."""

    @classmethod
    def calculate_shift_metrics(cls, date_str: str, shift_num: int) -> Tuple[MetricsDataSchema, List[Dict[str, Any]]]:
        """Calculates shift metrics for the specified date and shift number.
        
        Returns:
            (MetricsDataSchema, evidence_items_list)
        """
        shift_window = ShiftService.get_shift_window(date_str, shift_num)
        start_utc = shift_window.start_utc
        end_utc = shift_window.end_utc

        evidence_items: List[Dict[str, Any]] = []

        with db_manager.get_session() as session:
            # 1. Total employee messages in shift window
            # Excludes bots, webhooks, colleagues
            emp_msgs = session.execute(
                select(Message).where(
                    and_(
                        Message.timestamp_utc >= start_utc,
                        Message.timestamp_utc < end_utc,
                        Message.author_is_employee == True,
                        Message.is_bot == False,
                    )
                )
            ).scalars().all()

            # Separate verified employee replies
            verified_replies = [
                m for m in emp_msgs
                if m.verification_status == "verified" and m.is_reply_to_customer == True
            ]

            # Cases needing manual audit/verification (unverified agents or marked manual review)
            unverified_msgs = session.execute(
                select(Message).where(
                    and_(
                        Message.timestamp_utc >= start_utc,
                        Message.timestamp_utc < end_utc,
                        Message.verification_status.in_(["unverified_agent", "manual_review"]),
                    )
                )
            ).scalars().all()

            unverified_count = len(unverified_msgs)

            # Messages replied count: strictly verified replies to customers
            messages_replied_count = len(verified_replies)

            # 2. Distinct conversations replied to
            replied_conv_ids = set()
            for m in verified_replies:
                if m.platform_conversation_id:
                    replied_conv_ids.add(m.platform_conversation_id)

            # 3. Tickets opened / closed in this shift window
            tickets_opened = session.execute(
                select(func.count(Ticket.id)).where(
                    and_(
                        Ticket.opened_at_utc >= start_utc,
                        Ticket.opened_at_utc < end_utc,
                    )
                )
            ).scalar() or 0

            tickets_closed = session.execute(
                select(func.count(Ticket.id)).where(
                    and_(
                        Ticket.closed_at_utc >= start_utc,
                        Ticket.closed_at_utc < end_utc,
                    )
                )
            ).scalar() or 0

            # 4. Consult AI Classification table for categorized qualitative events
            # Linked to messages or conversations occurring in this shift window
            classifications = session.execute(
                select(AIClassification, Message).join(
                    Message, AIClassification.message_id == Message.id
                ).where(
                    and_(
                        Message.timestamp_utc >= start_utc,
                        Message.timestamp_utc < end_utc,
                    )
                )
            ).all()

            slow_network_count = 0
            devices_set = set()
            customers_tested_set = set()
            feedback_count = 0
            positive_feedbacks: List[str] = []
            escalations: List[str] = []
            pending_cases: List[str] = []
            follow_ups: List[Tuple[str, str]] = []
            manager_reviews: List[str] = []

            for ai_cls, msg in classifications:
                # Slow network reports: verified customer report
                if ai_cls.slow_network_report:
                    slow_network_count += 1
                    if ai_cls.device_name and ai_cls.device_name.strip():
                        devices_set.add(ai_cls.device_name.strip())
                    evidence_items.append({
                        "type": "Mạng chậm",
                        "message_id": msg.platform_message_id,
                        "device": ai_cls.device_name or "N/A",
                        "snippet": msg.content[:80],
                    })

                # Customer actually tested device
                if ai_cls.device_tested:
                    customers_tested_set.add(msg.conversation_id or msg.id)
                    evidence_items.append({
                        "type": "Đã test máy",
                        "message_id": msg.platform_message_id,
                        "snippet": msg.content[:80],
                    })

                # Feedback received
                if ai_cls.feedback_received:
                    feedback_count += 1
                    evidence_items.append({
                        "type": "Feedback nhận được",
                        "message_id": msg.platform_message_id,
                        "positive": ai_cls.positive_feedback,
                        "snippet": msg.content[:80],
                    })
                    if ai_cls.positive_feedback:
                        positive_feedbacks.append(msg.content[:100])

                # Escalation to Duong / Tung
                if ai_cls.escalated and ai_cls.escalation_owner:
                    owner = ai_cls.escalation_owner.strip()
                    reason = ai_cls.escalation_reason.strip() if ai_cls.escalation_reason else "cần hỗ trợ kỹ thuật"
                    escalations.append(f"{owner}: {reason}")
                    evidence_items.append({
                        "type": "Escalate",
                        "owner": owner,
                        "reason": reason,
                        "message_id": msg.platform_message_id,
                    })

                # Pending cases
                if ai_cls.pending_case:
                    reason = ai_cls.pending_reason.strip() if ai_cls.pending_reason else "chờ khách phản hồi"
                    pending_cases.append(reason)

                # Follow-ups
                if ai_cls.needs_follow_up:
                    action = ai_cls.follow_up_action.strip() if ai_cls.follow_up_action else "kiểm tra lại tình trạng"
                    follow_ups.append((str(msg.id), action))

                # Manager review (Tùng)
                if ai_cls.needs_manager_review:
                    desc = ai_cls.manager_review_desc.strip() if ai_cls.manager_review_desc else "vấn đề kỹ thuật đặc biệt"
                    manager_reviews.append(desc)

            # Format fields
            devices_str = ", ".join(sorted(devices_set)) if devices_set else "không có"
            escalate_str = "; ".join(escalations) if escalations else "không có"
            pending_str = "; ".join(pending_cases[:2]) if pending_cases else "không có"
            
            follow_up_count = len(follow_ups)
            follow_up_desc = "; ".join([act for _, act in follow_ups[:2]]) if follow_ups else "không có"

            best_feedback = positive_feedbacks[0] if positive_feedbacks else "không có"
            manager_review_str = "; ".join(manager_reviews) if manager_reviews else "không có"

            # Check if there is an existing saved DailyMetric record with manual user overrides
            saved_metric = session.execute(
                select(DailyMetric).where(
                    and_(
                        DailyMetric.date_str == date_str,
                        DailyMetric.shift_num == shift_num,
                    )
                )
            ).scalar_one_or_none()

            if saved_metric and saved_metric.is_user_edited:
                # Keep user edited values
                data = MetricsDataSchema(
                    messages_replied=saved_metric.messages_replied,
                    slow_network_count=saved_metric.slow_network_count,
                    slow_network_devices=saved_metric.slow_network_devices or "không có",
                    customers_tested=saved_metric.customers_tested,
                    feedback_count=saved_metric.feedback_count,
                    tickets_opened=saved_metric.tickets_opened,
                    tickets_closed=saved_metric.tickets_closed,
                    escalate_count=saved_metric.escalate_count,
                    escalate_details=saved_metric.escalate_details or "không có",
                    pending_cases_desc=saved_metric.pending_cases_desc or "không có",
                    follow_up_count=saved_metric.follow_up_count,
                    follow_up_desc=saved_metric.follow_up_desc or "không có",
                    best_positive_feedback=saved_metric.best_positive_feedback or "không có",
                    manager_review_issues=saved_metric.manager_review_issues or "không có",
                    unverified_count=saved_metric.unverified_count,
                    evidence_items=[json.dumps(e) for e in evidence_items],
                )
                return data, evidence_items

            data = MetricsDataSchema(
                messages_replied=messages_replied_count,
                slow_network_count=slow_network_count,
                slow_network_devices=devices_str,
                customers_tested=len(customers_tested_set),
                feedback_count=feedback_count,
                tickets_opened=tickets_opened,
                tickets_closed=tickets_closed,
                escalate_count=len(escalations),
                escalate_details=escalate_str,
                pending_cases_desc=pending_str,
                follow_up_count=follow_up_count,
                follow_up_desc=follow_up_desc,
                best_positive_feedback=best_feedback,
                manager_review_issues=manager_review_str,
                unverified_count=unverified_count,
                evidence_items=[json.dumps(e) for e in evidence_items],
            )
            return data, evidence_items

    @classmethod
    def save_shift_metrics(cls, date_str: str, shift_num: int, metrics: MetricsDataSchema, is_manual_edit: bool = False) -> None:
        """Persist or update calculated metrics in daily_metrics table."""
        with db_manager.get_session() as session:
            record = session.execute(
                select(DailyMetric).where(
                    and_(
                        DailyMetric.date_str == date_str,
                        DailyMetric.shift_num == shift_num,
                    )
                )
            ).scalar_one_or_none()

            if not record:
                record = DailyMetric(date_str=date_str, shift_num=shift_num)
                session.add(record)

            record.messages_replied = metrics.messages_replied
            record.slow_network_count = metrics.slow_network_count
            record.slow_network_devices = metrics.slow_network_devices
            record.customers_tested = metrics.customers_tested
            record.feedback_count = metrics.feedback_count
            record.tickets_opened = metrics.tickets_opened
            record.tickets_closed = metrics.tickets_closed
            record.escalate_count = metrics.escalate_count
            record.escalate_details = metrics.escalate_details
            record.pending_cases_desc = metrics.pending_cases_desc
            record.follow_up_count = metrics.follow_up_count
            record.follow_up_desc = metrics.follow_up_desc
            record.best_positive_feedback = metrics.best_positive_feedback
            record.manager_review_issues = metrics.manager_review_issues
            record.unverified_count = metrics.unverified_count
            record.is_user_edited = is_manual_edit
            session.commit()
