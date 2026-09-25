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

    # 최초 관리자 계정 (선택). 비워두면 학교만 생성되고 아무도 로그인할 수 없는 빈
    # 학교가 만들어지므로, 실제로는 이 세 값을 함께 입력하는 것을 강력히 권장한다.
    admin_name: Optional[str] = Field(None, description="학교 최초 관리자(교장/교감/교무부장 등) 이름")
    admin_email: Optional[str] = Field(
        None, description="관리자 로그인 이메일. workspace_domain과 도메인이 일치해야 함"
    )
    admin_initial_password: Optional[str] = Field(
        None, min_length=8, description="관리자 초기 비밀번호 (Google 로그인만 쓸 경우 비워둘 수 있음)"
    )


class SchoolCreateResponse(BaseModel):
    school_id: str
    name: str
    workspace_domain: str
    grades_created: int
    departments_created: int
    drive_sync_jobs_enqueued: int
    admin_email: Optional[str] = None
    admin_login_ready: bool = False
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
