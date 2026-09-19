import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.asyncio
async def test_root():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

@pytest.mark.asyncio
async def test_dashboard_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "school_name" in data
    assert "today_tasks" in data
    assert "shortcuts" in data
    assert "today_timetables" in data
    assert "recent_messages" in data
    assert len(data["shortcuts"]) >= 3
