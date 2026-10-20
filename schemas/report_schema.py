"""
Schemas for Daily Metrics and Shift Report Generation.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from schemas.shift_schema import ChecklistItemSchema


class MetricsDataSchema(BaseModel):
    """Raw and verified metrics for a work shift."""
    messages_replied: int = 0
    slow_network_count: int = 0
    slow_network_devices: str = "không có" # e.g. "PC-04, May 12" or "không có"
    customers_tested: int = 0
    feedback_count: int = 0
    tickets_opened: int = 0
    tickets_closed: int = 0
    escalate_count: int = 0
    escalate_details: str = "không có" # e.g. "Dương: Khách lỗi mạng sâu" or "không có"
    
    # Handover
    pending_cases_desc: str = "không có"
    follow_up_count: int = 0
    follow_up_desc: str = "không có"
    
    # Ca 3 specific
    best_positive_feedback: Optional[str] = "không có"
    manager_review_issues: Optional[str] = "không có"
    
    # Audit & verification tracking
    unverified_count: int = 0
    evidence_items: List[str] = Field(default_factory=list)


class ShiftReportPayload(BaseModel):
    """Data required to generate the formatted final report."""
    date_str: str # YYYY-MM-DD
    shift_num: int # 1, 2, 3
    employee_name: str
    checklists: List[ChecklistItemSchema]
    metrics: MetricsDataSchema
