from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User, UserRole

# auto_error=False -> 토큰이 없을 때 즉시 401을 던지지 않고, 선택적 인증 의존성에서
# "비로그인 상태"를 직접 판단할 수 있게 한다 (읽기 전용 데모 엔드포인트 호환).
_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    user_id: str
    school_id: str
    email: str
    role: UserRole
    teacher_id: Optional[str] = None


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[CurrentUser]:
    if credentials is None:
        return None

    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    user = await db.get(User, user_id)
    # 토큰 발급 이후 계정이 비활성화/삭제된 경우 등 모든 엣지케이스를 안전하게 거부한다.
    if not user or not user.is_active:
        return None

    return CurrentUser(
        user_id=user.id,
        school_id=user.school_id,
        email=user.email,
        role=user.role,
        teacher_id=payload.get("teacher_id"),
    )


async def get_current_user(
    current: Optional[CurrentUser] = Depends(get_current_user_optional),
) -> CurrentUser:
    if current is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current


def require_roles(*allowed_roles: UserRole):
    """지정된 역할 이상만 접근 가능하도록 제한하는 RBAC 의존성 팩토리.
    SUPER_ADMIN은 모든 학교 리소스에 대해 항상 접근 가능하다."""

    async def _dependency(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if current.role == UserRole.SUPER_ADMIN:
            return current
        if current.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="이 작업을 수행할 권한이 없습니다.",
            )
        return current

    return _dependency
