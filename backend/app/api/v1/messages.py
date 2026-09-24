from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.schemas.messaging import MessageCreateRequest, MessageDetailResponse
from app.services import messaging_service

router = APIRouter()


@router.post("/messages", response_model=MessageDetailResponse, status_code=201)
async def send_message(
    req: MessageCreateRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """교직원 메시지 발송 (전체공지/부서공지/개인쪽지).

    개인 쪽지는 발신자와 수신자만 조회할 수 있으며, 관리자 권한으로도 내용을
    우회해서 볼 수 없다 (school_id로만 범위가 제한되는 다른 API와 달리, 메시지는
    sender/recipient 여부로만 접근이 결정된다)."""
    if not current.teacher_id:
        raise HTTPException(status_code=400, detail="교직원 프로필이 없는 계정은 메시지를 보낼 수 없습니다.")
    message = await messaging_service.send_message(db, current.school_id, current.teacher_id, req)
    return await messaging_service.to_detail(db, message, is_read=True)


@router.get("/messages", response_model=List[MessageDetailResponse])
async def list_messages(
    box: Literal["inbox", "sent"] = "inbox",
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """받은 메시지함/보낸 메시지함 조회. 본인이 발신자이거나 수신자인 메시지만 보인다."""
    if not current.teacher_id:
        return []
    if box == "sent":
        return await messaging_service.list_sent(db, current.teacher_id)
    return await messaging_service.list_inbox(db, current.teacher_id)


@router.post("/messages/{message_id}/read", status_code=204)
async def mark_message_read(
    message_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current.teacher_id:
        raise HTTPException(status_code=400, detail="교직원 프로필이 없는 계정입니다.")
    await messaging_service.mark_read(db, current.teacher_id, message_id)
