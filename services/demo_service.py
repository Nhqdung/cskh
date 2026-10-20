"""
Demo Mode and Simulation Service.
Generates realistic simulated CSKH data for testing and demonstration
without requiring actual Discord, Meta, or Gemini credentials.
Includes:
- Discord customer tickets & staff replies.
- Meta Page messages with 'unverified_agent' status for manual review demo.
- Slow network reports with device names (PC-04, May 12).
- Customers who tested vs customers who will test later.
- Escalations to Dương and Tùng.
- Distinct checklists for Ca 1, Ca 2, and Ca 3.
- Clearly flags records as DEMO data.
"""

import json
import datetime
from typing import Dict, Any, List
from sqlalchemy import select, delete

from database.connection import db_manager
from models.orm import Message, Conversation, Ticket, AIClassification, ShiftChecklist, DailyMetric
from schemas.shift_schema import ChecklistStatus, ChecklistItemKey
from services.shift_service import ShiftService


class DemoService:
    """Manages generation and cleanup of realistic demo datasets."""

    @classmethod
    def populate_demo_data(cls, date_str: str) -> Dict[str, Any]:
        """Populates comprehensive demo scenario for the given date (YYYY-MM-DD)."""
        counts = {"messages": 0, "tickets": 0, "classifications": 0}

        # Clear existing demo data for this date first
        cls.clear_demo_data(date_str)

        # Base shift windows
        w1 = ShiftService.get_shift_window(date_str, 1) # 07:00 - 15:00
        w2 = ShiftService.get_shift_window(date_str, 2) # 15:00 - 23:00
        w3 = ShiftService.get_shift_window(date_str, 3) # 23:00 - 07:00 next day

        with db_manager.get_session() as session:
            # -------------------------------------------------------------
            # CA 1 DEMO SCENARIO
            # -------------------------------------------------------------
            # Conv 1: Slow network report on PC-04
            c1_time = w1.start_utc + datetime.timedelta(hours=1, minutes=15)
            conv1 = Conversation(
                platform="discord",
                platform_conversation_id="demo_thread_ticket_101",
                title="Ticket #101 - Khách báo mạng chập chờn",
                status="closed",
                customer_identifier="Khach_8812",
                first_activity_utc=c1_time,
                last_activity_utc=c1_time + datetime.timedelta(minutes=5),
            )
            session.add(conv1)
            session.flush()

            msg1_cust = Message(
                platform="discord",
                platform_message_id="demo_msg_001",
                platform_conversation_id=conv1.platform_conversation_id,
                channel_id="ch_tickets",
                author_id="cust_8812",
                author_name="Khach_8812",
                author_is_employee=False,
                is_bot=False,
                content="[DEMO] Ad ơi em đang dùng máy PC-04 mà mạng chậm quá, vào web giật lag liên tục.",
                timestamp_utc=c1_time,
                timestamp_local=ShiftService.utc_to_local(c1_time),
                verification_status="unverified",
                shift_date=date_str,
                shift_num=1,
                conversation_id=conv1.id,
            )
            session.add(msg1_cust)

            msg1_emp = Message(
                platform="discord",
                platform_message_id="demo_msg_002",
                platform_conversation_id=conv1.platform_conversation_id,
                channel_id="ch_tickets",
                author_id="emp_me",
                author_name="Nguyễn Văn A",
                author_is_employee=True,
                is_bot=False,
                content="[DEMO] Dạ chào bạn, mình đã kiểm tra và reset line mạng cho máy PC-04 rồi ạ, bạn test lại giúp mình nhé.",
                timestamp_utc=c1_time + datetime.timedelta(minutes=3),
                timestamp_local=ShiftService.utc_to_local(c1_time + datetime.timedelta(minutes=3)),
                reference_message_id="demo_msg_001",
                is_reply_to_customer=True,
                verification_status="verified",
                shift_date=date_str,
                shift_num=1,
                conversation_id=conv1.id,
            )
            session.add(msg1_emp)
            session.flush()

            ai_c1 = AIClassification(
                message_id=msg1_emp.id,
                conversation_id=conv1.id,
                slow_network_report=True,
                device_name="PC-04",
                device_tested=False, # Just reset, not confirmed tested yet
                feedback_received=False,
                positive_feedback=False,
                ticket_opened=True,
                ticket_closed=True,
                escalated=False,
                evidence_message_ids=json.dumps(["demo_msg_001", "demo_msg_002"]),
                confidence=0.95,
            )
            session.add(ai_c1)

            ticket1 = Ticket(
                platform="discord",
                platform_ticket_id="ticket_101",
                channel_id="ch_tickets",
                title="Ticket #101 - PC-04",
                status="closed",
                opened_at_utc=c1_time,
                closed_at_utc=c1_time + datetime.timedelta(minutes=5),
                closed_by_employee=True,
                shift_date=date_str,
                shift_num=1,
            )
            session.add(ticket1)

            # Conv 2: Customer tested and positive feedback
            c2_time = w1.start_utc + datetime.timedelta(hours=2, minutes=30)
            conv2 = Conversation(
                platform="discord",
                platform_conversation_id="demo_thread_ticket_102",
                title="Ticket #102 - Test máy",
                status="closed",
                customer_identifier="Khach_3345",
                first_activity_utc=c2_time,
                last_activity_utc=c2_time + datetime.timedelta(minutes=4),
            )
            session.add(conv2)
            session.flush()

            msg2_cust = Message(
                platform="discord",
                platform_message_id="demo_msg_003",
                platform_conversation_id=conv2.platform_conversation_id,
                channel_id="ch_tickets",
                author_id="cust_3345",
                author_name="Khach_3345",
                author_is_employee=False,
                is_bot=False,
                content="[DEMO] Mình vừa vào test máy May 12 xong rồi, mạng mượt và chạy render rất ngon nhé shop!",
                timestamp_utc=c2_time,
                timestamp_local=ShiftService.utc_to_local(c2_time),
                verification_status="unverified",
                shift_date=date_str,
                shift_num=1,
                conversation_id=conv2.id,
            )
            session.add(msg2_cust)

            msg2_emp = Message(
                platform="discord",
                platform_message_id="demo_msg_004",
                platform_conversation_id=conv2.platform_conversation_id,
                channel_id="ch_tickets",
                author_id="emp_me",
                author_name="Nguyễn Văn A",
                author_is_employee=True,
                is_bot=False,
                content="[DEMO] Dạ cảm ơn anh đã phản hồi và ủng hộ dịch vụ bên em ạ!",
                timestamp_utc=c2_time + datetime.timedelta(minutes=2),
                timestamp_local=ShiftService.utc_to_local(c2_time + datetime.timedelta(minutes=2)),
                reference_message_id="demo_msg_003",
                is_reply_to_customer=True,
                verification_status="verified",
                shift_date=date_str,
                shift_num=1,
                conversation_id=conv2.id,
            )
            session.add(msg2_emp)
            session.flush()

            ai_c2 = AIClassification(
                message_id=msg2_emp.id,
                conversation_id=conv2.id,
                slow_network_report=False,
                device_name="May 12",
                device_tested=True, # Actually tested
                feedback_received=True,
                positive_feedback=True,
                ticket_opened=False,
                ticket_closed=True,
                escalated=False,
                evidence_message_ids=json.dumps(["demo_msg_003", "demo_msg_004"]),
                confidence=0.98,
            )
            session.add(ai_c2)

            # Conv 3: Meta Messenger with 'unverified_agent' (Page reply)
            c3_time = w1.start_utc + datetime.timedelta(hours=4)
            msg3_meta = Message(
                platform="meta_messenger",
                platform_message_id="demo_meta_001",
                platform_conversation_id="meta_conv_889",
                author_id="page_12345",
                author_name="Page Representative",
                author_is_employee=False,
                is_bot=False,
                content="[DEMO] Chào bạn, shop có chính sách dùng thử 2 tiếng miễn phí nhé ạ.",
                timestamp_utc=c3_time,
                timestamp_local=ShiftService.utc_to_local(c3_time),
                is_reply_to_customer=True,
                verification_status="unverified_agent", # Needs manual staff audit
                shift_date=date_str,
                shift_num=1,
            )
            session.add(msg3_meta)

            # -------------------------------------------------------------
            # CA 2 DEMO SCENARIO: Escalations & Pending Cases
            # -------------------------------------------------------------
            c4_time = w2.start_utc + datetime.timedelta(hours=1, minutes=30)
            conv4 = Conversation(
                platform="discord",
                platform_conversation_id="demo_thread_ticket_201",
                title="Ticket #201 - Lỗi card màn hình",
                status="pending",
                customer_identifier="Khach_7719",
                first_activity_utc=c4_time,
            )
            session.add(conv4)
            session.flush()

            msg4_emp = Message(
                platform="discord",
                platform_message_id="demo_msg_005",
                platform_conversation_id=conv4.platform_conversation_id,
                channel_id="ch_tickets",
                author_id="emp_me",
                author_name="Nguyễn Văn A",
                author_is_employee=True,
                is_bot=False,
                content="[DEMO] Case này bị lỗi driver GPU sâu, em đã escalate chuyển qua cho anh Tùng kiểm tra cấu hình phần cứng giúp khách.",
                timestamp_utc=c4_time,
                timestamp_local=ShiftService.utc_to_local(c4_time),
                is_reply_to_customer=True,
                verification_status="verified",
                shift_date=date_str,
                shift_num=2,
                conversation_id=conv4.id,
            )
            session.add(msg4_emp)
            session.flush()

            ai_c4 = AIClassification(
                message_id=msg4_emp.id,
                conversation_id=conv4.id,
                escalated=True,
                escalation_owner="Tùng",
                escalation_reason="Lỗi driver GPU sâu",
                needs_follow_up=True,
                follow_up_action="Kiểm tra lại sau khi anh Tùng fix driver",
                pending_case=True,
                pending_reason="Chờ kỹ thuật kiểm tra GPU",
                needs_manager_review=True,
                manager_review_desc="Lỗi phần cứng GPU máy trạm",
                evidence_message_ids=json.dumps(["demo_msg_005"]),
                confidence=0.96,
            )
            session.add(ai_c4)

            session.commit()

        # Ca 1 & Ca 2 Checklists
        ShiftService.update_checklist_item(date_str, 1, ChecklistItemKey.CLEAN_BACKLOG, ChecklistStatus.COMPLETED)
        ShiftService.update_checklist_item(date_str, 1, ChecklistItemKey.CHECK_PENDING_12H, ChecklistStatus.COMPLETED)
        ShiftService.update_checklist_item(date_str, 1, ChecklistItemKey.REPLY_SLA_10M, ChecklistStatus.COMPLETED)
        ShiftService.update_checklist_item(date_str, 1, ChecklistItemKey.REPLY_ALL_FB_COMMENTS, ChecklistStatus.COMPLETED)
        ShiftService.update_checklist_item(date_str, 1, ChecklistItemKey.REPLY_7_VIDEOS_TIKTOK_YT, ChecklistStatus.INCOMPLETE, "Kênh chưa đăng video mới hôm nay")
        ShiftService.update_checklist_item(date_str, 1, ChecklistItemKey.ASK_FEEDBACK_POST_TEST, ChecklistStatus.COMPLETED)

        # Ca 3 Checklist (includes extra item)
        ShiftService.update_checklist_item(date_str, 3, ChecklistItemKey.CLEAN_BACKLOG, ChecklistStatus.COMPLETED)
        ShiftService.update_checklist_item(date_str, 3, ChecklistItemKey.CHECK_PENDING_12H, ChecklistStatus.COMPLETED)
        ShiftService.update_checklist_item(date_str, 3, ChecklistItemKey.REPLY_SLA_10M, ChecklistStatus.COMPLETED)
        ShiftService.update_checklist_item(date_str, 3, ChecklistItemKey.REPLY_ALL_FB_COMMENTS, ChecklistStatus.COMPLETED)
        ShiftService.update_checklist_item(date_str, 3, ChecklistItemKey.REPLY_7_VIDEOS_TIKTOK_YT, ChecklistStatus.NOT_APPLICABLE)
        ShiftService.update_checklist_item(date_str, 3, ChecklistItemKey.ASK_FEEDBACK_POST_TEST, ChecklistStatus.COMPLETED)
        ShiftService.update_checklist_item(date_str, 3, ChecklistItemKey.CLOSE_UNANSWERED_TICKETS_SHIFT3, ChecklistStatus.COMPLETED)

        counts["messages"] = 5
        counts["tickets"] = 1
        counts["classifications"] = 3
        return counts

    @classmethod
    def clear_demo_data(cls, date_str: str) -> None:
        """Removes demo records for the given date across messages, conversations, tickets, and classifications."""
        with db_manager.get_session() as session:
            # 1. Fetch demo message IDs
            demo_msg_ids = session.execute(
                select(Message.id).where(
                    Message.shift_date == date_str,
                    Message.content.like("%[DEMO]%"),
                )
            ).scalars().all()

            if demo_msg_ids:
                session.execute(
                    delete(AIClassification).where(
                        AIClassification.message_id.in_(demo_msg_ids)
                    )
                )

            # 2. Delete any lingering classifications with demo evidence
            session.execute(
                delete(AIClassification).where(
                    AIClassification.evidence_message_ids.like("%demo_%")
                )
            )

            # 3. Delete demo messages
            session.execute(
                delete(Message).where(
                    Message.shift_date == date_str,
                    Message.content.like("%[DEMO]%"),
                )
            )

            # 4. Delete demo tickets
            session.execute(
                delete(Ticket).where(
                    Ticket.shift_date == date_str,
                    Ticket.platform_ticket_id.like("ticket_%"),
                )
            )

            # 5. Delete demo conversations
            session.execute(
                delete(Conversation).where(
                    Conversation.platform_conversation_id.like("demo_%")
                )
            )

            session.commit()
