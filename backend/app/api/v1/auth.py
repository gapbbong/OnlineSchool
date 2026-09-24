from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.models import School, Teacher, User
from app.schemas.auth import CurrentUserResponse, GoogleLoginRequest, PasswordLoginRequest
from app.schemas.domain import Token
from app.services.auth_service import authenticate_with_google, authenticate_with_password

router = APIRouter()


def _build_token(user: User, teacher: Teacher, school: School, access_token: str) -> Token:
    return Token(
        access_token=access_token,
        token_type="bearer",
        user_info={
            "user_id": user.id,
            "school_id": school.id,
            "school_name": school.name,
            "email": user.email,
            "role": user.role.value,
            "name": teacher.name if teacher else None,
            "photo_url": teacher.photo_url if teacher else None,
        },
    )


@router.post("/auth/google/login", response_model=Token)
async def google_login(req: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    """Google Sign-In ID Token으로 로그인/최초 자동 가입.

    학교 도메인이 사전에 등록되어 있으면(멀티테넌트) 별도 승인 없이 교직원 계정이
    자동 생성되며, 앱 자체 세션 JWT를 발급한다.
    """
    user, teacher, school, access_token = await authenticate_with_google(db, req.id_token)
    return _build_token(user, teacher, school, access_token)


@router.post("/auth/password/login", response_model=Token)
async def password_login(req: PasswordLoginRequest, db: AsyncSession = Depends(get_db)):
    """이메일/비밀번호 로그인 (구글 워크스페이스를 쓰지 않는 학교용).

    계정은 자동 생성되지 않으며, 관리자가 교사 온보딩 시 초기 비밀번호를 설정해
    미리 만들어 둔 계정만 로그인할 수 있다."""
    user, teacher, school, access_token = await authenticate_with_password(db, req.email, req.password)
    return _build_token(user, teacher, school, access_token)


@router.get("/auth/me", response_model=CurrentUserResponse)
async def get_me(current: CurrentUser = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    school = await db.get(School, current.school_id)
    teacher = await db.get(Teacher, current.user_id)
    return CurrentUserResponse(
        user_id=current.user_id,
        school_id=current.school_id,
        school_name=school.name if school else "-",
        email=current.email,
        role=current.role.value,
        teacher_id=teacher.id if teacher else None,
        name=teacher.name if teacher else None,
        photo_url=teacher.photo_url if teacher else None,
    )
