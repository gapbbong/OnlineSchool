from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_roles
from app.models import UserRole
from app.schemas.admin import SchoolCreateRequest, SchoolCreateResponse
from app.services.school_provisioning_service import SchoolProvisioningService

router = APIRouter()


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
