"""
QThread Workers for asynchronous tasks to prevent UI freezing.
"""

from PySide6.QtCore import QThread, Signal
from connectors.discord_connector import DiscordConnector
from connectors.meta_connector import MetaConnector
from services.classification_service import ClassificationService
from services.sync_service import SyncService
from services.demo_service import DemoService


class ConnectionTestWorker(QThread):
    """Worker to test platform connections without blocking the GUI."""
    test_finished = Signal(str, bool, str, dict) # platform, success, error_message, details

    def __init__(self, platform: str):
        super().__init__()
        self.platform = platform

    def run(self):
        if self.platform == "discord":
            connector = DiscordConnector()
            res = connector.test_connection()
            self.test_finished.emit(
                "discord",
                res["success"],
                res["error"] or "Kết nối Discord Bot thành công!",
                res.get("details") or {},
            )
        elif self.platform == "meta":
            connector = MetaConnector()
            res = connector.test_connection()
            self.test_finished.emit(
                "meta",
                res["success"],
                res["error"] or "Kết nối Meta Graph API thành công!",
                res.get("details") or {},
            )
        elif self.platform == "gemini":
            ai_svc = ClassificationService()
            if not ai_svc.is_configured():
                self.test_finished.emit("gemini", False, "Chưa cấu hình Gemini API Key.", {})
            else:
                try:
                    # Test call with dummy text
                    test_res = ai_svc.classify_conversation_messages(
                        "test_conv",
                        [{"content": "Chào shop, mình cần tư vấn dịch vụ.", "is_employee": False}],
                        force_reclassify=True,
                    )
                    self.test_finished.emit("gemini", True, "Kết nối Gemini API thành công!", {"confidence": test_res.confidence})
                except Exception as e:
                    self.test_finished.emit("gemini", False, f"Lỗi Gemini: {e}", {})


class SyncWorker(QThread):
    """Worker to run sync backfill in the background."""
    sync_finished = Signal(dict)

    def __init__(self, date_str: str, shift_num: int):
        super().__init__()
        self.date_str = date_str
        self.shift_num = shift_num

    def run(self):
        svc = SyncService()
        res = svc.sync_shift_history(self.date_str, self.shift_num)
        self.sync_finished.emit(res)


class DemoWorker(QThread):
    """Worker to populate simulated demo data."""
    demo_finished = Signal(dict)

    def __init__(self, date_str: str):
        super().__init__()
        self.date_str = date_str

    def run(self):
        res = DemoService.populate_demo_data(self.date_str)
        self.demo_finished.emit(res)
