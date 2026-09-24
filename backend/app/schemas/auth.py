from typing import Optional

from pydantic import BaseModel


class GoogleLoginRequest(BaseModel):
    """프론트엔드(Google Identity Services)에서 받은 ID Token으로 로그인."""
    id_token: str


class PasswordLoginRequest(BaseModel):
    """구글 워크스페이스를 쓰지 않는 학교를 위한 이메일/비밀번호 로그인."""
    email: str
    password: str


class CurrentUserResponse(BaseModel):
    user_id: str
    school_id: str
    school_name: str
    email: str
    role: str
    teacher_id: Optional[str] = None
    name: Optional[str] = None
    photo_url: Optional[str] = None
