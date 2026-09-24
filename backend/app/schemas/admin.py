from typing import List, Optional

from pydantic import BaseModel, Field


class SchoolCreateRequest(BaseModel):
    """신규 학교 온보딩 요청 (SUPER_ADMIN 전용).

    학교마다 학제(중/고 3개 학년, 초등 6개 학년 등)와 부서 구성이 다를 수 있어
    grade_count/department_names를 선택적으로 재정의할 수 있게 했다."""
    name: str
    code: str = Field(..., min_length=2, max_length=50)
    workspace_domain: str = Field(..., description="예: kse.hs.kr (Google Workspace 도메인)")
    google_drive_root_folder_id: Optional[str] = None
    google_client_id: Optional[str] = None
    grade_count: int = Field(3, ge=1, le=6, description="학교급에 맞는 학년 수 (초등 6 / 중고 3 등)")
    academic_year: Optional[int] = Field(None, description="비워두면 현재 연도로 시작")
    department_names: Optional[List[str]] = Field(
        default=None,
        description="비워두면 마스터플랜 기본 부서 템플릿(교무부/연구부/학생부 등)을 사용",
    )


class SchoolCreateResponse(BaseModel):
    school_id: str
    name: str
    workspace_domain: str
    grades_created: int
    departments_created: int
    drive_sync_jobs_enqueued: int
    message: str


class GradeClassCount(BaseModel):
    grade_number: int
    class_count: int


class AcademicYearStructureResponse(BaseModel):
    academic_year: int
    grades: List[GradeClassCount]


class AcademicYearTransitionRequest(BaseModel):
    """새 학년도 전환 요청. grade_class_counts를 비우면 현재 학년도의 학년별 반 개수를
    그대로 복사해 새 학년도 구조를 만든다 (관리자가 그대로 확인만 하고 생성 가능)."""
    new_academic_year: int
    grade_class_counts: Optional[List[GradeClassCount]] = None


class AcademicYearTransitionResponse(BaseModel):
    previous_academic_year: int
    new_academic_year: int
    grades_created: int
    classes_created: int
    message: str


class SchoolSummaryResponse(BaseModel):
    """학교 확장 시 전체 현황을 한눈에 보기 위한 요약 정보."""
    school_id: str
    name: str
    code: str
    workspace_domain: str
    is_active: bool
    teacher_count: int
    department_count: int
    drive_configured: bool
    created_at: str
