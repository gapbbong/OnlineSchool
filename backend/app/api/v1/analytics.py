from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user_optional, require_roles
from app.models import UserRole
from app.schemas.analytics import AnalyticsSummaryResponse, LogEventRequest
from app.services import analytics_service

router = APIRouter()


@router.post("/analytics/events", status_code=204)
async def log_usage_event(
    req: LogEventRequest,
    current: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """기능 사용 로그 적재 (fire-and-forget). 비로그인 상태에서는 학교 문맥이 없어
    기록하지 않는다. 실패해도 절대 예외를 올리지 않아 프런트 UX에 영향이 없다."""
    if current:
        await analytics_service.log_event(db, current.school_id, current.teacher_id, req.event_type, req.metadata)


@router.get("/analytics/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    current: CurrentUser = Depends(require_roles(UserRole.SCHOOL_ADMIN, UserRole.DEPARTMENT_HEAD)),
    db: AsyncSession = Depends(get_db),
):
    """기능 사용 빈도 + 업무 패턴(부서별/상태별/반복 업무/마감 요일)을 한 번에 보여준다.
    어떤 기능이 안 쓰이는지, 어떤 업무가 반복되는지 파악해 개선 우선순위를 잡는 용도."""
    return await analytics_service.get_summary(db, current.school_id)
