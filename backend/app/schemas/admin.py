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
