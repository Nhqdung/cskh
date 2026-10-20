"""
Main Application Window for Personal CSKH Reporting Assistant.
Integrates all tabs:
1. Dashboard
2. Report Generator
3. Checklist
4. Sync & Audit
5. Settings
"""

import sys
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTabWidget, QStatusBar, QFrame
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon

from services.shift_service import ShiftService
from services.security_service import SecurityService
from app.ui.dashboard_widget import DashboardWidget
from app.ui.checklist_widget import ChecklistWidget
from app.ui.report_widget import ReportWidget
from app.ui.sync_widget import SyncWidget
from app.ui.settings_widget import SettingsWidget
from app.ui.styles import MAIN_STYLESHEET


class MainWindow(QMainWindow):
    """Main Application Window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Personal CSKH Reporting Assistant")
        self.resize(1150, 780)
        self.setMinimumSize(950, 650)
        self.setStyleSheet(MAIN_STYLESHEET)

        self._init_ui()
        self._init_timer()

    def _init_ui(self):
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 8)
        main_layout.setSpacing(10)

        # Header bar
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #181825;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 10px 16px;
            }
        """)
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(0, 0, 0, 0)

        lbl_app_title = QLabel("🤖 PERSONAL CSKH REPORTING ASSISTANT")
        lbl_app_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa;")
        h_layout.addWidget(lbl_app_title)

        h_layout.addStretch()

        self.lbl_clock = QLabel("Đang tải giờ...")
        self.lbl_clock.setStyleSheet("font-size: 13px; font-weight: bold; color: #a6e3a1;")
        h_layout.addWidget(self.lbl_clock)

        main_layout.addWidget(header_frame)

        # Tabs
        self.tabs = QTabWidget()
        
        self.dashboard_tab = DashboardWidget()
        self.checklist_tab = ChecklistWidget()
        self.report_tab = ReportWidget(checklist_widget=self.checklist_tab)
        self.sync_tab = SyncWidget()
        self.settings_tab = SettingsWidget()

        self.tabs.addTab(self.dashboard_tab, "📊 Dashboard")
        self.tabs.addTab(self.report_tab, "📝 Tạo Báo Cáo")
        self.tabs.addTab(self.checklist_tab, "✅ Checklist Cuối Ca")
        self.tabs.addTab(self.sync_tab, "⚡ Đồng Bộ & Đối Chiếu")
        self.tabs.addTab(self.settings_tab, "⚙️ Cấu Hình Tài Khoản")

        # Connect signals
        self.dashboard_tab.navigate_to_tab.connect(self.tabs.setCurrentIndex)
        self.tabs.currentChanged.connect(self.on_tab_changed)

        main_layout.addWidget(self.tabs)
        self.setCentralWidget(central_widget)

        # Status Bar
        status_bar = QStatusBar()
        status_bar.setStyleSheet("background-color: #11111b; color: #a6adc8; border-top: 1px solid #313244;")
        self.setStatusBar(status_bar)
        self.status_msg = QLabel("Múi giờ: Asia/Ho_Chi_Minh · SQLite: OK · Bảo mật: Tuân thủ API chính thức")
        status_bar.addPermanentWidget(self.status_msg)

    def _init_timer(self):
        """Update clock display every second."""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)
        self.update_clock()

    def update_clock(self):
        now = ShiftService.get_current_local_time()
        date_str, shift_num = ShiftService.resolve_shift_for_timestamp(now)
        time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        self.lbl_clock.setText(f"🕒 {time_str} · Ca {shift_num}")

    def on_tab_changed(self, index: int):
        if index == 0:
            self.dashboard_tab.refresh_dashboard()
        elif index == 1:
            self.report_tab.on_date_or_shift_changed()
        elif index == 3:
            self.sync_tab.load_messages()
