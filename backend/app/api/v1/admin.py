from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_roles
from app.models import UserRole
from app.schemas.admin import (
    AcademicYearStructureResponse, AcademicYearTransitionRequest, AcademicYearTransitionResponse,
    SchoolCreateRequest, SchoolCreateResponse, SchoolSummaryResponse,
)
from app.services import academic_year_service
from app.services.school_provisioning_service import SchoolProvisioningService

router = APIRouter()

_SCHOOL_ADMIN_ROLES = (UserRole.SCHOOL_ADMIN,)


@router.post("/admin/schools", response_model=SchoolCreateResponse, status_code=201)
async def create_school(
    req: SchoolCreateRequest,
    current: CurrentUser = Depends(require_roles(UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """신규 학교 온보딩 (플랫폼 SUPER_ADMIN 전용).

    타 학교로의 확장을 코드 배포 없이 API 호출 한 번으로 처리하기 위한 엔드포인트.
    School/SchoolSetting/기본 학년/기본 부서를 자동 생성하고, Drive 루트 폴더가
    지정되어 있으면 부서별 폴더 생성 작업을 비동기 큐에 적재한다.
    """
    return await SchoolProvisioningService.provision_school(db, current.user_id, req)


@router.get("/admin/schools", response_model=List[SchoolSummaryResponse])
async def list_schools(
    current: CurrentUser = Depends(require_roles(UserRole.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """전체 학교 현황을 한 화면에서 파악하기 위한 목록 (플랫폼 SUPER_ADMIN 전용)."""
    return await SchoolProvisioningService.list_schools(db)


@router.get("/admin/academic-year/structure", response_model=AcademicYearStructureResponse)
async def get_current_academic_year_structure(
    current: CurrentUser = Depends(require_roles(*_SCHOOL_ADMIN_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """새 학년도 전환 마법사의 기본값으로 쓸 현재 학년도의 학년별 반 개수."""
    return await academic_year_service.get_current_structure(db, current.school_id)


@router.post("/admin/academic-year/transition", response_model=AcademicYearTransitionResponse, status_code=201)
async def transition_academic_year(
    req: AcademicYearTransitionRequest,
    current: CurrentUser = Depends(require_roles(*_SCHOOL_ADMIN_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """새 학년도 시작 (학교 관리자 전용).

    새 학년도용 Grade/Class를 생성한다 (반 개수를 지정하지 않으면 현재 학년도 구조를
    그대로 복사). 이전 학년도 데이터는 손대지 않고 그대로 이력으로 남으며, 담임/시간표는
    관리자가 별도로 새로 배정해야 한다 (자동 승계하지 않음 - 매년 새로 정해지는 것이
    일반적이라 실수로 잘못 승계되는 것을 막기 위함)."""
    return await academic_year_service.transition_academic_year(db, current.school_id, current.user_id, req)
