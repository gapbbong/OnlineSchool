import pytest

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_usage_event_logging_and_summary(client):
    hong = await auth_headers("hong@kse.hs.kr")

    for event_type in ["VIEW_CALENDAR_WEEK", "VIEW_CALENDAR_WEEK", "VIEW_MESSAGES"]:
        res = await client.post("/api/v1/analytics/events", json={"event_type": event_type}, headers=hong)
        assert res.status_code == 204

    # 같은 제목의 업무를 반복 등록해 "반복 업무 후보" 집계를 검증한다.
    for _ in range(3):
        task_res = await client.post(
            "/api/v1/tasks",
            json={"title": "주간 회의", "start_datetime": "2026-09-24T09:00:00", "due_datetime": "2026-09-28T09:00:00"},
            headers=hong,
        )
        assert task_res.status_code == 201

    summary_res = await client.get("/api/v1/analytics/summary", headers=hong)
    assert summary_res.status_code == 200
    summary = summary_res.json()

    event_map = {e["event_type"]: e["count"] for e in summary["event_counts"]}
    assert event_map["VIEW_CALENDAR_WEEK"] == 2
    assert event_map["VIEW_MESSAGES"] == 1

    repeated = {t["title"]: t["count"] for t in summary["top_repeated_task_titles"]}
    assert repeated.get("주간 회의") == 3

    assert summary["total_tasks"] >= 3
    assert any(d["weekday"] == "월" and d["count"] >= 3 for d in summary["tasks_by_weekday"])


@pytest.mark.asyncio
async def test_analytics_summary_requires_admin_role(client):
    teacher_headers = await auth_headers("kim@kse.hs.kr")
    res = await client.get("/api/v1/analytics/summary", headers=teacher_headers)
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_anonymous_events_are_ignored_without_error(client):
    res = await client.post("/api/v1/analytics/events", json={"event_type": "VIEW_DASHBOARD"})
    assert res.status_code == 204
