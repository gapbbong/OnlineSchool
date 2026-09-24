import datetime
import logging
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.models import AuditLog, School, SchoolSetting, Teacher, TeacherStatus, User, UserRole

logger = logging.getLogger("AuthService")


def verify_google_id_token(id_token_str: str) -> dict[str, Any]:
    """Google ID Token 서명/만료 검증 후 클레임 반환.

    실제 Google 라이브러리 호출부를 별도 함수로 분리해 두어(테스트에서는 이 함수만
    monkeypatch), 학교별 OAuth 클라이언트가 달라도(aud 클레임) 동일한 검증 로직을
    재사용할 수 있게 한다. audience는 여기서 강제하지 않고 호출부(authenticate_with_google)
    에서 학교별 허용 클라이언트 목록과 비교한다 - 멀티테넌트 확장 시 학교마다 별도의
    Google Cloud OAuth 클라이언트를 쓸 수도, 플랫폼 공용 클라이언트를 공유할 수도 있어야
    하기 때문이다.
    """
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token as google_id_token
    except ImportError as exc:  # pragma: no cover - 의존성 누락은 배포 설정 문제
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google 인증 모듈이 설치되지 않았습니다.",
        ) from exc

    try:
        return google_id_token.verify_oauth2_token(id_token_str, google_requests.Request())
    except Exception as exc:
        logger.warning(f"[Google ID Token 검증 실패] {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 Google 인증 토큰입니다.",
        ) from exc


async def _resolve_school_by_domain(db: AsyncSession, domain: str) -> School:
    result = await db.execute(
        select(School).filter(
            func.lower(School.workspace_domain) == domain,
            School.is_active == True,  # noqa: E712
        )
    )
    school = result.scalars().first()
    if not school:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"'@{domain}' 도메인은 등록된 학교가 아닙니다. "
                "학교 관리자에게 온라인 교무실 등록을 요청하세요."
            ),
        )
    return school


def _check_client_audience(claims: dict[str, Any], school: School, school_setting: Optional[SchoolSetting]) -> None:
    allowed_client_ids = {
        cid for cid in [settings.GOOGLE_CLIENT_ID, getattr(school_setting, "google_client_id", None)] if cid
    }
    if not allowed_client_ids:
        # 아직 OAuth 클라이언트 ID가 설정되지 않은 초기 구축 단계 - 도메인 화이트리스트만으로 방어.
        return
    if claims.get("aud") not in allowed_client_ids:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="허용되지 않은 Google OAuth 클라이언트에서 발급된 토큰입니다.",
        )


async def authenticate_with_google(db: AsyncSession, id_token_str: str) -> tuple[User, Teacher, School, str]:
    claims = verify_google_id_token(id_token_str)

    email = (claims.get("email") or "").strip().lower()
    if not email or not claims.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일이 확인되지 않은 Google 계정입니다.",
        )

    # hd(Workspace hosted domain) 클레임이 있으면 우선 사용, 없으면(개인 Gmail 등) 이메일 도메인 사용.
    domain = (claims.get("hd") or email.split("@")[-1]).strip().lower()

    school = await _resolve_school_by_domain(db, domain)
    setting_result = await db.execute(select(SchoolSetting).filter(SchoolSetting.school_id == school.id))
    school_setting = setting_result.scalars().first()
    _check_client_audience(claims, school, school_setting)

    display_name = claims.get("name") or email.split("@")[0]
    photo_url = claims.get("picture")

    result = await db.execute(
        select(User).filter(User.school_id == school.id, func.lower(User.email) == email)
    )
    user = result.scalars().first()

    if user is not None:
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="비활성화된 계정입니다. 관리자에게 문의하세요.")

        teacher = await db.get(Teacher, user.id)
        if teacher is not None and teacher.status == TeacherStatus.RETIRED:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="퇴직 처리된 계정입니다. 관리자에게 문의하세요.")

        if teacher is None:
            # 데이터 불일치(예: 관리자가 User만 먼저 만든 경우)를 로그인 시점에 자가 치유한다.
            teacher = Teacher(
                id=user.id,
                school_id=school.id,
                name=display_name,
                photo_url=photo_url,
                workspace_email=email,
                hire_date=datetime.datetime.utcnow(),
            )
            db.add(teacher)
            db.add(AuditLog(
                school_id=school.id, actor_id=user.id, action="AUTO_HEAL_TEACHER_PROFILE",
                target_type="TEACHER", target_id=user.id, details={"email": email},
            ))
            await db.commit()
    else:
        # 최초 로그인 - 사전에 등록된 학교 도메인이면 별도 관리자 승인 없이 즉시 계정을 자동 발급한다.
        # (다수 학교로 확장 시 매번 수동 계정 생성을 하지 않기 위한 핵심 자동화 지점)
        user = User(school_id=school.id, email=email, role=UserRole.TEACHER, is_active=True)
        db.add(user)
        await db.flush()

        teacher = Teacher(
            id=user.id,
            school_id=school.id,
            name=display_name,
            photo_url=photo_url,
            workspace_email=email,
            hire_date=datetime.datetime.utcnow(),
        )
        db.add(teacher)
        db.add(AuditLog(
            school_id=school.id, actor_id=user.id, action="AUTO_PROVISION_LOGIN",
            target_type="TEACHER", target_id=user.id, details={"email": email, "name": display_name},
        ))
        await db.commit()

    access_token = create_access_token({
        "sub": user.id,
        "school_id": school.id,
        "role": user.role.value,
        "email": user.email,
        "teacher_id": teacher.id if teacher else None,
    })

    return user, teacher, school, access_token
