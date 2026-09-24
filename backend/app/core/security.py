import datetime
from typing import Any, Optional

from jose import JWTError, jwt

from app.core.config import settings

TOKEN_TYPE = "bearer"


def create_access_token(claims: dict[str, Any], expires_minutes: Optional[int] = None) -> str:
    """앱 자체 JWT 발급 (Google ID Token과는 별개의 세션 토큰)."""
    expire_minutes = expires_minutes if expires_minutes is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    now = datetime.datetime.now(datetime.timezone.utc)
    to_encode = {
        **claims,
        "iat": now,
        "exp": now + datetime.timedelta(minutes=expire_minutes),
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
