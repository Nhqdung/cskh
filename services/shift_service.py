"""
Work Shift Service for Personal CSKH Reporting Assistant.
Handles:
- Asia/Ho_Chi_Minh (UTC+7) timezone conversions.
- Shift window resolution (including midnight-crossing Ca 3).
- Strict non-overlapping boundary matching [start, end).
- Database shift persistence and checklist initializations.
"""

import datetime
from zoneinfo import ZoneInfo
from typing import Optional, List, Tuple
from sqlalchemy import select

from database.connection import db_manager
from models.orm import WorkShift, ShiftChecklist
from schemas.shift_schema import (
    WorkShiftConfig,
    ShiftTimeWindow,
    ChecklistItemSchema,
    ChecklistStatus,
    ChecklistItemKey,
    STANDARD_CHECKLIST_TITLES,
)

VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
UTC_TZ = ZoneInfo("UTC")


class ShiftService:
    """Manages shift definitions, timezone conversions, and checklist state."""

    @staticmethod
    def get_current_local_time() -> datetime.datetime:
        """Returns current datetime in Asia/Ho_Chi_Minh timezone."""
        return datetime.datetime.now(VN_TZ)

    @staticmethod
    def utc_to_local(dt_utc: datetime.datetime) -> datetime.datetime:
        """Convert UTC datetime to Asia/Ho_Chi_Minh datetime."""
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=UTC_TZ)
        return dt_utc.astimezone(VN_TZ)

    @staticmethod
    def local_to_utc(dt_local: datetime.datetime) -> datetime.datetime:
        """Convert Asia/Ho_Chi_Minh datetime to UTC datetime."""
        if dt_local.tzinfo is None:
            dt_local = dt_local.replace(tzinfo=VN_TZ)
        return dt_local.astimezone(UTC_TZ)

    @staticmethod
    def get_configured_shifts() -> List[WorkShiftConfig]:
        """Fetch active shift configurations from database or defaults."""
        try:
            with db_manager.get_session() as session:
                shifts = session.execute(
                    select(WorkShift).where(WorkShift.is_active == True).order_by(WorkShift.shift_num)
                ).scalars().all()
                if shifts:
                    return [
                        WorkShiftConfig(
                            shift_num=s.shift_num,
                            name=s.name,
                            start_time=s.start_time,
                            end_time=s.end_time,
                            crosses_midnight=s.crosses_midnight,
                            is_active=s.is_active,
                        )
                        for s in shifts
                    ]
        except Exception:
            pass

        # Safe defaults if DB is uninitialized
        return [
            WorkShiftConfig(shift_num=1, name="Ca 1", start_time="07:00", end_time="15:00", crosses_midnight=False),
            WorkShiftConfig(shift_num=2, name="Ca 2", start_time="15:00", end_time="23:00", crosses_midnight=False),
            WorkShiftConfig(shift_num=3, name="Ca 3", start_time="23:00", end_time="07:00", crosses_midnight=True),
        ]

    @classmethod
    def get_shift_window(cls, date_str: str, shift_num: int) -> ShiftTimeWindow:
        """Calculates precise local and UTC time windows for a given date (YYYY-MM-DD) and shift number.
        
        Boundary rule: [start, end) - half-open interval.
        """
        year, month, day = map(int, date_str.split("-"))
        shift_configs = {s.shift_num: s for s in cls.get_configured_shifts()}
        config = shift_configs.get(
            shift_num,
            WorkShiftConfig(shift_num=shift_num, name=f"Ca {shift_num}", start_time="07:00", end_time="15:00")
        )

        start_h, start_m = map(int, config.start_time.split(":"))
        end_h, end_m = map(int, config.end_time.split(":"))

        start_local = datetime.datetime(year, month, day, start_h, start_m, 0, tzinfo=VN_TZ)

        if config.crosses_midnight or (end_h < start_h) or (end_h == start_h and end_m <= start_m):
            # Ends on the following day
            end_local = start_local + datetime.timedelta(days=1)
            end_local = end_local.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
        else:
            end_local = start_local.replace(hour=end_h, minute=end_m, second=0, microsecond=0)

        start_utc = cls.local_to_utc(start_local)
        end_utc = cls.local_to_utc(end_local)

        return ShiftTimeWindow(
            date_str=date_str,
            shift_num=shift_num,
            shift_name=config.name,
            start_utc=start_utc,
            end_utc=end_utc,
            start_local=start_local,
            end_local=end_local,
        )

    @classmethod
    def resolve_shift_for_timestamp(cls, dt: datetime.datetime) -> Tuple[str, int]:
        """Given any UTC or local datetime, determines which (shift_date, shift_num) it belongs to.
        
        Uses half-open intervals [start, end).
        """
        local_dt = cls.utc_to_local(dt)
        local_date = local_dt.date()

        # Check candidate dates: previous day, today, next day
        for offset in (-1, 0, 1):
            cand_date = local_date + datetime.timedelta(days=offset)
            cand_date_str = cand_date.strftime("%Y-%m-%d")
            for s in cls.get_configured_shifts():
                window = cls.get_shift_window(cand_date_str, s.shift_num)
                if window.start_local <= local_dt < window.end_local:
                    return window.date_str, window.shift_num

        # Fallback to today Ca 1 if no match found
        return local_date.strftime("%Y-%m-%d"), 1

    @classmethod
    def get_or_create_checklist(cls, date_str: str, shift_num: int) -> List[ChecklistItemSchema]:
        """Retrieves or initializes the checklist for a specific shift."""
        expected_keys = [
            ChecklistItemKey.CLEAN_BACKLOG,
            ChecklistItemKey.CHECK_PENDING_12H,
            ChecklistItemKey.REPLY_SLA_10M,
            ChecklistItemKey.REPLY_ALL_FB_COMMENTS,
            ChecklistItemKey.REPLY_7_VIDEOS_TIKTOK_YT,
            ChecklistItemKey.ASK_FEEDBACK_POST_TEST,
        ]
        if shift_num == 3:
            expected_keys.append(ChecklistItemKey.CLOSE_UNANSWERED_TICKETS_SHIFT3)

        items_map = {}
        with db_manager.get_session() as session:
            db_items = session.execute(
                select(ShiftChecklist).where(
                    ShiftChecklist.date_str == date_str,
                    ShiftChecklist.shift_num == shift_num,
                )
            ).scalars().all()
            for it in db_items:
                items_map[it.item_key] = it

            # Create any missing keys
            created = False
            for key in expected_keys:
                if key.value not in items_map:
                    new_item = ShiftChecklist(
                        date_str=date_str,
                        shift_num=shift_num,
                        item_key=key.value,
                        status=ChecklistStatus.NOT_CHECKED.value,
                        reason=None,
                    )
                    session.add(new_item)
                    items_map[key.value] = new_item
                    created = True

            if created:
                session.commit()

        result = []
        for key in expected_keys:
            db_obj = items_map.get(key.value)
            result.append(
                ChecklistItemSchema(
                    item_key=key,
                    title=STANDARD_CHECKLIST_TITLES[key],
                    status=ChecklistStatus(db_obj.status) if db_obj else ChecklistStatus.NOT_CHECKED,
                    reason=db_obj.reason if db_obj else None,
                    evidence_notes=db_obj.evidence_notes if db_obj else None,
                )
            )
        return result

    @classmethod
    def update_checklist_item(
        cls,
        date_str: str,
        shift_num: int,
        item_key: ChecklistItemKey,
        status: ChecklistStatus,
        reason: Optional[str] = None,
    ) -> None:
        """Update a specific checklist item in the database."""
        with db_manager.get_session() as session:
            item = session.execute(
                select(ShiftChecklist).where(
                    ShiftChecklist.date_str == date_str,
                    ShiftChecklist.shift_num == shift_num,
                    ShiftChecklist.item_key == item_key.value,
                )
            ).scalar_one_or_none()
            if not item:
                item = ShiftChecklist(
                    date_str=date_str,
                    shift_num=shift_num,
                    item_key=item_key.value,
                )
                session.add(item)
            item.status = status.value
            item.reason = reason.strip() if reason else None
            item.updated_at_utc = datetime.datetime.utcnow()
            session.commit()
