import pytest
from sqlalchemy import select

import app.services.auth_service as auth_service
from app.core.database import AsyncSessionLocal
from app.models import Teacher, TeacherStatus, User

# Google 서명 검증 자체(google-auth 라이브러리 내부)는 신뢰하고, 우리 비즈니스 로직
# (테넌트 해석 / 자동 프로비저닝 / RBAC 발급)만 테스트하기 위해 verify_google_id_token만
# 가짜 클레임으로 대체한다.


def _fake_claims(email: str, hd: str = "kse.hs.kr", name: str = "테스트유저", verified: bool = True):
    return {"email": email, "email_verified": verified, "hd": hd, "name": name, "picture": None, "aud": "test-client"}


@pytest.mark.asyncio
async def test_google_login_existing_user(client, monkeypatch):
    monkeypatch.setattr(auth_service, "verify_google_id_token", lambda t: _fake_claims("hong@kse.hs.kr"))

    res = await client.post("/api/v1/auth/google/login", json={"id_token": "fake"})
    assert res.status_code == 200
    data = res.json()
    assert data["user_info"]["role"] == "SCHOOL_ADMIN"
    assert data["user_info"]["school_name"] == "한국과학기술고등학교"

    me_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "hong@kse.hs.kr"


@pytest.mark.asyncio
async def test_google_login_auto_provisions_new_teacher(client, monkeypatch):
    new_email = "newbie-auto@kse.hs.kr"
    monkeypatch.setattr(
        auth_service, "verify_google_id_token", lambda t: _fake_claims(new_email, name="새내기 선생님")
    )

    res = await client.post("/api/v1/auth/google/login", json={"id_token": "fake"})
    assert res.status_code == 200
    data = res.json()
    assert data["user_info"]["role"] == "TEACHER"
    assert data["user_info"]["name"] == "새내기 선생님"

    async with AsyncSessionLocal() as db:
        user_res = await db.execute(select(User).filter(User.email == new_email))
        user = user_res.scalars().first()
        assert user is not None
        teacher = await db.get(Teacher, user.id)
        assert teacher is not None
        assert teacher.name == "새내기 선생님"


@pytest.mark.asyncio
async def test_google_login_rejects_unregistered_domain(client, monkeypatch):
    monkeypatch.setattr(
        auth_service, "verify_google_id_token",
        lambda t: _fake_claims("someone@not-registered-school.kr", hd="not-registered-school.kr"),
    )
    res = await client.post("/api/v1/auth/google/login", json={"id_token": "fake"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_google_login_rejects_unverified_email(client, monkeypatch):
    monkeypatch.setattr(
        auth_service, "verify_google_id_token", lambda t: _fake_claims("hong@kse.hs.kr", verified=False)
    )
    res = await client.post("/api/v1/auth/google/login", json={"id_token": "fake"})
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_google_login_rejects_retired_teacher(client, monkeypatch):
    async with AsyncSessionLocal() as db:
        user_res = await db.execute(select(User).filter(User.email == "kim@kse.hs.kr"))
        user = user_res.scalars().first()
        teacher = await db.get(Teacher, user.id)
        teacher.status = TeacherStatus.RETIRED
        await db.commit()

    try:
        monkeypatch.setattr(auth_service, "verify_google_id_token", lambda t: _fake_claims("kim@kse.hs.kr"))
        res = await client.post("/api/v1/auth/google/login", json={"id_token": "fake"})
        assert res.status_code == 403
    finally:
        async with AsyncSessionLocal() as db:
            user_res = await db.execute(select(User).filter(User.email == "kim@kse.hs.kr"))
            user = user_res.scalars().first()
            teacher = await db.get(Teacher, user.id)
            teacher.status = TeacherStatus.EMPLOYED
            await db.commit()
