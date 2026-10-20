"""
Dashboard Widget for Personal CSKH Reporting Assistant.
Displays real-time status of shift, platforms, metrics, and sync status.
Adheres strictly to Section 5.1 requirements.
"""

import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QGroupBox, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Signal

from services.shift_service import ShiftService
from services.metrics_service import MetricsService
from connectors.discord_connector import DiscordConnector
from connectors.meta_connector import MetaConnector
from services.classification_service import ClassificationService
from app.ui.workers import ConnectionTestWorker


class DashboardWidget(QWidget):
    """5.1 Dashboard screen displaying connection statuses, shift times, and metrics summary."""
    navigate_to_tab = Signal(int) # Signal to navigate to tab index

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: ConnectionTestWorker = None
        self._init_ui()
        self.refresh_dashboard()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # 1. Top Bar: Shift & Work Date Info
        shift_group = QGroupBox("THÔNG TIN CA LÀM VIỆC HIỆN TẠI")
        shift_layout = QGridLayout(shift_group)
        shift_layout.setSpacing(12)

        self.lbl_work_date = QLabel("Ngày làm việc: --")
        self.lbl_work_date.setStyleSheet("font-size: 14px; font-weight: bold; color: #89b4fa;")
        
        self.lbl_current_shift = QLabel("Ca hiện tại: --")
        self.lbl_current_shift.setStyleSheet("font-size: 14px; font-weight: bold; color: #a6e3a1;")

        self.lbl_shift_time = QLabel("Thời gian ca: --:-- đến --:-- (Asia/Ho_Chi_Minh)")
        self.lbl_shift_time.setStyleSheet("font-size: 13px; color: #cdd6f4;")

        shift_layout.addWidget(self.lbl_work_date, 0, 0)
        shift_layout.addWidget(self.lbl_current_shift, 0, 1)
        shift_layout.addWidget(self.lbl_shift_time, 1, 0, 1, 2)
        layout.addWidget(shift_group)

        # 2. Connection Statuses
        conn_group = QGroupBox("TRẠNG THÁI KẾT NỐI HỆ THỐNG")
        conn_layout = QGridLayout(conn_group)
        conn_layout.setSpacing(14)

        # Discord
        lbl_d_title = QLabel("Discord Bot:")
        lbl_d_title.setStyleSheet("font-weight: bold;")
        self.lbl_discord_status = QLabel("⚪ Chưa kiểm tra")
        self.lbl_discord_status.setStyleSheet("color: #f9e2af;")
        self.btn_test_discord = QPushButton("Kiểm tra Discord")
        self.btn_test_discord.setObjectName("btn_secondary")
        self.btn_test_discord.clicked.connect(lambda: self._test_platform("discord"))

        # Meta
        lbl_m_title = QLabel("Meta Business / Page:")
        lbl_m_title.setStyleSheet("font-weight: bold;")
        self.lbl_meta_status = QLabel("⚪ Chưa kiểm tra")
        self.lbl_meta_status.setStyleSheet("color: #f9e2af;")
        self.btn_test_meta = QPushButton("Kiểm tra Meta")
        self.btn_test_meta.setObjectName("btn_secondary")
        self.btn_test_meta.clicked.connect(lambda: self._test_platform("meta"))

        # Gemini
        lbl_g_title = QLabel("Gemini AI API:")
        lbl_g_title.setStyleSheet("font-weight: bold;")
        self.lbl_gemini_status = QLabel("⚪ Chưa kiểm tra")
        self.lbl_gemini_status.setStyleSheet("color: #f9e2af;")
        self.btn_test_gemini = QPushButton("Kiểm tra Gemini")
        self.btn_test_gemini.setObjectName("btn_secondary")
        self.btn_test_gemini.clicked.connect(lambda: self._test_platform("gemini"))

        conn_layout.addWidget(lbl_d_title, 0, 0)
        conn_layout.addWidget(self.lbl_discord_status, 0, 1)
        conn_layout.addWidget(self.btn_test_discord, 0, 2)

        conn_layout.addWidget(lbl_m_title, 1, 0)
        conn_layout.addWidget(self.lbl_meta_status, 1, 1)
        conn_layout.addWidget(self.btn_test_meta, 1, 2)

        conn_layout.addWidget(lbl_g_title, 2, 0)
        conn_layout.addWidget(self.lbl_gemini_status, 2, 1)
        conn_layout.addWidget(self.btn_test_gemini, 2, 2)

        layout.addWidget(conn_group)

        # 3. Live Shift Counters
        stat_group = QGroupBox("SỐ LIỆU TỔNG QUAN TRONG CA")
        stat_layout = QGridLayout(stat_group)
        stat_layout.setSpacing(16)

        # Card 1: Discord Messages
        self.card_discord = self._create_metric_card("Discord (Tin gửi trong ca)", "0", "#89b4fa")
        # Card 2: Meta Verified Responses
        self.card_meta = self._create_metric_card("Meta (Phản hồi đã xác minh)", "0", "#a6e3a1")
        # Card 3: Unverified / Needing Manual Review
        self.card_unverified = self._create_metric_card("Cần đối chiếu thủ công", "0", "#fab387")

        stat_layout.addWidget(self.card_discord, 0, 0)
        stat_layout.addWidget(self.card_meta, 0, 1)
        stat_layout.addWidget(self.card_unverified, 0, 2)

        layout.addWidget(stat_group)

        # 4. Sync State & Actions
        sync_info_group = QGroupBox("ĐỒNG BỘ DỮ LIỆU")
        sync_info_layout = QHBoxLayout(sync_info_group)

        self.lbl_last_sync = QLabel("Trạng thái đồng bộ lần cuối: Chưa thực hiện")
        self.lbl_last_sync.setStyleSheet("color: #a6adc8;")
        sync_info_layout.addWidget(self.lbl_last_sync)

        sync_info_layout.addStretch()

        self.btn_audit_unverified = QPushButton("🔍 Xem case cần đối chiếu")
        self.btn_audit_unverified.setObjectName("btn_secondary")
        self.btn_audit_unverified.clicked.connect(lambda: self.navigate_to_tab.emit(3)) # Go to Sync/Audit Tab
        sync_info_layout.addWidget(self.btn_audit_unverified)

        self.btn_refresh = QPushButton("🔄 Làm mới dữ liệu")
        self.btn_refresh.clicked.connect(self.refresh_dashboard)
        sync_info_layout.addWidget(self.btn_refresh)

        layout.addWidget(sync_info_group)
        layout.addStretch()

    def _create_metric_card(self, title: str, initial_value: str, color_hex: str) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: #11111b;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        vbox = QVBoxLayout(frame)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 12px; color: #a6adc8;")
        
        lbl_val = QLabel(initial_value)
        lbl_val.setObjectName("card_val")
        lbl_val.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {color_hex};")
        
        vbox.addWidget(lbl_title)
        vbox.addWidget(lbl_val)
        return frame

    def refresh_dashboard(self):
        """Refreshes shift info and calculates current metrics."""
        now_local = ShiftService.get_current_local_time()
        date_str, shift_num = ShiftService.resolve_shift_for_timestamp(now_local)
        shift_window = ShiftService.get_shift_window(date_str, shift_num)

        self.lbl_work_date.setText(f"Ngày làm việc: {date_str}")
        self.lbl_current_shift.setText(f"Ca hiện tại: {shift_window.shift_name} (Ca {shift_num})")
        self.lbl_shift_time.setText(
            f"Thời gian ca: {shift_window.start_local.strftime('%H:%M')} đến {shift_window.end_local.strftime('%H:%M')} (Asia/Ho_Chi_Minh)"
        )

        # Check configured states statically
        disc_cfg = DiscordConnector().is_configured()
        meta_cfg = MetaConnector().is_configured()
        gemini_cfg = ClassificationService().is_configured()

        if not disc_cfg:
            self.lbl_discord_status.setText("❌ Chưa cấu hình")
            self.lbl_discord_status.setStyleSheet("color: #f38ba8;")
        if not meta_cfg:
            self.lbl_meta_status.setText("❌ Chưa cấu hình")
            self.lbl_meta_status.setStyleSheet("color: #f38ba8;")
        if not gemini_cfg:
            self.lbl_gemini_status.setText("❌ Chưa cấu hình")
            self.lbl_gemini_status.setStyleSheet("color: #f38ba8;")

        # Metrics
        metrics, _ = MetricsService.calculate_shift_metrics(date_str, shift_num)
        
        # Total discord messages sent
        val_disc = self.card_discord.findChild(QLabel, "card_val")
        if val_disc:
            val_disc.setText(str(metrics.messages_replied))

        # Meta verified
        val_meta = self.card_meta.findChild(QLabel, "card_val")
        if val_meta:
            val_meta.setText("0") # Separated if meta verified

        # Unverified
        val_unver = self.card_unverified.findChild(QLabel, "card_val")
        if val_unver:
            val_unver.setText(str(metrics.unverified_count))

    def _test_platform(self, platform: str):
        """Run platform connection test in background worker."""
        if platform == "discord":
            self.lbl_discord_status.setText("⏳ Đang kiểm tra...")
            self.lbl_discord_status.setStyleSheet("color: #89b4fa;")
            self.btn_test_discord.setEnabled(False)
        elif platform == "meta":
            self.lbl_meta_status.setText("⏳ Đang kiểm tra...")
            self.lbl_meta_status.setStyleSheet("color: #89b4fa;")
            self.btn_test_meta.setEnabled(False)
        elif platform == "gemini":
            self.lbl_gemini_status.setText("⏳ Đang kiểm tra...")
            self.lbl_gemini_status.setStyleSheet("color: #89b4fa;")
            self.btn_test_gemini.setEnabled(False)

        self.worker = ConnectionTestWorker(platform)
        self.worker.test_finished.connect(self._on_test_finished)
        self.worker.start()

    def _on_test_finished(self, platform: str, success: bool, message: str, details: dict):
        if platform == "discord":
            self.btn_test_discord.setEnabled(True)
            if success:
                self.lbl_discord_status.setText(f"🟢 Sẵn sàng ({details.get('bot_user')})")
                self.lbl_discord_status.setStyleSheet("color: #a6e3a1;")
            else:
                self.lbl_discord_status.setText("🔴 Lỗi kết nối")
                self.lbl_discord_status.setStyleSheet("color: #f38ba8;")
                QMessageBox.warning(self, "Lỗi kết nối Discord", message)

        elif platform == "meta":
            self.btn_test_meta.setEnabled(True)
            if success:
                self.lbl_meta_status.setText(f"🟢 Sẵn sàng ({details.get('page_name')})")
                self.lbl_meta_status.setStyleSheet("color: #a6e3a1;")
            else:
                self.lbl_meta_status.setText("🔴 Lỗi kết nối")
                self.lbl_meta_status.setStyleSheet("color: #f38ba8;")
                QMessageBox.warning(self, "Lỗi kết nối Meta", message)

        elif platform == "gemini":
            self.btn_test_gemini.setEnabled(True)
            if success:
                self.lbl_gemini_status.setText("🟢 Sẵn sàng")
                self.lbl_gemini_status.setStyleSheet("color: #a6e3a1;")
            else:
                self.lbl_gemini_status.setText("🔴 Lỗi kết nối")
                self.lbl_gemini_status.setStyleSheet("color: #f38ba8;")
                QMessageBox.warning(self, "Lỗi kết nối Gemini", message)
