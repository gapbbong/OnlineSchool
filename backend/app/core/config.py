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
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
