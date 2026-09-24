import datetime
from typing import List, Optional

from pydantic import BaseModel, model_validator


class MessageCreateRequest(BaseModel):
    msg_type: str  # ANNOUNCEMENT | DEPARTMENT | DIRECT
    target_department_id: Optional[str] = None
    recipient_ids: Optional[List[str]] = None  # DIRECT일 때 사용 (교사 id 목록)
    title: Optional[str] = None
    content: str
    linked_task_id: Optional[str] = None
    linked_timetable_id: Optional[str] = None

    @model_validator(mode="after")
    def _validate_targets(self):
        if self.msg_type == "DEPARTMENT" and not self.target_department_id:
            raise ValueError("부서 공지는 target_department_id가 필요합니다.")
        if self.msg_type == "DIRECT" and not self.recipient_ids:
            raise ValueError("개인 쪽지는 recipient_ids가 최소 1명 필요합니다.")
        if self.msg_type not in ("ANNOUNCEMENT", "DEPARTMENT", "DIRECT"):
            raise ValueError("msg_type은 ANNOUNCEMENT/DEPARTMENT/DIRECT 중 하나여야 합니다.")
        return self


class LinkedTaskSummary(BaseModel):
    id: str
    title: str
    due_datetime: Optional[datetime.datetime] = None
    status: str


class LinkedTimetableSummary(BaseModel):
    id: str
    day_of_week: str
    period: int
    subject_name: str
    room_name: Optional[str] = None
    practice_room_name: Optional[str] = None


class MessageDetailResponse(BaseModel):
    id: str
    sender_id: str
    sender_name: str
    msg_type: str
    target_department_id: Optional[str] = None
    target_department_name: Optional[str] = None
    title: Optional[str] = None
    content: str
    created_at: datetime.datetime
    is_read: bool = False
    linked_task: Optional[LinkedTaskSummary] = None
    linked_timetable: Optional[LinkedTimetableSummary] = None
