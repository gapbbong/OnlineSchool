import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import SyncOutbox, SyncOutboxStatus
from app.services.sync_queue import process_pending
from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_work_handover_create_enqueues_drive_folder_and_transfer_appends_note(client):
    admin_headers = await auth_headers("hong@kse.hs.kr")

    meta_res = await client.get("/api/v1/schools/meta")
    dept_id = meta_res.json()["departments"][0]["id"]

    me_hong = (await client.get("/api/v1/auth/me", headers=admin_headers)).json()
    me_kim = (await client.get("/api/v1/auth/me", headers=await auth_headers("kim@kse.hs.kr"))).json()

    create_res = await client.post(
        "/api/v1/work-handovers",
        json={
            "work_title": "방과후학교 담당",
            "department_id": dept_id,
            "current_teacher_id": me_hong["teacher_id"],
            "handover_note": "최초 등록",
        },
        headers=admin_headers,
    )
    assert create_res.status_code == 201
    handover = create_res.json()
    assert handover["current_teacher_name"] == "홍길동"

    # 학교 Drive 루트가 시드에 설정되어 있으므로 폴더 생성 작업이 큐에 적재되어야 한다.
    async with AsyncSessionLocal() as db:
        outbox_res = await db.execute(
            select(SyncOutbox).filter(SyncOutbox.entity_id == handover["id"], SyncOutbox.entity_type == "WORK_HANDOVER")
        )
        outbox_item = outbox_res.scalars().first()
        assert outbox_item is not None
        assert outbox_item.status == SyncOutboxStatus.PENDING

        processed = await process_pending(db)
        assert processed >= 1

    # 처리 후 폴더 ID가 채워졌는지 목록 조회로 확인. 아직 실제 Google API 연동 전(목 응답)
    # 이므로 drive_folder_url은 일부러 비워둔다 - 클릭하면 404가 나는 가짜 링크를 보여주지
    # 않기 위함 (google_sync.MOCK_FOLDER_ID_PREFIX 참고).
    list_res = await client.get("/api/v1/work-handovers", headers=admin_headers)
    updated = next(h for h in list_res.json() if h["id"] == handover["id"])
    assert updated["drive_folder_id"] is not None
    assert updated["drive_folder_url"] is None

    # 담당자를 김철수로 인수인계
    transfer_res = await client.post(
        f"/api/v1/work-handovers/{handover['id']}/handover",
        json={"new_teacher_id": me_kim["teacher_id"], "note": "2학기부터 인계합니다."},
        headers=admin_headers,
    )
    assert transfer_res.status_code == 200
    transferred = transfer_res.json()
    assert transferred["current_teacher_name"] == "김철수"
    assert "홍길동 → 김철수" in transferred["handover_note"]
    assert "2학기부터 인계합니다." in transferred["handover_note"]
    assert "최초 등록" in transferred["handover_note"]  # 이전 메모 이력이 유지되어야 한다
    # 폴더는 담당자가 바뀌어도 그대로 유지되어야 한다 (인수인계의 핵심 포인트)
    assert transferred["drive_folder_id"] == updated["drive_folder_id"]


@pytest.mark.asyncio
async def test_work_handover_requires_admin_role(client):
    teacher_headers = await auth_headers("kim@kse.hs.kr")
    res = await client.post(
        "/api/v1/work-handovers", json={"work_title": "권한없음 테스트"}, headers=teacher_headers
    )
    assert res.status_code == 403
