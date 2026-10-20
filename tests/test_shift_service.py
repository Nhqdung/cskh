"""
Unit tests for ShiftService, timezone conversions, and shift boundary logic.
"""

import datetime
from zoneinfo import ZoneInfo
from services.shift_service import ShiftService, VN_TZ, UTC_TZ
from schemas.shift_schema import ChecklistItemKey, ChecklistStatus


def test_utc_and_local_conversion():
    # 07:00 VN time on 2026-10-20 is 00:00 UTC on 2026-10-20
    dt_local = datetime.datetime(2026, 10, 20, 7, 0, 0, tzinfo=VN_TZ)
    dt_utc = ShiftService.local_to_utc(dt_local)
    assert dt_utc.hour == 0
    assert dt_utc.day == 20

    # Back to local
    converted_back = ShiftService.utc_to_local(dt_utc)
    assert converted_back.hour == 7
    assert converted_back.day == 20


def test_shift_1_and_2_windows(test_db):
    w1 = ShiftService.get_shift_window("2026-10-20", 1)
    assert w1.start_local.hour == 7
    assert w1.end_local.hour == 15
    assert w1.start_local.day == 20
    assert w1.end_local.day == 20
    # In UTC (UTC+7)
    assert w1.start_utc.hour == 0
    assert w1.end_utc.hour == 8

    w2 = ShiftService.get_shift_window("2026-10-20", 2)
    assert w2.start_local.hour == 15
    assert w2.end_local.hour == 23


def test_shift_3_crosses_midnight(test_db):
    w3 = ShiftService.get_shift_window("2026-10-20", 3)
    assert w3.start_local.day == 20
    assert w3.start_local.hour == 23
    # Crosses to next day
    assert w3.end_local.day == 21
    assert w3.end_local.hour == 7

    # Check UTC
    assert w3.start_utc.day == 20
    assert w3.start_utc.hour == 16
    assert w3.end_utc.day == 21
    assert w3.end_utc.hour == 0


def test_boundary_resolution(test_db):
    # Exactly 14:59:59 is Ca 1
    t1 = datetime.datetime(2026, 10, 20, 14, 59, 59, tzinfo=VN_TZ)
    d1, s1 = ShiftService.resolve_shift_for_timestamp(t1)
    assert d1 == "2026-10-20"
    assert s1 == 1

    # Exactly 15:00:00 moves to Ca 2 [half-open interval [start, end))
    t2 = datetime.datetime(2026, 10, 20, 15, 0, 0, tzinfo=VN_TZ)
    d2, s2 = ShiftService.resolve_shift_for_timestamp(t2)
    assert d2 == "2026-10-20"
    assert s2 == 2

    # 02:30 AM on 2026-10-21 belongs to Ca 3 of 2026-10-20!
    t3 = datetime.datetime(2026, 10, 21, 2, 30, 0, tzinfo=VN_TZ)
    d3, s3 = ShiftService.resolve_shift_for_timestamp(t3)
    assert d3 == "2026-10-20"
    assert s3 == 3


def test_checklist_shift3_extra_item(test_db):
    # Ca 1 checklist has 6 items
    cl1 = ShiftService.get_or_create_checklist("2026-10-20", 1)
    keys1 = [item.item_key for item in cl1]
    assert len(keys1) == 6
    assert ChecklistItemKey.CLOSE_UNANSWERED_TICKETS_SHIFT3 not in keys1

    # Ca 3 checklist has 7 items
    cl3 = ShiftService.get_or_create_checklist("2026-10-20", 3)
    keys3 = [item.item_key for item in cl3]
    assert len(keys3) == 7
    assert ChecklistItemKey.CLOSE_UNANSWERED_TICKETS_SHIFT3 in keys3
