import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import School, SyncOutbox, SyncOutboxStatus
from app.services.sync_queue import process_pending
from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_task_crud_lifecycle_and_sync_outbox(client):
    headers = await auth_headers("hong@kse.hs.kr")

    create_res = await client.post(
        "/api/v1/tasks",
        json={
            "title": "테스트 업무",
            "description": "동기화 큐 검증용",
            "start_datetime": "2026-09-24T09:00:00",
            "due_datetime": "2026-09-24T17:00:00",
            "priority": "HIGH",
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    task = create_res.json()
    assert task["status"] == "PENDING"

    # 생성 직후 Sheets 동기화 아웃박스가 적재되어 있어야 한다 (비동기, 아직 처리 전).
    async with AsyncSessionLocal() as db:
        outbox_res = await db.execute(select(SyncOutbox).filter(SyncOutbox.entity_id == task["id"]))
        outbox_item = outbox_res.scalars().first()
        assert outbox_item is not None
        assert outbox_item.status == SyncOutboxStatus.PENDING

        processed = await process_pending(db)
        assert processed >= 1

        await db.refresh(outbox_item)
        assert outbox_item.status == SyncOutboxStatus.SUCCESS

    # 목록/수정 조회
    list_res = await client.get("/api/v1/tasks", headers=headers)
    assert any(t["id"] == task["id"] for t in list_res.json())

    update_res = await client.patch(
        f"/api/v1/tasks/{task['id']}", json={"status": "COMPLETED"}, headers=headers
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "COMPLETED"

    # 다른 교사는 본인이 만들지도, 담당자도 아닌 업무를 삭제할 수 없다.
    other_headers = await auth_headers("kim@kse.hs.kr")
    forbidden = await client.delete(f"/api/v1/tasks/{task['id']}", headers=other_headers)
    assert forbidden.status_code == 403

    delete_res = await client.delete(f"/api/v1/tasks/{task['id']}", headers=headers)
    assert delete_res.status_code == 204


@pytest.mark.asyncio
async def test_admin_school_provisioning_and_isolation(client):
    admin_headers = await auth_headers("platform-admin@kse.hs.kr")

    res = await client.post(
        "/api/v1/admin/schools",
        json={
            "name": "테스트고등학교",
            "code": "TEST_PROVISION_HS",
            "workspace_domain": "test-provision.hs.kr",
            "grade_count": 3,
        },
        headers=admin_headers,
    )
    assert res.status_code == 201
    body = res.json()
    assert body["departments_created"] == 8
    assert body["grades_created"] == 3

    async with AsyncSessionLocal() as db:
        school = await db.get(School, body["school_id"])
        assert school is not None
        assert school.workspace_domain == "test-provision.hs.kr"

    # 중복 도메인은 거부되어야 한다.
    dup_res = await client.post(
        "/api/v1/admin/schools",
        json={"name": "중복학교", "code": "DUP_HS", "workspace_domain": "test-provision.hs.kr"},
        headers=admin_headers,
    )
    assert dup_res.status_code == 400

    # 일반 교사는 신규 학교를 등록할 수 없다 (SUPER_ADMIN 전용).
    teacher_headers = await auth_headers("hong@kse.hs.kr")
    forbidden_res = await client.post(
        "/api/v1/admin/schools",
        json={"name": "권한없음학교", "code": "NOPERM_HS", "workspace_domain": "noperm.hs.kr"},
        headers=teacher_headers,
    )
    assert forbidden_res.status_code == 403

    # 학교 현황 목록에 방금 만든 학교가 통계와 함께 보여야 한다.
    list_res = await client.get("/api/v1/admin/schools", headers=admin_headers)
    assert list_res.status_code == 200
    listed = {s["workspace_domain"]: s for s in list_res.json()}
    assert "test-provision.hs.kr" in listed
    assert listed["test-provision.hs.kr"]["department_count"] == 8
    assert listed["test-provision.hs.kr"]["drive_configured"] is False

    forbidden_list = await client.get("/api/v1/admin/schools", headers=teacher_headers)
    assert forbidden_list.status_code == 403
