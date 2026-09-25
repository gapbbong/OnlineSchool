from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_roles
from app.models import UserRole
from app.schemas.handover import WorkHandoverCreateRequest, WorkHandoverResponse, WorkHandoverTransferRequest
from app.services import handover_service

router = APIRouter()

_HANDOVER_MANAGE_ROLES = (UserRole.SCHOOL_ADMIN, UserRole.DEPARTMENT_HEAD)


@router.get("/work-handovers", response_model=List[WorkHandoverResponse])
async def list_work_handovers(
    department_id: Optional[str] = Query(None),
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """업무 인수인계 현황 조회 (담당업무별 현재 담당자 + Drive 폴더 + 인수인계 메모)."""
    return await handover_service.list_handovers(db, current.school_id, department_id)


@router.post("/work-handovers", response_model=WorkHandoverResponse, status_code=201)
async def create_work_handover(
    req: WorkHandoverCreateRequest,
    current: CurrentUser = Depends(require_roles(*_HANDOVER_MANAGE_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """담당업무 단위 인수인계 항목 생성. 부서/학교 Drive 루트 폴더가 있으면 업무 전용
    하위 폴더 생성을 비동기로 함께 요청한다."""
    return await handover_service.create_handover(db, current.school_id, current.user_id, req)


@router.post("/work-handovers/{handover_id}/handover", response_model=WorkHandoverResponse)
async def transfer_work_handover(
    handover_id: str,
    req: WorkHandoverTransferRequest,
    current: CurrentUser = Depends(require_roles(*_HANDOVER_MANAGE_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """담당자를 새 교사로 이관. Drive 폴더는 그대로 유지되고, 인수인계 메모에 이번
    인계 기록이 맨 위에 추가되어 다음 담당자가 이전 이력을 그대로 이어받는다."""
    return await handover_service.transfer_handover(db, current.school_id, current.user_id, handover_id, req)
