import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import Class, Grade
from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_transition_creates_new_year_and_preserves_old(client):
    admin_headers = await auth_headers("hong@kse.hs.kr")

    before_res = await client.get("/api/v1/admin/academic-year/structure", headers=admin_headers)
    assert before_res.status_code == 200
    before = before_res.json()
    assert before["academic_year"] == 2026
    assert before["grades"] == [{"grade_number": 3, "class_count": 1}]  # 시드 데이터 기준

    transition_res = await client.post(
        "/api/v1/admin/academic-year/transition",
        json={"new_academic_year": 2027},
        headers=admin_headers,
    )
    assert transition_res.status_code == 201
    body = transition_res.json()
    assert body["previous_academic_year"] == 2026
    assert body["new_academic_year"] == 2027
    assert body["grades_created"] == 1
    assert body["classes_created"] == 1

    # 새 학년도가 "현재 학년도"로 반영되어야 한다.
    after_res = await client.get("/api/v1/admin/academic-year/structure", headers=admin_headers)
    assert after_res.json()["academic_year"] == 2027

    # 이전 학년도(2026) 반 데이터는 삭제되지 않고 그대로 남아있어야 한다.
    async with AsyncSessionLocal() as db:
        old_grades = (await db.execute(select(Grade).filter(Grade.academic_year == 2026))).scalars().all()
        new_grades = (await db.execute(select(Grade).filter(Grade.academic_year == 2027))).scalars().all()
        assert len(old_grades) == 1
        assert len(new_grades) == 1
        assert old_grades[0].id != new_grades[0].id

        new_classes = (await db.execute(select(Class).filter(Class.grade_id == new_grades[0].id))).scalars().all()
        assert len(new_classes) == 1


@pytest.mark.asyncio
async def test_transition_rejects_non_increasing_year_and_custom_counts(client):
    admin_headers = await auth_headers("hong@kse.hs.kr")

    same_year_res = await client.post(
        "/api/v1/admin/academic-year/transition", json={"new_academic_year": 2026}, headers=admin_headers
    )
    assert same_year_res.status_code == 400

    custom_res = await client.post(
        "/api/v1/admin/academic-year/transition",
        json={"new_academic_year": 2028, "grade_class_counts": [{"grade_number": 1, "class_count": 4}, {"grade_number": 2, "class_count": 3}]},
        headers=admin_headers,
    )
    assert custom_res.status_code == 201
    body = custom_res.json()
    assert body["grades_created"] == 2
    assert body["classes_created"] == 7


@pytest.mark.asyncio
async def test_transition_requires_school_admin(client):
    teacher_headers = await auth_headers("kim@kse.hs.kr")
    res = await client.post(
        "/api/v1/admin/academic-year/transition", json={"new_academic_year": 2099}, headers=teacher_headers
    )
    assert res.status_code == 403
