from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

if "sqlite" in settings.DATABASE_URL:
    _connect_args = {"check_same_thread": False}
elif "asyncpg" in settings.DATABASE_URL:
    # Supabase 등 pgbouncer 트랜잭션 풀러 앞단에서는 서버 사이드 prepared statement
    # 캐시가 "prepared statement ... already exists" 오류를 일으킬 수 있어 끈다.
    _connect_args = {"statement_cache_size": 0}
else:
    _connect_args = {}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
