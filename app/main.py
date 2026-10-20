"""
Application Entry Point for Personal CSKH Reporting Assistant.
Supports both Desktop GUI (PySide6) and Headless CLI modes.
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

from database.connection import db_manager
from services.security_service import SensitiveDataFilter, SecurityService
from services.shift_service import ShiftService
from services.metrics_service import MetricsService
from services.report_service import ReportService
from services.demo_service import DemoService
from schemas.report_schema import ShiftReportPayload


def setup_logging():
    """Sets up root logger with sensitive data scrubbing filter."""
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(SensitiveDataFilter())

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format=log_format,
        handlers=[handler],
    )


def run_cli_demo(date_str: str | None = None):
    """Generates demo data and prints reports for Ca 1, Ca 2, Ca 3 in CLI."""
    target_date = date_str or ShiftService.get_current_local_time().strftime("%Y-%m-%d")
    print(f"\n=======================================================")
    print(f" KHỞI TẠO DỮ LIỆU DEMO CHO NGÀY: {target_date}")
    print(f"=======================================================\n")

    res = DemoService.populate_demo_data(target_date)
    print(f"✅ Đã tạo {res['messages']} tin nhắn mô phỏng, {res['tickets']} ticket và {res['classifications']} phân loại AI.")

    emp_name = SecurityService.get_credential("EMPLOYEE_NAME", "Nguyễn Văn A")

    for shift_num in (1, 2, 3):
        print(f"\n-------------------------------------------------------")
        print(f" MẪU BÁO CÁO CA {shift_num} ({target_date})")
        print(f"-------------------------------------------------------\n")
        checklists = ShiftService.get_or_create_checklist(target_date, shift_num)
        metrics, _ = MetricsService.calculate_shift_metrics(target_date, shift_num)

        payload = ShiftReportPayload(
            date_str=target_date,
            shift_num=shift_num,
            employee_name=emp_name,
            checklists=checklists,
            metrics=metrics,
        )
        report_text = ReportService.generate_report_text(payload)
        print(report_text)


def run_gui():
    """Launches PySide6 desktop GUI."""
    from PySide6.QtWidgets import QApplication
    from app.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Personal CSKH Reporting Assistant")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


def main():
    setup_logging()
    db_manager.init_db()

    parser = argparse.ArgumentParser(description="Personal CSKH Reporting Assistant")
    parser.add_argument("--demo", action="store_true", help="Populate demo data and output sample reports")
    parser.add_argument("--date", type=str, default=None, help="Date in YYYY-MM-DD for demo or report generation")
    parser.add_argument("--cli", action="store_true", help="Run in headless CLI mode without opening GUI window")

    args = parser.parse_args()

    if args.demo:
        run_cli_demo(args.date)
        return

    # Check for GUI display availability
    has_display = bool(os.getenv("DISPLAY") or os.getenv("WAYLAND_DISPLAY") or sys.platform == "win32")
    if args.cli or not has_display:
        if not has_display:
            print("ℹ️ Không tìm thấy màn hình hiển thị (DISPLAY). Đang chạy ở chế độ CLI...")
        run_cli_demo(args.date)
    else:
        run_gui()


if __name__ == "__main__":
    main()
