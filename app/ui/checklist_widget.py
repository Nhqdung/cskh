"""
Checklist Widget for End-of-Shift Tasks.
Allows CSKH staff to review and update checklist items with explicit reasons and SLA audit.
Adheres strictly to Section 5.8.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QRadioButton, QButtonGroup, QLineEdit, QPushButton, QScrollArea,
    QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Signal

from schemas.shift_schema import ChecklistStatus, ChecklistItemKey, ChecklistItemSchema
from services.shift_service import ShiftService


class ChecklistItemRow(QFrame):
    """Row component representing a single checklist item."""

    def __init__(self, item: ChecklistItemSchema, on_changed_callback=None):
        super().__init__()
        self.item = item
        self.on_changed = on_changed_callback
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #11111b;
                border: 1px solid #313244;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(6)

        # Title & Status Radios
        top_layout = QHBoxLayout()
        lbl_title = QLabel(self.item.title)
        lbl_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #89b4fa;")
        top_layout.addWidget(lbl_title)
        top_layout.addStretch()

        self.btn_group = QButtonGroup(self)
        self.rb_completed = QRadioButton("✅ Hoàn thành")
        self.rb_incomplete = QRadioButton("❌ Chưa xong")
        self.rb_na = QRadioButton("⚪ K/A")
        self.rb_not_checked = QRadioButton("⚠️ Chưa kiểm tra")

        for idx, rb in enumerate([self.rb_completed, self.rb_incomplete, self.rb_na, self.rb_not_checked]):
            self.btn_group.addButton(rb, idx)
            top_layout.addWidget(rb)

        main_layout.addLayout(top_layout)

        # Reason Input (shown or highlighted if incomplete)
        bottom_layout = QHBoxLayout()
        lbl_reason = QLabel("Lý do nếu chưa hoàn thành:")
        lbl_reason.setStyleSheet("color: #a6adc8; font-size: 12px;")
        self.txt_reason = QLineEdit(self.item.reason or "")
        self.txt_reason.setPlaceholderText("Nhập lý do ngắn gọn...")

        bottom_layout.addWidget(lbl_reason)
        bottom_layout.addWidget(self.txt_reason)
        main_layout.addLayout(bottom_layout)

        # Special SLA notice
        if self.item.item_key == ChecklistItemKey.REPLY_SLA_10M:
            lbl_sla_note = QLabel("ℹ️ SLA < 10 phút yêu cầu bằng chứng timestamp đối chiếu. Nếu thiếu mốc thời gian, vui lòng xác minh.")
            lbl_sla_note.setStyleSheet("color: #fab387; font-size: 11px;")
            main_layout.addWidget(lbl_sla_note)
        elif self.item.item_key == ChecklistItemKey.REPLY_7_VIDEOS_TIKTOK_YT:
            lbl_tt_note = QLabel("ℹ️ TikTok/YT chưa tích hợp API tự động. Yêu cầu nhân viên xác minh thủ công.")
            lbl_tt_note.setStyleSheet("color: #fab387; font-size: 11px;")
            main_layout.addWidget(lbl_tt_note)

        # Set initial status
        if self.item.status == ChecklistStatus.COMPLETED:
            self.rb_completed.setChecked(True)
        elif self.item.status == ChecklistStatus.INCOMPLETE:
            self.rb_incomplete.setChecked(True)
        elif self.item.status == ChecklistStatus.NOT_APPLICABLE:
            self.rb_na.setChecked(True)
        else:
            self.rb_not_checked.setChecked(True)

    def get_current_state(self) -> ChecklistItemSchema:
        """Returns updated ChecklistItemSchema from current widget inputs."""
        checked_id = self.btn_group.checkedId()
        if checked_id == 0:
            status = ChecklistStatus.COMPLETED
        elif checked_id == 1:
            status = ChecklistStatus.INCOMPLETE
        elif checked_id == 2:
            status = ChecklistStatus.NOT_APPLICABLE
        else:
            status = ChecklistStatus.NOT_CHECKED

        return ChecklistItemSchema(
            item_key=self.item.item_key,
            title=self.item.title,
            status=status,
            reason=self.txt_reason.text().strip() or None,
        )


class ChecklistWidget(QWidget):
    """5.8 Checklist management screen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.date_str = ""
        self.shift_num = 1
        self.rows: list[ChecklistItemRow] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        self.lbl_header = QLabel("CHECKLIST CUỐI CA")
        self.lbl_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #89b4fa;")
        header_layout.addWidget(self.lbl_header)
        header_layout.addStretch()

        self.btn_save_checklist = QPushButton("💾 Lưu Checklist")
        self.btn_save_checklist.clicked.connect(self.save_checklist)
        header_layout.addWidget(self.btn_save_checklist)

        layout.addLayout(header_layout)

        # Scrollable area of items
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(10)
        self.scroll.setWidget(self.scroll_content)

        layout.addWidget(self.scroll)

    def load_checklist(self, date_str: str, shift_num: int):
        """Loads and displays items for the specific date and shift."""
        self.date_str = date_str
        self.shift_num = shift_num
        self.lbl_header.setText(f"CHECKLIST CUỐI CA: {date_str} · Ca {shift_num}")

        # Clear existing rows
        for r in self.rows:
            self.scroll_layout.removeWidget(r)
            r.deleteLater()
        self.rows.clear()

        items = ShiftService.get_or_create_checklist(date_str, shift_num)
        for it in items:
            row = ChecklistItemRow(it)
            self.rows.append(row)
            self.scroll_layout.addWidget(row)

        self.scroll_layout.addStretch()

    def save_checklist(self):
        """Persists current status and reasons to database."""
        if not self.date_str:
            return

        for r in self.rows:
            st = r.get_current_state()
            ShiftService.update_checklist_item(
                self.date_str,
                self.shift_num,
                st.item_key,
                st.status,
                st.reason,
            )

        QMessageBox.information(self, "Đã lưu", "Checklist đã được cập nhật thành công!")

    def get_items(self) -> list[ChecklistItemSchema]:
        """Returns the current list of checklist schemas."""
        return [r.get_current_state() for r in self.rows]
