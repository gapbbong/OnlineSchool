import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import School
from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_dashboard_resolves_school_by_subdomain_header(client):
    """서브도메인 그라운드워크: X-School-Subdomain 헤더가 School.subdomain과 매칭되면
    익명 요청도 해당 학교로 스코프되어야 하고, 헤더가 없으면 기존 기본 데모 학교
    동작(첫 번째 활성 학교)이 그대로 유지되어야 한다 (회귀 방지)."""
    admin_headers = await auth_headers("platform-admin@kse.hs.kr")

    provision_res = await client.post(
        "/api/v1/admin/schools",
        json={"name": "서브도메인테스트고", "code": "SUBDOMAIN_HS", "workspace_domain": "subdomain-test.hs.kr"},
        headers=admin_headers,
    )
    assert provision_res.status_code == 201
    other_school_id = provision_res.json()["school_id"]

    # 학교 생성 API에는 서브도메인 필드가 없으므로(범위 밖), DB에 직접 설정한다.
    async with AsyncSessionLocal() as db:
        school = await db.get(School, other_school_id)
        school.subdomain = "subdomaintest"
        await db.commit()

    # 서브도메인 헤더로 요청하면 새로 만든 학교의 이름이 돌아와야 한다.
    subdomain_res = await client.get(
        "/api/v1/dashboard", headers={"X-School-Subdomain": "subdomaintest"}
    )
    assert subdomain_res.status_code == 200
    assert subdomain_res.json()["school_name"] == "서브도메인테스트고"

    # 헤더 없이(기존 방식) 요청하면 기본 데모 학교(KSE)가 그대로 반환되어야 한다.
    default_res = await client.get("/api/v1/dashboard")
    assert default_res.status_code == 200
    assert default_res.json()["school_name"] != "서브도메인테스트고"

    async with AsyncSessionLocal() as db:
        res = await db.execute(select(School).filter(School.is_active == True).order_by(School.created_at.asc()))
        default_school = res.scalars().first()
        assert default_res.json()["school_name"] == default_school.name


@pytest.mark.asyncio
async def test_dashboard_falls_back_when_subdomain_unrecognized(client):
    """인식되지 않는 서브도메인은 에러 없이 기본 데모 동작으로 폴백해야 한다."""
    res = await client.get(
        "/api/v1/dashboard", headers={"X-School-Subdomain": "no-such-school-subdomain"}
    )
    assert res.status_code == 200
