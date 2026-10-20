"""
Unit tests for ReportService.
Verifies strict adherence to report templates for Ca 1, 2, and 3,
checklist rendering rules, and PII suppression.
"""

from schemas.shift_schema import ChecklistItemSchema, ChecklistItemKey, ChecklistStatus
from schemas.report_schema import MetricsDataSchema, ShiftReportPayload
from services.report_service import ReportService


def test_standard_report_ca_1_structure():
    checklists = [
        ChecklistItemSchema(item_key=ChecklistItemKey.CLEAN_BACKLOG, title="Dọn tồn đọng / đọc bàn giao ca trước", status=ChecklistStatus.COMPLETED),
        ChecklistItemSchema(item_key=ChecklistItemKey.CHECK_PENDING_12H, title="Check ticket pending, đóng nếu quá 12h", status=ChecklistStatus.COMPLETED),
        ChecklistItemSchema(item_key=ChecklistItemKey.REPLY_SLA_10M, title="Reply Discord + Fanpage SLA < 10 phút", status=ChecklistStatus.COMPLETED),
        ChecklistItemSchema(item_key=ChecklistItemKey.REPLY_ALL_FB_COMMENTS, title="Reply hết comment Fanpage", status=ChecklistStatus.COMPLETED),
        ChecklistItemSchema(item_key=ChecklistItemKey.REPLY_7_VIDEOS_TIKTOK_YT, title="Reply comment 7 video TikTok/YT", status=ChecklistStatus.INCOMPLETE, reason="Chưa đăng video"),
        ChecklistItemSchema(item_key=ChecklistItemKey.ASK_FEEDBACK_POST_TEST, title="Xin feedback sau test máy", status=ChecklistStatus.COMPLETED),
    ]

    metrics = MetricsDataSchema(
        messages_replied=45,
        slow_network_count=1,
        slow_network_devices="PC-04",
        customers_tested=3,
        feedback_count=2,
        tickets_opened=2,
        tickets_closed=2,
        escalate_count=0,
        escalate_details="không có",
        pending_cases_desc="không có",
        follow_up_count=0,
        follow_up_desc="không có",
    )

    payload = ShiftReportPayload(
        date_str="2026-10-20",
        shift_num=1,
        employee_name="Nguyễn Văn A",
        checklists=checklists,
        metrics=metrics,
    )

    report = ReportService.generate_report_text(payload)

    # 1. Check Header
    assert "[RP-CSKH] 2026-10-20 · Ca 1 · Nguyễn Văn A" in report

    # 2. Check Incomplete Checklist formatting
    assert "❌ Reply comment 7 video TikTok/YT – Chưa đăng video" in report

    # 3. Check Exact Numbers
    assert "Tin nhắn đã reply: 45" in report
    assert "Báo cáo mạng chậm: 1 – máy: PC-04" in report
    assert "Khách test máy: 3 | Feedback nhận được: 2" in report
    assert "Ticket mở: 2 | Đóng: 2" in report
    assert "Escalate: 0 – không có" in report

    # 4. Check Handover
    assert "Case pending: không có" in report
    assert "Khách cần follow up: 0 – không có" in report

    # 5. Ca 1 must NOT contain TỔNG KẾT NGÀY
    assert "TỔNG KẾT NGÀY" not in report


def test_shift_3_report_includes_daily_summary():
    checklists = [
        ChecklistItemSchema(item_key=ChecklistItemKey.CLEAN_BACKLOG, title="Dọn tồn đọng / đọc bàn giao ca trước", status=ChecklistStatus.COMPLETED),
        ChecklistItemSchema(item_key=ChecklistItemKey.CHECK_PENDING_12H, title="Check ticket pending, đóng nếu quá 12h", status=ChecklistStatus.COMPLETED),
        ChecklistItemSchema(item_key=ChecklistItemKey.REPLY_SLA_10M, title="Reply Discord + Fanpage SLA < 10 phút", status=ChecklistStatus.COMPLETED),
        ChecklistItemSchema(item_key=ChecklistItemKey.REPLY_ALL_FB_COMMENTS, title="Reply hết comment Fanpage", status=ChecklistStatus.COMPLETED),
        ChecklistItemSchema(item_key=ChecklistItemKey.REPLY_7_VIDEOS_TIKTOK_YT, title="Reply comment 7 video TikTok/YT", status=ChecklistStatus.NOT_APPLICABLE),
        ChecklistItemSchema(item_key=ChecklistItemKey.ASK_FEEDBACK_POST_TEST, title="Xin feedback sau test máy", status=ChecklistStatus.COMPLETED),
        ChecklistItemSchema(item_key=ChecklistItemKey.CLOSE_UNANSWERED_TICKETS_SHIFT3, title="Đóng toàn bộ ticket chưa phản hồi trong ngày", status=ChecklistStatus.COMPLETED),
    ]

    metrics = MetricsDataSchema(
        messages_replied=12,
        slow_network_count=0,
        slow_network_devices="không có",
        customers_tested=1,
        feedback_count=1,
        tickets_opened=0,
        tickets_closed=1,
        escalate_count=0,
        escalate_details="không có",
        pending_cases_desc="không có",
        follow_up_count=0,
        follow_up_desc="không có",
        best_positive_feedback="Khách khen server đêm chạy rất êm",
        manager_review_issues="Kiểm tra lại đường truyền FPT",
    )

    payload = ShiftReportPayload(
        date_str="2026-10-20",
        shift_num=3,
        employee_name="Nguyễn Văn A",
        checklists=checklists,
        metrics=metrics,
    )

    report = ReportService.generate_report_text(payload)

    # Must contain extra checklist item
    assert "✅ Đóng toàn bộ ticket chưa phản hồi trong ngày" in report

    # Must contain TỔNG KẾT NGÀY
    assert "TỔNG KẾT NGÀY" in report
    assert "Feedback tích cực nhất: Khách khen server đêm chạy rất êm" in report
    assert "Vấn đề cần anh Tùng xem: Kiểm tra lại đường truyền FPT" in report


def test_pii_sanitized_in_report():
    checklists = [
        ChecklistItemSchema(item_key=ChecklistItemKey.CLEAN_BACKLOG, title="Dọn tồn đọng / đọc bàn giao ca trước", status=ChecklistStatus.COMPLETED),
    ]

    metrics = MetricsDataSchema(
        messages_replied=5,
        pending_cases_desc="Khách gọi 0987654321 đòi hoàn tiền", # Phone number in handover note!
    )

    payload = ShiftReportPayload(
        date_str="2026-10-20",
        shift_num=1,
        employee_name="Nguyễn Văn A",
        checklists=checklists,
        metrics=metrics,
    )

    report = ReportService.generate_report_text(payload)
    # Phone number must be redacted
    assert "0987654321" not in report
    assert "[SỐ ĐIỆN THOẠI ĐÃ ẨN]" in report
