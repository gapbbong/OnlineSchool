from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.models import School, Teacher, User
from app.schemas.auth import CurrentUserResponse, GoogleLoginRequest
from app.schemas.domain import Token
from app.services.auth_service import authenticate_with_google

router = APIRouter()


@router.post("/auth/google/login", response_model=Token)
async def google_login(req: GoogleLoginRequest, db: AsyncSession = Depends(get_db)):
    """Google Sign-In ID Token으로 로그인/최초 자동 가입.

    학교 도메인이 사전에 등록되어 있으면(멀티테넌트) 별도 승인 없이 교직원 계정이
    자동 생성되며, 앱 자체 세션 JWT를 발급한다.
    """
    user, teacher, school, access_token = await authenticate_with_google(db, req.id_token)
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
