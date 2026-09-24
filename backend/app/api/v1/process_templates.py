from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, require_roles
from app.models import UserRole
from app.schemas.process_template import (
    ProcessTemplateCreateRequest,
    ProcessTemplateResponse,
    ProcessTemplateUpdateRequest,
)
from app.services import process_template_service

router = APIRouter()

_TEMPLATE_MANAGE_ROLES = (UserRole.SCHOOL_ADMIN, UserRole.DEPARTMENT_HEAD)


@router.get("/process-templates", response_model=List[ProcessTemplateResponse])
async def list_process_templates(
    category: Optional[str] = Query(None),
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """표준 업무 처리 절차 및 품의 양식 목록 조회. 행정실 등의 요구사항이 담당자에
    따라 제멋대로 바뀐다는 불만을 없애기 위한 것이므로, 역할과 무관하게 로그인한
    모든 교직원에게 열려 있다 (투명성이 핵심 목적)."""
    return await process_template_service.list_templates(db, current.school_id, category)


@router.post("/process-templates", response_model=ProcessTemplateResponse, status_code=201)
async def create_process_template(
    req: ProcessTemplateCreateRequest,
    current: CurrentUser = Depends(require_roles(*_TEMPLATE_MANAGE_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """표준 절차/양식 신규 등록 (관리자/부서장 전용). 생성 시점에 감사 로그를 남겨
    이후 "언제, 누가, 무엇을 바꿨는지" 추적할 수 있게 한다."""
    return await process_template_service.create_template(db, current.school_id, current.user_id, req)


@router.patch("/process-templates/{template_id}", response_model=ProcessTemplateResponse)
async def update_process_template(
    template_id: str,
    req: ProcessTemplateUpdateRequest,
    current: CurrentUser = Depends(require_roles(*_TEMPLATE_MANAGE_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """표준 절차/양식 수정 (관리자/부서장 전용). 무엇이 바뀌었는지 감사 로그에 남겨서
    교사들이 "요구사항이 최근에 바뀌었는지"를 확인할 수 있게 한다."""
    return await process_template_service.update_template(db, current.school_id, current.user_id, template_id, req)


@router.delete("/process-templates/{template_id}", status_code=204)
async def delete_process_template(
    template_id: str,
    current: CurrentUser = Depends(require_roles(*_TEMPLATE_MANAGE_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """표준 절차/양식 삭제 (관리자/부서장 전용)."""
    await process_template_service.delete_template(db, current.school_id, current.user_id, template_id)
