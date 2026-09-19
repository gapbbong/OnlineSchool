import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models import School, Department
from sqlalchemy import select
from app.core.database import AsyncSessionLocal

@pytest.mark.asyncio
async def test_teacher_onboarding_pipeline():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. 메타데이터 조회
        meta_res = await ac.get("/api/v1/schools/meta")
        assert meta_res.status_code == 200
        meta = meta_res.json()
        assert len(meta["departments"]) > 0
        dept_id = meta["departments"][0]["id"]
        
        # 2. 신규 교사 온보딩 요청
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
        onboard_res = await ac.post("/api/v1/teachers/onboarding", json=payload)
        assert onboard_res.status_code == 200
        data = onboard_res.json()
        assert data["name"] == "박선생"
        assert data["workspace_email"] == "park@kse.hs.kr"
        assert data["drive_folder_granted"] is True
