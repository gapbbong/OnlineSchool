import datetime
from typing import Any, Optional

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

TOKEN_TYPE = "bearer"

# 구글 워크스페이스를 쓰지 않는 학교를 위한 이메일/비밀번호 로그인.
# (passlib의 CryptContext는 최신 bcrypt와 버전 호환 문제가 있어 bcrypt를 직접 사용한다)
_BCRYPT_MAX_BYTES = 72


def hash_password(raw_password: str) -> str:
    truncated = raw_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(truncated, bcrypt.gensalt()).decode("utf-8")


def verify_password(raw_password: str, hashed_password: str) -> bool:
    try:
        truncated = raw_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(truncated, hashed_password.encode("utf-8"))
    except ValueError:
        return False


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
