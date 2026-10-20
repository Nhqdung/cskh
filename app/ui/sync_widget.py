"""
Sync and Manual Data Audit Widget.
Displays synchronized messages for the active or selected shift.
Provides audit tools to verify or unverify agent messages (e.g. from Meta Page)
and trigger live or demo synchronizations.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QDateEdit, QComboBox, QMessageBox, QProgressBar
)
from PySide6.QtCore import Qt, QDate
from sqlalchemy import select, and_

from database.connection import db_manager
from models.orm import Message
from services.shift_service import ShiftService
from services.sync_service import SyncService
from services.demo_service import DemoService
from app.ui.workers import SyncWorker, DemoWorker


class SyncWidget(QWidget):
    """5.3 & 5.4 Sync & Audit Screen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sync_worker: SyncWorker = None
        self.demo_worker: DemoWorker = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Control Bar
        ctrl_group = QGroupBox("ĐỒNG BỘ DỮ LIỆU & QUẢN LÝ DEMO")
        ctrl_layout = QHBoxLayout(ctrl_group)

        ctrl_layout.addWidget(QLabel("Ngày:"))
        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setDate(QDate.currentDate())
        self.date_picker.dateChanged.connect(self.load_messages)
        ctrl_layout.addWidget(self.date_picker)

        ctrl_layout.addWidget(QLabel("Ca:"))
        self.combo_shift = QComboBox()
        self.combo_shift.addItems(["Ca 1", "Ca 2", "Ca 3"])
        self.combo_shift.currentIndexChanged.connect(self.load_messages)
        ctrl_layout.addWidget(self.combo_shift)

        self.btn_sync = QPushButton("⚡ Đồng bộ từ Discord & Meta")
        self.btn_sync.clicked.connect(self.trigger_sync)
        ctrl_layout.addWidget(self.btn_sync)

        self.btn_load_demo = QPushButton("🧪 Nạp dữ liệu DEMO")
        self.btn_load_demo.setObjectName("btn_secondary")
        self.btn_load_demo.clicked.connect(self.trigger_demo)
        ctrl_layout.addWidget(self.btn_load_demo)

        self.btn_clear_demo = QPushButton("🗑️ Xóa DEMO")
        self.btn_clear_demo.setObjectName("btn_danger")
        self.btn_clear_demo.clicked.connect(self.clear_demo)
        ctrl_layout.addWidget(self.btn_clear_demo)

        ctrl_layout.addStretch()
        layout.addWidget(ctrl_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # Indeterminate
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Message Audit Table
        self.lbl_table_info = QLabel("Danh sách tin nhắn trong ca làm việc:")
        self.lbl_table_info.setStyleSheet("font-weight: bold; color: #89b4fa;")
        layout.addWidget(self.lbl_table_info)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Nền tảng", "Thời gian (VN)", "Người gửi", "Nội dung", "Trạng thái", "Thao tác xác minh"
        ])
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        layout.addWidget(self.table)

        # Initial load
        self.load_messages()

    def get_selected_date_str(self) -> str:
        return self.date_picker.date().toString("yyyy-MM-dd")

    def get_selected_shift_num(self) -> int:
        return self.combo_shift.currentIndex() + 1

    def trigger_sync(self):
        """Starts background sync for selected shift."""
        self.progress_bar.setVisible(True)
        self.btn_sync.setEnabled(False)

        date_str = self.get_selected_date_str()
        shift_num = self.get_selected_shift_num()

        self.sync_worker = SyncWorker(date_str, shift_num)
        self.sync_worker.sync_finished.connect(self._on_sync_finished)
        self.sync_worker.start()

    def _on_sync_finished(self, result: dict):
        self.progress_bar.setVisible(False)
        self.btn_sync.setEnabled(True)
        
        status = result.get("status")
        synced = result.get("records_synced", 0)
        errors = result.get("errors", [])
        
        err_text = f"\nGhi chú / Lỗi: {'; '.join(errors)}" if errors else ""
        QMessageBox.information(
            self,
            "Đồng bộ hoàn tất",
            f"Trạng thái: {status.upper()}\nSố bản ghi mới: {synced}{err_text}"
        )
        self.load_messages()

    def trigger_demo(self):
        """Loads demo records."""
        self.progress_bar.setVisible(True)
        self.btn_load_demo.setEnabled(False)

        date_str = self.get_selected_date_str()
        self.demo_worker = DemoWorker(date_str)
        self.demo_worker.demo_finished.connect(self._on_demo_finished)
        self.demo_worker.start()

    def _on_demo_finished(self, result: dict):
        self.progress_bar.setVisible(False)
        self.btn_load_demo.setEnabled(True)
        QMessageBox.information(
            self,
            "Nạp Demo thành công",
            f"Đã tạo {result.get('messages')} tin nhắn mô phỏng, {result.get('tickets')} ticket và {result.get('classifications')} phân loại AI cho ngày đã chọn!"
        )
        self.load_messages()

    def clear_demo(self):
        """Removes demo records."""
        date_str = self.get_selected_date_str()
        DemoService.clear_demo_data(date_str)
        QMessageBox.information(self, "Đã xóa", f"Đã xóa dữ liệu DEMO của ngày {date_str}.")
        self.load_messages()

    def load_messages(self):
        """Query messages within shift window and display in table."""
        date_str = self.get_selected_date_str()
        shift_num = self.get_selected_shift_num()
        shift_window = ShiftService.get_shift_window(date_str, shift_num)

        self.lbl_table_info.setText(
            f"Danh sách tin nhắn: {date_str} · Ca {shift_num} ({shift_window.start_local.strftime('%H:%M')} - {shift_window.end_local.strftime('%H:%M')})"
        )

        with db_manager.get_session() as session:
            msgs = session.execute(
                select(Message).where(
                    and_(
                        Message.timestamp_utc >= shift_window.start_utc,
                        Message.timestamp_utc < shift_window.end_utc,
                    )
                ).order_by(Message.timestamp_utc.asc())
            ).scalars().all()

            self.table.setRowCount(len(msgs))
            for row, m in enumerate(msgs):
                self.table.setItem(row, 0, QTableWidgetItem(str(m.id)))
                self.table.setItem(row, 1, QTableWidgetItem(m.platform))
                self.table.setItem(row, 2, QTableWidgetItem(m.timestamp_local.strftime("%H:%M:%S")))
                self.table.setItem(row, 3, QTableWidgetItem(m.author_name or m.author_id))
                self.table.setItem(row, 4, QTableWidgetItem(m.content))

                # Status item
                status_item = QTableWidgetItem(m.verification_status)
                if m.verification_status == "verified":
                    status_item.setForeground(Qt.green)
                elif m.verification_status == "unverified_agent":
                    status_item.setForeground(Qt.yellow)
                else:
                    status_item.setForeground(Qt.lightGray)
                self.table.setItem(row, 5, status_item)

                # Action button for unverified messages
                btn_verify = QPushButton("Xác nhận của tôi" if m.verification_status != "verified" else "Bỏ xác nhận")
                btn_verify.setObjectName("btn_secondary" if m.verification_status == "verified" else "")
                btn_verify.clicked.connect(lambda ch, mid=m.id, curr_stat=m.verification_status: self.toggle_verify(mid, curr_stat))
                self.table.setCellWidget(row, 6, btn_verify)

    def toggle_verify(self, message_id: int, current_status: str):
        """Allows manual verification of message author."""
        svc = SyncService()
        new_state = (current_status != "verified")
        svc.manual_verify_message(message_id, new_state, mark_as_reply=new_state)
        self.load_messages()
