"""
Report Generator and Preview Widget.
Adheres strictly to Section 5.9 and Section 6:
- Exact template layout preservation (Ca 1/2 vs Ca 3).
- Manual editing and verification of all metrics and handover fields.
- Evidence viewer for audits.
- Copy to clipboard & export to .txt.
- Local history persistence (NEVER automatically sends out).
"""

import json
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QGroupBox, QLineEdit, QSpinBox, QTextEdit,
    QPlainTextEdit, QDateEdit, QComboBox, QMessageBox, QFileDialog,
    QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QSplitter
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QGuiApplication

from schemas.shift_schema import ChecklistItemSchema
from schemas.report_schema import MetricsDataSchema, ShiftReportPayload
from services.shift_service import ShiftService
from services.metrics_service import MetricsService
from services.report_service import ReportService
from services.security_service import SecurityService


class EvidenceDialog(QDialog):
    """Pop-up modal displaying evidence links and message IDs for metrics audit."""

    def __init__(self, evidence_items: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bằng chứng đối chiếu số liệu (Evidence Audit)")
        self.resize(750, 400)
        self.setStyleSheet("background-color: #1e1e2e; color: #cdd6f4;")

        layout = QVBoxLayout(self)
        lbl_info = QLabel("Danh sách tin nhắn và sự kiện làm bằng chứng cho các chỉ số:")
        lbl_info.setStyleSheet("font-weight: bold; color: #89b4fa;")
        layout.addWidget(lbl_info)

        table = QTableWidget(len(evidence_items), 4)
        table.setHorizontalHeaderLabels(["Loại chỉ số", "Message ID / Chi tiết", "Snippet nội dung (Đã ẩn PII)", "Ghi chú"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for row, item in enumerate(evidence_items):
            if isinstance(item, str):
                try:
                    item = json.loads(item)
                except Exception:
                    item = {"type": "Info", "snippet": item}

            table.setItem(row, 0, QTableWidgetItem(str(item.get("type", "N/A"))))
            table.setItem(row, 1, QTableWidgetItem(str(item.get("message_id") or item.get("device") or item.get("owner") or "")))
            table.setItem(row, 2, QTableWidgetItem(str(item.get("snippet", ""))))
            table.setItem(row, 3, QTableWidgetItem(str(item.get("reason", ""))))

        layout.addWidget(table)

        btn_close = QPushButton("Đóng")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)


class ReportWidget(QWidget):
    """5.9 Report Generator screen with exact template preview and editing."""

    def __init__(self, checklist_widget=None, parent=None):
        super().__init__(parent)
        self.checklist_widget = checklist_widget
        self.current_evidence = []
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # Splitter: Left panel is Form/Editing, Right panel is Live Preview
        splitter = QSplitter(Qt.Horizontal)

        # ----------------- LEFT PANEL: CONTROLS & EDIT FIELDS -----------------
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(10)

        # Selection Bar (Date, Shift, Employee Name)
        meta_group = QGroupBox("THIẾT LẬP BÁO CÁO")
        meta_layout = QGridLayout(meta_group)

        meta_layout.addWidget(QLabel("Ngày:"), 0, 0)
        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDate(QDate.currentDate())
        self.date_picker.dateChanged.connect(self.on_date_or_shift_changed)
        meta_layout.addWidget(self.date_picker, 0, 1)

        meta_layout.addWidget(QLabel("Ca:"), 0, 2)
        self.combo_shift = QComboBox()
        self.combo_shift.addItems(["Ca 1 (07:00 - 15:00)", "Ca 2 (15:00 - 23:00)", "Ca 3 (23:00 - 07:00)"])
        self.combo_shift.currentIndexChanged.connect(self.on_date_or_shift_changed)
        meta_layout.addWidget(self.combo_shift, 0, 3)

        meta_layout.addWidget(QLabel("Tên nhân viên:"), 1, 0)
        default_emp = SecurityService.get_credential("EMPLOYEE_NAME", "Nguyễn Văn A")
        self.txt_emp_name = QLineEdit(default_emp)
        self.txt_emp_name.textChanged.connect(self.generate_preview)
        meta_layout.addWidget(self.txt_emp_name, 1, 1, 1, 3)

        left_layout.addWidget(meta_group)

        # Editable Metrics Fields
        metric_group = QGroupBox("CHỈNH SỬA SỐ LIỆU BÁO CÁO")
        metric_layout = QGridLayout(metric_group)
        metric_layout.setSpacing(8)

        # Tin nhắn đã reply
        metric_layout.addWidget(QLabel("Tin nhắn đã reply:"), 0, 0)
        self.spin_replied = QSpinBox()
        self.spin_replied.setRange(0, 99999)
        self.spin_replied.valueChanged.connect(self.generate_preview)
        metric_layout.addWidget(self.spin_replied, 0, 1)

        # Báo cáo mạng chậm & máy
        metric_layout.addWidget(QLabel("Báo cáo mạng chậm:"), 1, 0)
        self.spin_slow_net = QSpinBox()
        self.spin_slow_net.setRange(0, 9999)
        self.spin_slow_net.valueChanged.connect(self.generate_preview)
        metric_layout.addWidget(self.spin_slow_net, 1, 1)

        metric_layout.addWidget(QLabel("Tên máy mạng chậm:"), 1, 2)
        self.txt_slow_devices = QLineEdit("không có")
        self.txt_slow_devices.textChanged.connect(self.generate_preview)
        metric_layout.addWidget(self.txt_slow_devices, 1, 3)

        # Khách test máy & Feedback
        metric_layout.addWidget(QLabel("Khách test máy:"), 2, 0)
        self.spin_tested = QSpinBox()
        self.spin_tested.setRange(0, 9999)
        self.spin_tested.valueChanged.connect(self.generate_preview)
        metric_layout.addWidget(self.spin_tested, 2, 1)

        metric_layout.addWidget(QLabel("Feedback nhận được:"), 2, 2)
        self.spin_feedback = QSpinBox()
        self.spin_feedback.setRange(0, 9999)
        self.spin_feedback.valueChanged.connect(self.generate_preview)
        metric_layout.addWidget(self.spin_feedback, 2, 3)

        # Ticket mở & đóng
        metric_layout.addWidget(QLabel("Ticket mở:"), 3, 0)
        self.spin_ticket_open = QSpinBox()
        self.spin_ticket_open.setRange(0, 9999)
        self.spin_ticket_open.valueChanged.connect(self.generate_preview)
        metric_layout.addWidget(self.spin_ticket_open, 3, 1)

        metric_layout.addWidget(QLabel("Ticket đóng:"), 3, 2)
        self.spin_ticket_close = QSpinBox()
        self.spin_ticket_close.setRange(0, 9999)
        self.spin_ticket_close.valueChanged.connect(self.generate_preview)
        metric_layout.addWidget(self.spin_ticket_close, 3, 3)

        # Escalate & Details
        metric_layout.addWidget(QLabel("Escalate:"), 4, 0)
        self.spin_escalate = QSpinBox()
        self.spin_escalate.setRange(0, 9999)
        self.spin_escalate.valueChanged.connect(self.generate_preview)
        metric_layout.addWidget(self.spin_escalate, 4, 1)

        metric_layout.addWidget(QLabel("Chi tiết Escalate:"), 4, 2)
        self.txt_escalate_det = QLineEdit("không có")
        self.txt_escalate_det.setPlaceholderText("Dương/Tùng: lý do ngắn | không có")
        self.txt_escalate_det.textChanged.connect(self.generate_preview)
        metric_layout.addWidget(self.txt_escalate_det, 4, 3)

        left_layout.addWidget(metric_group)

        # Handover Fields
        handover_group = QGroupBox("BÀN GIAO CA SAU")
        handover_layout = QGridLayout(handover_group)

        handover_layout.addWidget(QLabel("Case pending:"), 0, 0)
        self.txt_pending = QLineEdit("không có")
        self.txt_pending.textChanged.connect(self.generate_preview)
        handover_layout.addWidget(self.txt_pending, 0, 1, 1, 3)

        handover_layout.addWidget(QLabel("Khách cần follow up (SL):"), 1, 0)
        self.spin_follow_up = QSpinBox()
        self.spin_follow_up.setRange(0, 9999)
        self.spin_follow_up.valueChanged.connect(self.generate_preview)
        handover_layout.addWidget(self.spin_follow_up, 1, 1)

        handover_layout.addWidget(QLabel("Việc cần làm:"), 1, 2)
        self.txt_follow_up_action = QLineEdit("không có")
        self.txt_follow_up_action.textChanged.connect(self.generate_preview)
        handover_layout.addWidget(self.txt_follow_up_action, 1, 3)

        left_layout.addWidget(handover_group)

        # Shift 3 specific fields
        self.shift3_group = QGroupBox("TỔNG KẾT NGÀY (CHỈ DÀNH CHO CA 3)")
        shift3_layout = QGridLayout(self.shift3_group)

        shift3_layout.addWidget(QLabel("Feedback tích cực nhất:"), 0, 0)
        self.txt_best_feedback = QLineEdit("không có")
        self.txt_best_feedback.textChanged.connect(self.generate_preview)
        shift3_layout.addWidget(self.txt_best_feedback, 0, 1)

        shift3_layout.addWidget(QLabel("Vấn đề cần anh Tùng xem:"), 1, 0)
        self.txt_manager_issues = QLineEdit("không có")
        self.txt_manager_issues.textChanged.connect(self.generate_preview)
        shift3_layout.addWidget(self.txt_manager_issues, 1, 1)

        self.shift3_group.setVisible(False)
        left_layout.addWidget(self.shift3_group)

        # Evidence Button & Recalculate
        action_row = QHBoxLayout()
        self.btn_view_evidence = QPushButton("🔍 Xem bằng chứng số liệu")
        self.btn_view_evidence.setObjectName("btn_secondary")
        self.btn_view_evidence.clicked.connect(self.show_evidence)
        action_row.addWidget(self.btn_view_evidence)

        self.btn_recalc = QPushButton("🔄 Tải lại số liệu gốc")
        self.btn_recalc.setObjectName("btn_secondary")
        self.btn_recalc.clicked.connect(self.load_shift_metrics)
        action_row.addWidget(self.btn_recalc)

        left_layout.addLayout(action_row)
        left_layout.addStretch()

        splitter.addWidget(left_widget)

        # ----------------- RIGHT PANEL: EXACT PREVIEW & EXPORT -----------------
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(10)

        lbl_preview_title = QLabel("BẢN XEM TRƯỚC BÁO CÁO (ĐÚNG MẪU NỘI BỘ)")
        lbl_preview_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #89b4fa;")
        right_layout.addWidget(lbl_preview_title)

        self.preview_text = QPlainTextEdit()
        self.preview_text.setReadOnly(True)
        # Use clean monospace font
        mono_font = QFont("Consolas" if "Consolas" in QFont().families() else "Monospace", 10)
        self.preview_text.setFont(mono_font)
        self.preview_text.setStyleSheet("""
            QPlainTextEdit {
                background-color: #11111b;
                color: #cdd6f4;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 12px;
                line-height: 1.4;
            }
        """)
        right_layout.addWidget(self.preview_text)

        # Export & Copy Buttons
        btn_layout = QHBoxLayout()
        self.btn_copy = QPushButton("📋 Sao chép báo cáo")
        self.btn_copy.setStyleSheet("background-color: #a6e3a1; color: #11111b; font-weight: bold;")
        self.btn_copy.clicked.connect(self.copy_to_clipboard)
        btn_layout.addWidget(self.btn_copy)

        self.btn_export = QPushButton("💾 Xuất file .txt")
        self.btn_export.clicked.connect(self.export_txt)
        btn_layout.addWidget(self.btn_export)

        right_layout.addLayout(btn_layout)

        lbl_notice = QLabel("⚠️ Báo cáo không tự động gửi ra ngoài. Bạn hãy xem lại, sao chép và tự đăng lên kênh cho phép.")
        lbl_notice.setStyleSheet("color: #fab387; font-size: 11px;")
        right_layout.addWidget(lbl_notice)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 5)

        main_layout.addWidget(splitter)

        # Initial load
        self.on_date_or_shift_changed()

    def get_selected_date_str(self) -> str:
        return self.date_picker.date().toString("yyyy-MM-dd")

    def get_selected_shift_num(self) -> int:
        return self.combo_shift.currentIndex() + 1

    def on_date_or_shift_changed(self):
        shift_num = self.get_selected_shift_num()
        self.shift3_group.setVisible(shift_num == 3)
        
        # Sync checklist widget if available
        if self.checklist_widget:
            self.checklist_widget.load_checklist(self.get_selected_date_str(), shift_num)

        self.load_shift_metrics()

    def load_shift_metrics(self):
        """Fetch metrics from database and populate edit fields."""
        date_str = self.get_selected_date_str()
        shift_num = self.get_selected_shift_num()

        metrics, evidence = MetricsService.calculate_shift_metrics(date_str, shift_num)
        self.current_evidence = evidence

        # Populate form
        self.spin_replied.setValue(metrics.messages_replied)
        self.spin_slow_net.setValue(metrics.slow_network_count)
        self.txt_slow_devices.setText(metrics.slow_network_devices)
        self.spin_tested.setValue(metrics.customers_tested)
        self.spin_feedback.setValue(metrics.feedback_count)
        self.spin_ticket_open.setValue(metrics.tickets_opened)
        self.spin_ticket_close.setValue(metrics.tickets_closed)
        self.spin_escalate.setValue(metrics.escalate_count)
        self.txt_escalate_det.setText(metrics.escalate_details)
        self.txt_pending.setText(metrics.pending_cases_desc)
        self.spin_follow_up.setValue(metrics.follow_up_count)
        self.txt_follow_up_action.setText(metrics.follow_up_desc)
        self.txt_best_feedback.setText(metrics.best_positive_feedback or "không có")
        self.txt_manager_issues.setText(metrics.manager_review_issues or "không có")

        self.generate_preview()

    def generate_preview(self):
        """Builds formatted report and updates preview text box."""
        date_str = self.get_selected_date_str()
        shift_num = self.get_selected_shift_num()
        emp_name = self.txt_emp_name.text().strip() or "Nhân viên CSKH"

        # Checklists
        checklists = self.checklist_widget.get_items() if self.checklist_widget else ShiftService.get_or_create_checklist(date_str, shift_num)

        metrics = MetricsDataSchema(
            messages_replied=self.spin_replied.value(),
            slow_network_count=self.spin_slow_net.value(),
            slow_network_devices=self.txt_slow_devices.text().strip() or "không có",
            customers_tested=self.spin_tested.value(),
            feedback_count=self.spin_feedback.value(),
            tickets_opened=self.spin_ticket_open.value(),
            tickets_closed=self.spin_ticket_close.value(),
            escalate_count=self.spin_escalate.value(),
            escalate_details=self.txt_escalate_det.text().strip() or "không có",
            pending_cases_desc=self.txt_pending.text().strip() or "không có",
            follow_up_count=self.spin_follow_up.value(),
            follow_up_desc=self.txt_follow_up_action.text().strip() or "không có",
            best_positive_feedback=self.txt_best_feedback.text().strip() or "không có",
            manager_review_issues=self.txt_manager_issues.text().strip() or "không có",
        )

        payload = ShiftReportPayload(
            date_str=date_str,
            shift_num=shift_num,
            employee_name=emp_name,
            checklists=checklists,
            metrics=metrics,
        )

        report_content = ReportService.generate_report_text(payload)
        self.preview_text.setPlainText(report_content)

    def show_evidence(self):
        """Displays modal with evidence records."""
        dialog = EvidenceDialog(self.current_evidence, self)
        dialog.exec()

    def copy_to_clipboard(self):
        """Copies report text to system clipboard and saves report to DB history."""
        content = self.preview_text.toPlainText()
        if not content:
            return

        clipboard = QGuiApplication.clipboard()
        clipboard.setText(content)

        # Save to DB history
        ReportService.save_report(
            self.get_selected_date_str(),
            self.get_selected_shift_num(),
            self.txt_emp_name.text().strip() or "Nhân viên CSKH",
            content,
        )

        QMessageBox.information(
            self,
            "Đã sao chép",
            "Nội dung báo cáo đã được sao chép vào bộ nhớ đệm (Clipboard) và lưu vào lịch sử báo cáo!"
        )

    def export_txt(self):
        """Exports preview text to a .txt file."""
        content = self.preview_text.toPlainText()
        if not content:
            return

        default_filename = f"BaoCao_CSKH_{self.get_selected_date_str()}_Ca{self.get_selected_shift_num()}.txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu báo cáo CSKH",
            default_filename,
            "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            ReportService.export_to_file(content, Path(file_path))
            QMessageBox.information(self, "Đã xuất file", f"Đã lưu báo cáo thành công vào:\n{file_path}")
