import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import Teacher, TeacherStatus, User, UserRole
from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_teacher_timetable_blocks_cross_school_access_even_when_anonymous(client):
    """IDOR 회귀 테스트: KSE(기본 데모 학교)가 아닌 다른 학교 소속 교사의 시간표는,
    로그인 없이도(익명 요청) 조회할 수 없어야 한다. 이전에는 `current`가 None일 때
    school_id 검사 자체가 건너뛰어져 어떤 학교의 교사든 조회가 가능했다."""
    admin_headers = await auth_headers("platform-admin@kse.hs.kr")

    provision_res = await client.post(
        "/api/v1/admin/schools",
        json={"name": "격리테스트고", "code": "ISOLATION_HS", "workspace_domain": "isolation-test.hs.kr"},
        headers=admin_headers,
    )
    assert provision_res.status_code == 201
    other_school_id = provision_res.json()["school_id"]

    # 다른 학교 소속 교사를 DB에 직접 생성 (해당 학교 전용 관리자 계정이 없으므로 온보딩
    # API 대신 직접 삽입 - 엔드포인트 로직 자체를 검증하는 것이 목적).
    async with AsyncSessionLocal() as db:
        other_user = User(school_id=other_school_id, email="isolated@isolation-test.hs.kr", role=UserRole.TEACHER)
        db.add(other_user)
        await db.flush()
        other_teacher = Teacher(id=other_user.id, school_id=other_school_id, name="격리교사")
        db.add(other_teacher)
        await db.commit()
        other_teacher_id = other_teacher.id

    # KSE가 기본 데모 학교이므로, 익명 요청으로 KSE 소속 교사를 조회하면 성공해야 한다
    # (기존 데모/부트스트랩 동작은 유지).
    kse_res = await db_first_kse_teacher_id()
    anon_kse_res = await client.get(f"/api/v1/timetables/teacher/{kse_res}")
    assert anon_kse_res.status_code == 200

    # 익명 요청으로 다른 학교(격리테스트고) 소속 교사를 조회하면 반드시 404여야 한다.
    anon_cross_res = await client.get(f"/api/v1/timetables/teacher/{other_teacher_id}")
    assert anon_cross_res.status_code == 404

    # 로그인한 사용자(KSE 소속)가 다른 학교 교사 id로 조회해도 404.
    kse_headers = await auth_headers("hong@kse.hs.kr")
    login_cross_res = await client.get(f"/api/v1/timetables/teacher/{other_teacher_id}", headers=kse_headers)
    assert login_cross_res.status_code == 404


async def db_first_kse_teacher_id() -> str:
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).filter(User.email == "hong@kse.hs.kr"))
        return res.scalars().first().id


@pytest.mark.asyncio
async def test_teacher_directory_enforces_same_dept_and_email_visibility(client):
    admin_headers = await auth_headers("hong@kse.hs.kr")
    meta_res = await client.get("/api/v1/schools/meta")
    depts = meta_res.json()["departments"]
    dept_a = depts[0]["id"]
    dept_b = depts[1]["id"] if len(depts) > 1 else depts[0]["id"]

    # 같은 부서에서만 공개되도록 설정한 교사 등록
    onboard_res = await client.post(
        "/api/v1/teachers/onboarding",
        json={
            "name": "부서공개교사",
            "phone_number": "010-1234-0000",
            "workspace_email": "deptvis@kse.hs.kr",
            "department_id": dept_a,
            "phone_visibility": "SAME_DEPT",
            "role": "TEACHER",
        },
        headers=admin_headers,
    )
    assert onboard_res.status_code == 200

    # 같은 부서(dept_a) 소속 교사를 하나 더 등록해 SAME_DEPT 조건을 만족시킨다.
    same_dept_res = await client.post(
        "/api/v1/teachers/onboarding",
        json={
            "name": "같은부서교사",
            "phone_number": "010-1234-1111",
            "workspace_email": "samedept@kse.hs.kr",
            "department_id": dept_a,
            "role": "TEACHER",
        },
        headers=admin_headers,
    )
    assert same_dept_res.status_code == 200

    same_dept_headers = await auth_headers("samedept@kse.hs.kr")

    list_as_same_dept = await client.get("/api/v1/teachers", headers=same_dept_headers)
    target = next(t for t in list_as_same_dept.json() if t["workspace_email"] == "deptvis@kse.hs.kr")
    assert target["phone_number"] == "010-1234-0000"  # 같은 부서라 공개됨

    # 다른 부서 소속 교사(김철수)는 SAME_DEPT 대상 교사의 번호를 볼 수 없어야 한다.
    kim_headers = await auth_headers("kim@kse.hs.kr")
    list_as_other_dept = await client.get("/api/v1/teachers", headers=kim_headers)
    target_for_kim = next(t for t in list_as_other_dept.json() if t["workspace_email"] == "deptvis@kse.hs.kr")
    assert target_for_kim["phone_number"] != "010-1234-0000"


@pytest.mark.asyncio
async def test_retired_teacher_excluded_from_directory(client):
    admin_headers = await auth_headers("hong@kse.hs.kr")

    async with AsyncSessionLocal() as db:
        kim_res = await db.execute(select(User).filter(User.email == "kim@kse.hs.kr"))
        kim_user = kim_res.scalars().first()
        teacher = await db.get(Teacher, kim_user.id)
        teacher.status = TeacherStatus.RETIRED
        await db.commit()

    try:
        list_res = await client.get("/api/v1/teachers", headers=admin_headers)
        assert all(t["workspace_email"] != "kim@kse.hs.kr" for t in list_res.json())
    finally:
        async with AsyncSessionLocal() as db:
            kim_res = await db.execute(select(User).filter(User.email == "kim@kse.hs.kr"))
            kim_user = kim_res.scalars().first()
            teacher = await db.get(Teacher, kim_user.id)
            teacher.status = TeacherStatus.EMPLOYED
            await db.commit()
