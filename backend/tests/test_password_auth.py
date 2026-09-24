import pytest

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_password_login_works_after_onboarding_with_initial_password(client):
    admin_headers = await auth_headers("hong@kse.hs.kr")
    meta_res = await client.get("/api/v1/schools/meta")
    dept_id = meta_res.json()["departments"][0]["id"]

    onboard_res = await client.post(
        "/api/v1/teachers/onboarding",
        json={
            "name": "비번교사",
            "phone_number": "010-5555-6666",
            "workspace_email": "pwteacher@kse.hs.kr",
            "department_id": dept_id,
            "role": "TEACHER",
            "initial_password": "Sup3rSecret!",
        },
        headers=admin_headers,
    )
    assert onboard_res.status_code == 200

    login_res = await client.post(
        "/api/v1/auth/password/login",
        json={"email": "pwteacher@kse.hs.kr", "password": "Sup3rSecret!"},
    )
    assert login_res.status_code == 200
    body = login_res.json()
    assert body["user_info"]["email"] == "pwteacher@kse.hs.kr"
    assert body["user_info"]["role"] == "TEACHER"

    me_res = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me_res.status_code == 200
    assert me_res.json()["name"] == "비번교사"


@pytest.mark.asyncio
async def test_password_login_rejects_wrong_password_and_missing_account(client):
    admin_headers = await auth_headers("hong@kse.hs.kr")
    meta_res = await client.get("/api/v1/schools/meta")
    dept_id = meta_res.json()["departments"][0]["id"]

    await client.post(
        "/api/v1/teachers/onboarding",
        json={
            "name": "비번틀림교사",
            "phone_number": "010-7777-8888",
            "workspace_email": "wrongpw@kse.hs.kr",
            "department_id": dept_id,
            "role": "TEACHER",
            "initial_password": "CorrectPassword1",
        },
        headers=admin_headers,
    )

    wrong_res = await client.post(
        "/api/v1/auth/password/login",
        json={"email": "wrongpw@kse.hs.kr", "password": "WrongPassword"},
    )
    assert wrong_res.status_code == 401

    no_account_res = await client.post(
        "/api/v1/auth/password/login",
        json={"email": "nobody@kse.hs.kr", "password": "whatever"},
    )
    assert no_account_res.status_code == 401
    # 존재하지 않는 계정과 비밀번호 오류가 같은 메시지를 반환해야 한다 (계정 존재 여부 노출 방지).
    assert wrong_res.json()["detail"] == no_account_res.json()["detail"]

    # 구글 로그인으로만 만들어진 계정(초기 비밀번호 없음)은 비밀번호 로그인이 거부되어야 한다.
    no_password_res = await client.post(
        "/api/v1/auth/password/login",
        json={"email": "hong@kse.hs.kr", "password": "anything"},
    )
    assert no_password_res.status_code == 401
