from typing import Optional

from pydantic import BaseModel


class GoogleLoginRequest(BaseModel):
    """프론트엔드(Google Identity Services)에서 받은 ID Token으로 로그인."""
    id_token: str


class CurrentUserResponse(BaseModel):
    user_id: str
    school_id: str
    school_name: str
    email: str
    role: str
    teacher_id: Optional[str] = None
    name: Optional[str] = None
    photo_url: Optional[str] = None
