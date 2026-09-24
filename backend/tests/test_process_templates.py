import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import AuditLog
from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_process_template_create_requires_admin_role(client):
    teacher_headers = await auth_headers("kim@kse.hs.kr")
    res = await client.post(
        "/api/v1/process-templates",
        json={"category": "구매품의", "title": "권한없음 테스트", "description": "설명"},
        headers=teacher_headers,
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_process_template_crud_and_audit_log(client):
    admin_headers = await auth_headers("hong@kse.hs.kr")
    teacher_headers = await auth_headers("kim@kse.hs.kr")

    meta_res = await client.get("/api/v1/schools/meta")
    dept_id = meta_res.json()["departments"][0]["id"]

    me_kim = (await client.get("/api/v1/auth/me", headers=teacher_headers)).json()

    create_res = await client.post(
        "/api/v1/process-templates",
        json={
            "category": "구매품의",
            "title": "소모품 구매 품의",
            "description": "1. 품의서 작성\n2. 행정실 제출\n3. 결재 후 구매",
            "department_id": dept_id,
            "required_items": "견적서, 품의서",
            "form_doc_url": "https://docs.google.com/document/d/example",
            "contact_teacher_id": me_kim["teacher_id"],
        },
        headers=admin_headers,
    )
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["title"] == "소모품 구매 품의"
    assert created["department_name"] is not None
    assert created["contact_teacher_name"] == "김철수"
    template_id = created["id"]

    # 감사 로그가 남아야 한다 (요구사항 변경 이력을 추적할 수 있어야 하는 것이 핵심 포인트).
    async with AsyncSessionLocal() as db:
        audit_res = await db.execute(
            select(AuditLog).filter(
                AuditLog.target_id == template_id, AuditLog.action == "CREATE_PROCESS_TEMPLATE"
            )
        )
        audit_row = audit_res.scalars().first()
        assert audit_row is not None
        assert audit_row.target_type == "PROCESS_TEMPLATE"

    # 모든 인증된 역할(교사 포함)이 목록을 조회할 수 있어야 한다 - 투명성이 핵심.
    list_res_teacher = await client.get("/api/v1/process-templates", headers=teacher_headers)
    assert list_res_teacher.status_code == 200
    assert any(t["id"] == template_id for t in list_res_teacher.json())

    # 카테고리 필터
    filtered_res = await client.get(
        "/api/v1/process-templates", params={"category": "구매품의"}, headers=teacher_headers
    )
    assert filtered_res.status_code == 200
    assert any(t["id"] == template_id for t in filtered_res.json())

    # 수정 - 필드가 바뀌고 이후 조회에 반영되어야 한다.
    update_res = await client.patch(
        f"/api/v1/process-templates/{template_id}",
        json={"description": "1. 새 품의서 양식 작성\n2. 행정실 제출", "required_items": "새 견적서"},
        headers=admin_headers,
    )
    assert update_res.status_code == 200
    updated = update_res.json()
    assert "새 품의서 양식" in updated["description"]
    assert updated["required_items"] == "새 견적서"
    assert updated["title"] == "소모품 구매 품의"  # 전달하지 않은 필드는 유지되어야 한다

    async with AsyncSessionLocal() as db:
        audit_res = await db.execute(
            select(AuditLog).filter(
                AuditLog.target_id == template_id, AuditLog.action == "UPDATE_PROCESS_TEMPLATE"
            )
        )
        assert audit_res.scalars().first() is not None

    list_res_after_update = await client.get("/api/v1/process-templates", headers=teacher_headers)
    refetched = next(t for t in list_res_after_update.json() if t["id"] == template_id)
    assert "새 품의서 양식" in refetched["description"]

    # 교사는 수정 권한이 없어야 한다.
    forbidden_update = await client.patch(
        f"/api/v1/process-templates/{template_id}", json={"title": "권한없음"}, headers=teacher_headers
    )
    assert forbidden_update.status_code == 403

    # 삭제
    delete_res = await client.delete(f"/api/v1/process-templates/{template_id}", headers=admin_headers)
    assert delete_res.status_code == 204

    async with AsyncSessionLocal() as db:
        audit_res = await db.execute(
            select(AuditLog).filter(
                AuditLog.target_id == template_id, AuditLog.action == "DELETE_PROCESS_TEMPLATE"
            )
        )
        assert audit_res.scalars().first() is not None

    list_res_after_delete = await client.get("/api/v1/process-templates", headers=teacher_headers)
    assert all(t["id"] != template_id for t in list_res_after_delete.json())
