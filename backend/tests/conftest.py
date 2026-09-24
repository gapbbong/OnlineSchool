import asyncio

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from app.main import app
from app.core.database import AsyncSessionLocal
from app.core.security import create_access_token
from app.init_db import init_db
from app.models import User


@pytest.fixture(scope="session", autouse=True)
def _seed_database():
    """테스트 세션 시작 시 DB를 한 번 초기화/시드한다. 각 테스트가 DB를 공유하므로
    (별도 트랜잭션 롤백 없음) 테스트는 서로 다른 이메일/도메인을 사용해 독립적으로 작성한다."""
    asyncio.run(init_db())


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def auth_headers(email: str) -> dict:
    """시드 데이터(app/init_db.py)에 존재하는 계정 이메일로 앱 세션 JWT를 즉시 발급한다.
    Google 로그인 자체(서명 검증)는 test_auth.py에서 별도로 검증하므로, 다른 테스트에서는
    이 헬퍼로 인증된 상태를 빠르게 만든다."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).filter(User.email == email))
        user = result.scalars().first()
        if not user:
            raise RuntimeError(
                f"시드 계정을 찾을 수 없습니다: {email} (먼저 `python -m app.init_db` 실행 필요)"
            )
        token = create_access_token({
            "sub": user.id,
            "school_id": user.school_id,
            "role": user.role.value,
            "email": user.email,
            "teacher_id": user.id,
        })
    return {"Authorization": f"Bearer {token}"}
