import pytest

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_teacher_onboarding_pipeline(client):
    # 1. 메타데이터 조회
    meta_res = await client.get("/api/v1/schools/meta")
    assert meta_res.status_code == 200
    meta = meta_res.json()
    assert len(meta["departments"]) > 0
    dept_id = meta["departments"][0]["id"]

    # 2. 신규 교사 온보딩 요청 (관리자 로그인 필요)
    headers = await auth_headers("hong@kse.hs.kr")
    payload = {
        "name": "박선생",
        "phone_number": "010-9999-8888",
        "workspace_email": "park@kse.hs.kr",
        "car_number": "33허 9999",
        "phone_visibility": "ALL_STAFF",
        "car_visibility": "ADMIN_ONLY",
        "department_id": dept_id,
        "position": "교과교사",
        "assigned_work": "진로상담",
        "role": "TEACHER",
        "sync_google_drive": True,
        "sync_google_sheets": True
    }
    onboard_res = await client.post("/api/v1/teachers/onboarding", json=payload, headers=headers)
    assert onboard_res.status_code == 200
    data = onboard_res.json()
    assert data["name"] == "박선생"
    assert data["workspace_email"] == "park@kse.hs.kr"
    assert data["drive_folder_granted"] is True


@pytest.mark.asyncio
async def test_teacher_onboarding_requires_admin_role(client):
    meta_res = await client.get("/api/v1/schools/meta")
    dept_id = meta_res.json()["departments"][0]["id"]

    # 일반 교사(TEACHER) 권한으로는 신규 교사 등록이 거부되어야 한다.
    headers = await auth_headers("kim@kse.hs.kr")
    payload = {
        "name": "테스트",
        "phone_number": "010-0000-0000",
        "workspace_email": "notallowed@kse.hs.kr",
        "department_id": dept_id,
        "role": "TEACHER",
    }
    res = await client.post("/api/v1/teachers/onboarding", json=payload, headers=headers)
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_teacher_onboarding_requires_login(client):
    meta_res = await client.get("/api/v1/schools/meta")
    dept_id = meta_res.json()["departments"][0]["id"]

    payload = {
        "name": "익명",
        "phone_number": "010-0000-0001",
        "workspace_email": "anon@kse.hs.kr",
        "department_id": dept_id,
        "role": "TEACHER",
    }
    res = await client.post("/api/v1/teachers/onboarding", json=payload)
    assert res.status_code == 401
