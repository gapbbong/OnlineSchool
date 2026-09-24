import datetime
from typing import Optional

from pydantic import BaseModel


class WorkHandoverCreateRequest(BaseModel):
    work_title: str
    department_id: Optional[str] = None
    current_teacher_id: Optional[str] = None
    handover_note: Optional[str] = None


class WorkHandoverTransferRequest(BaseModel):
    new_teacher_id: str
    note: Optional[str] = None


class WorkHandoverResponse(BaseModel):
    id: str
    work_title: str
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    current_teacher_id: Optional[str] = None
    current_teacher_name: Optional[str] = None
    drive_folder_id: Optional[str] = None
    drive_folder_url: Optional[str] = None
    handover_note: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
