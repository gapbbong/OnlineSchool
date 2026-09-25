from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class LogEventRequest(BaseModel):
    event_type: str
    metadata: Optional[Dict[str, Any]] = None


class EventCount(BaseModel):
    event_type: str
    count: int


class DepartmentTaskCount(BaseModel):
    department_name: str
    count: int


class StatusCount(BaseModel):
    status: str
    count: int


class PriorityCount(BaseModel):
    priority: str
    count: int


class TitleFrequency(BaseModel):
    title: str
    count: int


class WeekdayCount(BaseModel):
    weekday: str
    count: int


class AnalyticsSummaryResponse(BaseModel):
    total_events: int
    total_tasks: int
    event_counts: List[EventCount]
    tasks_by_department: List[DepartmentTaskCount]
    tasks_by_status: List[StatusCount]
    tasks_by_priority: List[PriorityCount]
    top_repeated_task_titles: List[TitleFrequency]
    tasks_by_weekday: List[WeekdayCount]
