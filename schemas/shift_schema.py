"""
Schemas for Work Shift and Checklist management.
Handles shift timing, boundary calculations, and checklist definitions.
"""

import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class ChecklistStatus(str, Enum):
    NOT_CHECKED = "not_checked"
    COMPLETED = "completed"
    INCOMPLETE = "incomplete"
    NOT_APPLICABLE = "not_applicable"


class ChecklistItemKey(str, Enum):
    CLEAN_BACKLOG = "clean_backlog"
    CHECK_PENDING_12H = "check_pending_12h"
    REPLY_SLA_10M = "reply_sla_10m"
    REPLY_ALL_FB_COMMENTS = "reply_all_fb_comments"
    REPLY_7_VIDEOS_TIKTOK_YT = "reply_7_videos_tiktok_yt"
    ASK_FEEDBACK_POST_TEST = "ask_feedback_post_test"
    CLOSE_UNANSWERED_TICKETS_SHIFT3 = "close_unanswered_tickets_shift3"


STANDARD_CHECKLIST_TITLES = {
    ChecklistItemKey.CLEAN_BACKLOG: "Dọn tồn đọng / đọc bàn giao ca trước",
    ChecklistItemKey.CHECK_PENDING_12H: "Check ticket pending, đóng nếu quá 12h",
    ChecklistItemKey.REPLY_SLA_10M: "Reply Discord + Fanpage SLA < 10 phút",
    ChecklistItemKey.REPLY_ALL_FB_COMMENTS: "Reply hết comment Fanpage",
    ChecklistItemKey.REPLY_7_VIDEOS_TIKTOK_YT: "Reply comment 7 video TikTok/YT",
    ChecklistItemKey.ASK_FEEDBACK_POST_TEST: "Xin feedback sau test máy",
    ChecklistItemKey.CLOSE_UNANSWERED_TICKETS_SHIFT3: "Đóng toàn bộ ticket chưa phản hồi trong ngày",
}


class ChecklistItemSchema(BaseModel):
    item_key: ChecklistItemKey
    title: str
    status: ChecklistStatus = ChecklistStatus.NOT_CHECKED
    reason: Optional[str] = None
    evidence_notes: Optional[str] = None


class WorkShiftConfig(BaseModel):
    shift_num: int
    name: str
    start_time: str # "HH:MM"
    end_time: str   # "HH:MM"
    crosses_midnight: bool = False
    is_active: bool = True


class ShiftTimeWindow(BaseModel):
    date_str: str # YYYY-MM-DD local
    shift_num: int
    shift_name: str
    start_utc: datetime.datetime
    end_utc: datetime.datetime
    start_local: datetime.datetime
    end_local: datetime.datetime
