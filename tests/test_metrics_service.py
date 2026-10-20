"""
Unit tests for independent metrics calculation service.
Verifies counting rules, anti-duplication, employee filtering, bot filtering,
and Meta unverified agent separation.
"""

import datetime
from zoneinfo import ZoneInfo
from models.orm import Message, Conversation, Ticket, AIClassification
from services.metrics_service import MetricsService
from services.shift_service import ShiftService, VN_TZ


def test_metrics_employee_only_and_bot_exclusion(test_db):
    date_str = "2026-10-20"
    shift_num = 1
    w1 = ShiftService.get_shift_window(date_str, shift_num)
    t_msg = w1.start_utc + datetime.timedelta(hours=2)

    with test_db.get_session() as session:
        # 1. Designated employee reply to customer (VERIFIED)
        session.add(
            Message(
                platform="discord",
                platform_message_id="msg_emp_01",
                author_id="1122334455",
                author_is_employee=True,
                is_bot=False,
                content="Chào bạn, mình hỗ trợ nhé.",
                timestamp_utc=t_msg,
                timestamp_local=ShiftService.utc_to_local(t_msg),
                is_reply_to_customer=True,
                verification_status="verified",
                shift_date=date_str,
                shift_num=shift_num,
            )
        )

        # 2. Designated employee general announcement (NOT a reply to customer)
        session.add(
            Message(
                platform="discord",
                platform_message_id="msg_emp_02",
                author_id="1122334455",
                author_is_employee=True,
                is_bot=False,
                content="Thông báo bảo trì chung trên kênh announcements.",
                timestamp_utc=t_msg + datetime.timedelta(minutes=5),
                timestamp_local=ShiftService.utc_to_local(t_msg + datetime.timedelta(minutes=5)),
                is_reply_to_customer=False,
                verification_status="verified",
                shift_date=date_str,
                shift_num=shift_num,
            )
        )

        # 3. Colleague message (different employee ID)
        session.add(
            Message(
                platform="discord",
                platform_message_id="msg_colleague_01",
                author_id="9999999999", # Colleague ID
                author_is_employee=False,
                is_bot=False,
                content="Tin nhắn của đồng nghiệp trực cùng ca.",
                timestamp_utc=t_msg + datetime.timedelta(minutes=10),
                timestamp_local=ShiftService.utc_to_local(t_msg + datetime.timedelta(minutes=10)),
                is_reply_to_customer=True,
                verification_status="unverified",
                shift_date=date_str,
                shift_num=shift_num,
            )
        )

        # 4. Bot / Webhook automated message
        session.add(
            Message(
                platform="discord",
                platform_message_id="msg_bot_01",
                author_id="bot_id_123",
                author_is_employee=True, # Even if someone mislabeled author_is_employee
                is_bot=True,             # is_bot MUST take precedence!
                content="Ticket opened automatically by Discord Bot.",
                timestamp_utc=t_msg + datetime.timedelta(minutes=15),
                timestamp_local=ShiftService.utc_to_local(t_msg + datetime.timedelta(minutes=15)),
                is_reply_to_customer=True,
                verification_status="verified",
                shift_date=date_str,
                shift_num=shift_num,
            )
        )

        # 5. Meta Page response with unverified agent
        session.add(
            Message(
                platform="meta_messenger",
                platform_message_id="meta_msg_unverified",
                author_id="page_id_xyz",
                author_is_employee=False,
                is_bot=False,
                content="Tin nhắn gửi từ Fanpage nhưng chưa xác minh nhân viên cụ thể.",
                timestamp_utc=t_msg + datetime.timedelta(minutes=20),
                timestamp_local=ShiftService.utc_to_local(t_msg + datetime.timedelta(minutes=20)),
                is_reply_to_customer=True,
                verification_status="unverified_agent", # MUST NOT be counted in verified replies
                shift_date=date_str,
                shift_num=shift_num,
            )
        )
        session.commit()

    # Calculate metrics
    metrics, evidence = MetricsService.calculate_shift_metrics(date_str, shift_num)

    # Tin nhắn đã reply: strictly ONLY msg_emp_01 (count = 1)
    assert metrics.messages_replied == 1

    # Unverified count includes the Meta unverified agent
    assert metrics.unverified_count >= 1


def test_metrics_slow_network_and_devices(test_db):
    date_str = "2026-10-20"
    shift_num = 1
    w1 = ShiftService.get_shift_window(date_str, shift_num)
    t_msg = w1.start_utc + datetime.timedelta(hours=1)

    with test_db.get_session() as session:
        m1 = Message(
            platform="discord",
            platform_message_id="msg_net_1",
            author_id="cust_1",
            content="Khách kêu lag máy PC-01",
            timestamp_utc=t_msg,
            timestamp_local=ShiftService.utc_to_local(t_msg),
            is_reply_to_customer=False,
            shift_date=date_str,
            shift_num=shift_num,
        )
        session.add(m1)
        session.flush()

        ai1 = AIClassification(
            message_id=m1.id,
            slow_network_report=True,
            device_name="PC-01",
        )
        session.add(ai1)

        m2 = Message(
            platform="discord",
            platform_message_id="msg_net_2",
            author_id="cust_2",
            content="Máy May 05 cũng chậm",
            timestamp_utc=t_msg + datetime.timedelta(minutes=5),
            timestamp_local=ShiftService.utc_to_local(t_msg + datetime.timedelta(minutes=5)),
            is_reply_to_customer=False,
            shift_date=date_str,
            shift_num=shift_num,
        )
        session.add(m2)
        session.flush()

        ai2 = AIClassification(
            message_id=m2.id,
            slow_network_report=True,
            device_name="May 05",
        )
        session.add(ai2)
        session.commit()

    metrics, _ = MetricsService.calculate_shift_metrics(date_str, shift_num)
    assert metrics.slow_network_count == 2
    assert "PC-01" in metrics.slow_network_devices
    assert "May 05" in metrics.slow_network_devices
