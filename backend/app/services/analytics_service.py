from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Department, Task, UsageEvent
from app.schemas.analytics import (
    AnalyticsSummaryResponse, DepartmentTaskCount, EventCount, PriorityCount,
    StatusCount, TitleFrequency, WeekdayCount,
)

_WEEKDAY_NAMES = ["월", "화", "수", "목", "금", "토", "일"]


async def log_event(
    db: AsyncSession, school_id: str, teacher_id: Optional[str], event_type: str, metadata: Optional[Dict[str, Any]]
) -> None:
    """기능 사용 로그 1건 적재. 분석 자체가 목적이므로 실패해도 조용히 무시하고
    호출부(요청 처리 흐름)에 절대 영향을 주지 않는다."""
    try:
        db.add(UsageEvent(school_id=school_id, teacher_id=teacher_id, event_type=event_type, metadata_json=metadata or {}))
        await db.commit()
    except Exception:
        await db.rollback()


async def get_summary(db: AsyncSession, school_id: str) -> AnalyticsSummaryResponse:
    ev_res = await db.execute(
        select(UsageEvent.event_type, func.count())
        .filter(UsageEvent.school_id == school_id)
        .group_by(UsageEvent.event_type)
        .order_by(func.count().desc())
    )
    event_counts = [EventCount(event_type=et, count=c) for et, c in ev_res.all()]

    dept_res = await db.execute(
        select(Department.name, func.count(Task.id))
        .join(Task, Task.department_id == Department.id)
        .filter(Task.school_id == school_id)
        .group_by(Department.name)
        .order_by(func.count(Task.id).desc())
    )
    tasks_by_department = [DepartmentTaskCount(department_name=n, count=c) for n, c in dept_res.all()]

    status_res = await db.execute(
        select(Task.status, func.count()).filter(Task.school_id == school_id).group_by(Task.status)
    )
    tasks_by_status = [StatusCount(status=s.value, count=c) for s, c in status_res.all()]

    prio_res = await db.execute(
        select(Task.priority, func.count()).filter(Task.school_id == school_id).group_by(Task.priority)
    )
    tasks_by_priority = [PriorityCount(priority=p.value, count=c) for p, c in prio_res.all()]

    # 같은 제목의 업무가 반복 등록될수록 "자동 반복 업무"로 만들면 좋은 후보다.
    title_res = await db.execute(
        select(func.trim(Task.title), func.count())
        .filter(Task.school_id == school_id)
        .group_by(func.trim(Task.title))
        .order_by(func.count().desc())
        .limit(10)
    )
    top_repeated_task_titles = [TitleFrequency(title=t, count=c) for t, c in title_res.all() if c > 1]

    weekday_res = await db.execute(
        select(Task.due_datetime).filter(Task.school_id == school_id, Task.due_datetime.isnot(None))
    )
    weekday_counter = {name: 0 for name in _WEEKDAY_NAMES}
    for (due,) in weekday_res.all():
        weekday_counter[_WEEKDAY_NAMES[due.weekday()]] += 1
    tasks_by_weekday = [WeekdayCount(weekday=n, count=weekday_counter[n]) for n in _WEEKDAY_NAMES]

    total_tasks = (await db.execute(select(func.count()).select_from(Task).filter(Task.school_id == school_id))).scalar_one()

    return AnalyticsSummaryResponse(
        total_events=sum(e.count for e in event_counts),
        total_tasks=total_tasks,
        event_counts=event_counts,
        tasks_by_department=tasks_by_department,
        tasks_by_status=tasks_by_status,
        tasks_by_priority=tasks_by_priority,
        top_repeated_task_titles=top_repeated_task_titles,
        tasks_by_weekday=tasks_by_weekday,
    )
