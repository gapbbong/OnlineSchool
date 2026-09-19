import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from app.models.entities import UserRole, VisibilityScope, DayOfWeek

# 신규 교사 온보딩 요청 DTO
class TeacherOnboardingRequest(BaseModel):
    # 1. 기본 정보
    name: str
    phone_number: str
    workspace_email: EmailStr
    car_number: Optional[str] = None
    
    # 개인정보 공개범위
    phone_visibility: VisibilityScope = VisibilityScope.ALL_STAFF
    car_visibility: VisibilityScope = VisibilityScope.ADMIN_ONLY
    
    # 2. 학교 정보
    department_id: str
    position: Optional[str] = "교과교사"
    assigned_work: Optional[str] = None
    
    # 3. 담임/부담임
    homeroom_grade: Optional[int] = None
    homeroom_class: Optional[int] = None
    
    # 4. 담당 과목 & 시간표 초기 배정 (선택)
    subject_id: Optional[str] = None
    timetable_slots: Optional[List[dict]] = []  # [{"day": "MON", "period": 1, "grade": 3, "class": 2, "room_id": "...", "practice_room_id": "..."}]
    
    # 5. 시스템 권한
    role: UserRole = UserRole.TEACHER
    
    # 6. Google Workspace & Drive 연동 옵션
    sync_google_drive: bool = True
    sync_google_sheets: bool = True

class TeacherOnboardingResponse(BaseModel):
    teacher_id: str
    user_id: str
    name: str
    workspace_email: str
    department_name: str
    role: str
    drive_folder_granted: bool
    sheets_access_granted: bool
    created_timetables_count: int
    message: str
