from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
import datetime
from app.models.entities import UserRole, TeacherStatus, VisibilityScope, TaskPriority, TaskStatus, DayOfWeek, RoomType

# --- Auth & User ---
class Token(BaseModel):
    access_token: str
    token_type: str
    user_info: dict

class UserBase(BaseModel):
    email: str
    role: UserRole

# --- Teacher ---
class TeacherBase(BaseModel):
    name: str
    photo_url: Optional[str] = None
    phone_number: Optional[str] = None
    workspace_email: Optional[str] = None
    car_number: Optional[str] = None
    position: Optional[str] = None
    assigned_work: Optional[str] = None
    status: TeacherStatus = TeacherStatus.EMPLOYED
    phone_visibility: VisibilityScope = VisibilityScope.ALL_STAFF
    car_visibility: VisibilityScope = VisibilityScope.ADMIN_ONLY
    email_visibility: VisibilityScope = VisibilityScope.ALL_STAFF
    memo: Optional[str] = None

class TeacherResponse(TeacherBase):
    id: str
    school_id: str
    departments: List[str] = []
    homeroom_class_name: Optional[str] = None

    class Config:
        from_attributes = True

# --- Room ---
class RoomBase(BaseModel):
    room_name: str
    building: Optional[str] = None
    floor: Optional[int] = None
    room_type: RoomType = RoomType.GENERAL
    equipment: Optional[str] = None

class RoomResponse(RoomBase):
    id: str
    school_id: str

    class Config:
        from_attributes = True

# --- Timetable ---
class TimetableItemResponse(BaseModel):
    id: str
    day_of_week: DayOfWeek
    period: int
    subject_name: str
    teacher_name: str
    grade_number: int
    class_number: int
    room_name: Optional[str] = None
    practice_room_name: Optional[str] = None
    lesson_type: str

    class Config:
        from_attributes = True

# --- Task (1사분면) ---
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    department_id: Optional[str] = None
    assignee_id: Optional[str] = None
    start_datetime: datetime.datetime
    due_datetime: Optional[datetime.datetime] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    visibility: VisibilityScope = VisibilityScope.ALL_STAFF

class TaskResponse(TaskBase):
    id: str
    school_id: str
    creator_name: Optional[str] = None
    assignee_name: Optional[str] = None
    department_name: Optional[str] = None
    google_drive_folder_id: Optional[str] = None
    google_sheet_id: Optional[str] = None

    class Config:
        from_attributes = True

# --- Shortcut (2사분면) ---
class ShortcutResponse(BaseModel):
    id: str
    title: str
    url: str
    icon: str
    category: str
    sort_order: int

    class Config:
        from_attributes = True

# --- Message (4사분면) ---
class MessageResponse(BaseModel):
    id: str
    sender_name: str
    msg_type: str
    title: Optional[str] = None
    content: str
    created_at: datetime.datetime
    is_read: bool = False

    class Config:
        from_attributes = True

# --- 4분할 대시보드 통합 Aggregation 응답 ---
class DashboardSummaryResponse(BaseModel):
    school_name: str
    today_tasks: List[TaskResponse]
    shortcuts: List[ShortcutResponse]
    today_timetables: List[TimetableItemResponse]
    recent_messages: List[MessageResponse]
