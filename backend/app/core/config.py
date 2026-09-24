from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "온라인 교무실 (Online Faculty Hub)"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./online_school.db"
    
    # JWT & Security
    SECRET_KEY: str = "insecure_dev_secret_key_change_in_production_9f83a2"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Google OAuth (플랫폼 공용 클라이언트. 학교별로 SchoolSetting.google_client_id를
    # 별도 등록하면 해당 학교는 자체 OAuth 클라이언트를 우선 사용한다)
    GOOGLE_CLIENT_ID: Optional[str] = None

    # Google Workspace 비동기 동기화 큐 (Sheets/Drive) 워커 설정
    SYNC_WORKER_INTERVAL_SECONDS: int = 15
    SYNC_WORKER_BATCH_SIZE: int = 20
    SYNC_MAX_ATTEMPTS: int = 5

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
