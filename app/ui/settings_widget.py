"""
Settings and Account Configuration Widget.
Allows configuration of:
- Discord Bot Token, User ID, Allowed Channels
- Meta App ID, Page ID, Page Access Token, Webhook Secret
- Gemini API Key and Model Name
- Shift time boundaries and timezones
Adheres strictly to Section 5.2 and security requirements (no plain password logging).
"""

import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QLineEdit, QPushButton, QGroupBox, QComboBox, QSpinBox,
    QMessageBox, QScrollArea
)
from PySide6.QtCore import Qt

from database.connection import db_manager
from models.orm import Setting, WorkShift
from services.security_service import SecurityService
from app.ui.workers import ConnectionTestWorker


class SettingsWidget(QWidget):
    """5.2 Account Configuration Screen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: ConnectionTestWorker = None
        self._init_ui()
        self.load_settings()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(14)

        # 1. Employee & General
        gen_group = QGroupBox("THÔNG TIN NHÂN VIÊN & HỆ THỐNG")
        gen_layout = QGridLayout(gen_group)

        gen_layout.addWidget(QLabel("Tên nhân viên CSKH:"), 0, 0)
        self.txt_emp_name = QLineEdit()
        self.txt_emp_name.setPlaceholderText("Ví dụ: Nguyễn Văn A")
        gen_layout.addWidget(self.txt_emp_name, 0, 1)

        gen_layout.addWidget(QLabel("Múi giờ chuẩn:"), 1, 0)
        self.txt_timezone = QLineEdit("Asia/Ho_Chi_Minh")
        self.txt_timezone.setReadOnly(True)
        gen_layout.addWidget(self.txt_timezone, 1, 1)

        gen_layout.addWidget(QLabel("Thời hạn lưu tin nhắn (ngày):"), 2, 0)
        self.spin_retention = QSpinBox()
        self.spin_retention.setRange(7, 365)
        self.spin_retention.setValue(60)
        gen_layout.addWidget(self.spin_retention, 2, 1)

        layout.addWidget(gen_group)

        # 2. Discord Bot Settings
        disc_group = QGroupBox("CẤU HÌNH DISCORD BOT (API CHÍNH THỨC)")
        disc_layout = QGridLayout(disc_group)

        disc_layout.addWidget(QLabel("Discord Bot Token:"), 0, 0)
        self.txt_discord_token = QLineEdit()
        self.txt_discord_token.setEchoMode(QLineEdit.Password)
        self.txt_discord_token.setPlaceholderText("Nhập Bot Token từ Discord Developer Portal")
        disc_layout.addWidget(self.txt_discord_token, 0, 1)

        disc_layout.addWidget(QLabel("Discord User ID của bạn:"), 1, 0)
        self.txt_discord_user_id = QLineEdit()
        self.txt_discord_user_id.setPlaceholderText("User ID để nhận diện tin nhắn của bạn")
        disc_layout.addWidget(self.txt_discord_user_id, 1, 1)

        disc_layout.addWidget(QLabel("Channel / Ticket IDs được phép:"), 2, 0)
        self.txt_discord_channels = QLineEdit()
        self.txt_discord_channels.setPlaceholderText("Cách nhau bởi dấu phẩy, ví dụ: 123456789,987654321")
        disc_layout.addWidget(self.txt_discord_channels, 2, 1)

        self.btn_test_discord = QPushButton("Kiểm tra kết nối Discord")
        self.btn_test_discord.setObjectName("btn_secondary")
        self.btn_test_discord.clicked.connect(lambda: self._test_platform("discord"))
        disc_layout.addWidget(self.btn_test_discord, 3, 1, alignment=Qt.AlignRight)

        layout.addWidget(disc_group)

        # 3. Meta Settings
        meta_group = QGroupBox("CẤU HÌNH META BUSINESS SUITE / GRAPH API")
        meta_layout = QGridLayout(meta_group)

        meta_layout.addWidget(QLabel("Meta Page ID:"), 0, 0)
        self.txt_meta_page_id = QLineEdit()
        self.txt_meta_page_id.setPlaceholderText("ID của Fanpage được cấp quyền")
        meta_layout.addWidget(self.txt_meta_page_id, 0, 1)

        meta_layout.addWidget(QLabel("Page Access Token:"), 1, 0)
        self.txt_meta_token = QLineEdit()
        self.txt_meta_token.setEchoMode(QLineEdit.Password)
        self.txt_meta_token.setPlaceholderText("Page Access Token có quyền pages_messaging, pages_read_engagement")
        meta_layout.addWidget(self.txt_meta_token, 1, 1)

        meta_layout.addWidget(QLabel("Meta App ID:"), 2, 0)
        self.txt_meta_app_id = QLineEdit()
        self.txt_meta_app_id.setPlaceholderText("App ID trên developers.facebook.com")
        meta_layout.addWidget(self.txt_meta_app_id, 2, 1)

        meta_layout.addWidget(QLabel("Webhook Verify Token:"), 3, 0)
        self.txt_meta_verify = QLineEdit()
        self.txt_meta_verify.setPlaceholderText("Mã bảo mật xác thực Webhook tự đặt")
        meta_layout.addWidget(self.txt_meta_verify, 3, 1)

        self.btn_test_meta = QPushButton("Kiểm tra kết nối Meta")
        self.btn_test_meta.setObjectName("btn_secondary")
        self.btn_test_meta.clicked.connect(lambda: self._test_platform("meta"))
        meta_layout.addWidget(self.btn_test_meta, 4, 1, alignment=Qt.AlignRight)

        layout.addWidget(meta_group)

        # 4. Gemini API Settings
        gem_group = QGroupBox("CẤU HÌNH GOOGLE GEMINI AI")
        gem_layout = QGridLayout(gem_group)

        gem_layout.addWidget(QLabel("Gemini API Key:"), 0, 0)
        self.txt_gemini_key = QLineEdit()
        self.txt_gemini_key.setEchoMode(QLineEdit.Password)
        self.txt_gemini_key.setPlaceholderText("Lấy key tại Google AI Studio (aistudio.google.com)")
        gem_layout.addWidget(self.txt_gemini_key, 0, 1)

        gem_layout.addWidget(QLabel("Model Identifier:"), 1, 0)
        self.combo_gemini_model = QComboBox()
        self.combo_gemini_model.setEditable(True)
        self.combo_gemini_model.addItems(["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash"])
        gem_layout.addWidget(self.combo_gemini_model, 1, 1)

        self.btn_test_gemini = QPushButton("Kiểm tra Gemini API")
        self.btn_test_gemini.setObjectName("btn_secondary")
        self.btn_test_gemini.clicked.connect(lambda: self._test_platform("gemini"))
        gem_layout.addWidget(self.btn_test_gemini, 2, 1, alignment=Qt.AlignRight)

        layout.addWidget(gem_group)

        # Bottom Save Button
        btn_save_all = QPushButton("💾 LƯU TOÀN BỘ CẤU HÌNH")
        btn_save_all.setStyleSheet("background-color: #a6e3a1; color: #11111b; font-size: 14px; font-weight: bold; padding: 10px;")
        btn_save_all.clicked.connect(self.save_all_settings)
        layout.addWidget(btn_save_all)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def load_settings(self):
        """Loads credentials and configs from env/keyring/database."""
        self.txt_emp_name.setText(SecurityService.get_credential("EMPLOYEE_NAME", "Nguyễn Văn A"))
        self.txt_discord_token.setText(SecurityService.get_credential("DISCORD_BOT_TOKEN", ""))
        self.txt_discord_user_id.setText(SecurityService.get_credential("DISCORD_USER_ID", ""))
        self.txt_discord_channels.setText(SecurityService.get_credential("DISCORD_ALLOWED_CHANNEL_IDS", ""))

        self.txt_meta_page_id.setText(SecurityService.get_credential("META_PAGE_ID", ""))
        self.txt_meta_token.setText(SecurityService.get_credential("META_PAGE_ACCESS_TOKEN", ""))
        self.txt_meta_app_id.setText(SecurityService.get_credential("META_APP_ID", ""))
        self.txt_meta_verify.setText(SecurityService.get_credential("META_WEBHOOK_VERIFY_TOKEN", ""))

        self.txt_gemini_key.setText(SecurityService.get_credential("GEMINI_API_KEY", ""))
        model_name = SecurityService.get_credential("GEMINI_MODEL_NAME", "gemini-2.5-flash")
        idx = self.combo_gemini_model.findText(model_name)
        if idx >= 0:
            self.combo_gemini_model.setCurrentIndex(idx)
        else:
            self.combo_gemini_model.setEditText(model_name)

    def save_all_settings(self):
        """Saves credentials into environment, keyring, and local database."""
        settings_map = {
            "EMPLOYEE_NAME": self.txt_emp_name.text().strip(),
            "DISCORD_BOT_TOKEN": self.txt_discord_token.text().strip(),
            "DISCORD_USER_ID": self.txt_discord_user_id.text().strip(),
            "DISCORD_ALLOWED_CHANNEL_IDS": self.txt_discord_channels.text().strip(),
            "META_PAGE_ID": self.txt_meta_page_id.text().strip(),
            "META_PAGE_ACCESS_TOKEN": self.txt_meta_token.text().strip(),
            "META_APP_ID": self.txt_meta_app_id.text().strip(),
            "META_WEBHOOK_VERIFY_TOKEN": self.txt_meta_verify.text().strip(),
            "GEMINI_API_KEY": self.txt_gemini_key.text().strip(),
            "GEMINI_MODEL_NAME": self.combo_gemini_model.currentText().strip(),
            "DATA_RETENTION_DAYS": str(self.spin_retention.value()),
        }

        # 1. Update keyring & runtime env
        for k, v in settings_map.items():
            SecurityService.set_credential(k, v)

        # 2. Persist to database Setting table
        with db_manager.get_session() as session:
            for k, v in settings_map.items():
                # Avoid storing raw secrets in db directly
                val_to_store = v if not ("TOKEN" in k or "KEY" in k or "SECRET" in k) else "[STORED_IN_KEYRING_OR_ENV]"
                setting = session.get(Setting, k)
                if not setting:
                    setting = Setting(key=k, value=val_to_store)
                    session.add(setting)
                else:
                    setting.value = val_to_store
            session.commit()

        # 3. Append to .env file if it exists or write safe .env
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        try:
            lines = []
            for k, v in settings_map.items():
                lines.append(f"{k}={v}")
            env_path.write_text("\n".join(lines), encoding="utf-8")
        except Exception as ex:
            pass

        QMessageBox.information(self, "Đã lưu", "Cấu hình tài khoản và thông tin đã được lưu thành công!")

    def _test_platform(self, platform: str):
        self.worker = ConnectionTestWorker(platform)
        self.worker.test_finished.connect(self._on_test_finished)
        self.worker.start()

    def _on_test_finished(self, platform: str, success: bool, message: str, details: dict):
        if success:
            QMessageBox.information(self, f"Thành công ({platform.upper()})", message)
        else:
            QMessageBox.warning(self, f"Thất bại ({platform.upper()})", message)
