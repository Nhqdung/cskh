"""
Report Generation and Formatting Service.
Generates the exact specified CSKH shift report template.
Validates formatting constraints, checklist rendering, and PII elimination.
"""

import os
from pathlib import Path
from typing import Optional, List
from sqlalchemy import select

from database.connection import db_manager
from models.orm import ShiftReport
from schemas.shift_schema import ChecklistStatus, ChecklistItemSchema, ChecklistItemKey
from schemas.report_schema import ShiftReportPayload, MetricsDataSchema
from services.security_service import SecurityService


class ReportService:
    """Builds and manages standardized CSKH reports."""

    @classmethod
    def generate_report_text(cls, payload: ShiftReportPayload) -> str:
        """Formats the exact report string adhering strictly to prompt template requirements.
        
        Ca 1/2 standard layout, Ca 3 includes the extra checklist item and 'TỔNG KẾT NGÀY'.
        """
        # Ensure employee name is PII-safe (no phone or token)
        emp_name = payload.employee_name.strip() or "Nhân viên CSKH"

        lines: List[str] = []

        # Header
        lines.append(f"[RP-CSKH] {payload.date_str} · Ca {payload.shift_num} · {emp_name}")
        lines.append("")

        # CHECKLIST
        lines.append("CHECKLIST")
        for item in payload.checklists:
            # Shift 3 specific item should only appear in Shift 3
            if item.item_key == ChecklistItemKey.CLOSE_UNANSWERED_TICKETS_SHIFT3 and payload.shift_num != 3:
                continue

            if item.status == ChecklistStatus.COMPLETED:
                lines.append(f"✅ {item.title}")
            elif item.status == ChecklistStatus.INCOMPLETE:
                reason = item.reason.strip() if item.reason else "Chưa hoàn tất"
                lines.append(f"❌ {item.title} – {reason}")
            elif item.status == ChecklistStatus.NOT_APPLICABLE:
                lines.append(f"⚪ {item.title} (K/A)")
            else: # NOT_CHECKED
                lines.append(f"⚠️ {item.title} (Chưa kiểm tra)")

        lines.append("")

        # SỐ LIỆU
        m = payload.metrics
        lines.append("SỐ LIỆU")
        lines.append(f"Tin nhắn đã reply: {int(m.messages_replied)}")
        
        slow_dev = m.slow_network_devices.strip() if m.slow_network_devices and m.slow_network_devices.strip() else "không có"
        lines.append(f"Báo cáo mạng chậm: {int(m.slow_network_count)} – máy: {slow_dev}")
        
        lines.append(f"Khách test máy: {int(m.customers_tested)} | Feedback nhận được: {int(m.feedback_count)}")
        lines.append(f"Ticket mở: {int(m.tickets_opened)} | Đóng: {int(m.tickets_closed)}")
        
        esc_det = m.escalate_details.strip() if m.escalate_details and m.escalate_details.strip() else "không có"
        lines.append(f"Escalate: {int(m.escalate_count)} – {esc_det}")
        lines.append("")

        # BÀN GIAO CA SAU
        pending_desc = m.pending_cases_desc.strip() if m.pending_cases_desc and m.pending_cases_desc.strip() else "không có"
        follow_up_desc = m.follow_up_desc.strip() if m.follow_up_desc and m.follow_up_desc.strip() else "không có"
        
        lines.append("BÀN GIAO CA SAU")
        lines.append(f"Case pending: {pending_desc}")
        lines.append(f"Khách cần follow up: {int(m.follow_up_count)} – {follow_up_desc}")

        # TỔNG KẾT NGÀY (Only for Ca 3)
        if payload.shift_num == 3:
            lines.append("")
            lines.append("TỔNG KẾT NGÀY")
            best_fb = m.best_positive_feedback.strip() if m.best_positive_feedback and m.best_positive_feedback.strip() else "không có"
            mgr_issues = m.manager_review_issues.strip() if m.manager_review_issues and m.manager_review_issues.strip() else "không có"
            lines.append(f"Feedback tích cực nhất: {best_fb}")
            lines.append(f"Vấn đề cần anh Tùng xem: {mgr_issues}")

        raw_report = "\n".join(lines)
        
        # Security sanitization pass: double-check that no phone numbers or customer usernames leaked
        cleaned_report = SecurityService.sanitize_text(raw_report)
        return cleaned_report

    @classmethod
    def save_report(cls, date_str: str, shift_num: int, employee_name: str, content: str) -> ShiftReport:
        """Saves generated report to database history."""
        with db_manager.get_session() as session:
            report = session.execute(
                select(ShiftReport).where(
                    ShiftReport.date_str == date_str,
                    ShiftReport.shift_num == shift_num,
                )
            ).scalar_one_or_none()

            if not report:
                report = ShiftReport(
                    date_str=date_str,
                    shift_num=shift_num,
                    employee_name=employee_name,
                    report_content=content,
                    status="finalized",
                )
                session.add(report)
            else:
                report.employee_name = employee_name
                report.report_content = content
                report.status = "finalized"
            session.commit()
            return report

    @classmethod
    def export_to_file(cls, content: str, file_path: Path) -> Path:
        """Export report text to a .txt file."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return file_path
