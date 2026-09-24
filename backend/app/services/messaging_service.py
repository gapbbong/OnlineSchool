import datetime
from typing import List

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Department, Message, MessageRecipient, Room, Subject, Task, Teacher, TeacherDepartment, Timetable,
)
from app.schemas.messaging import (
    LinkedTaskSummary, LinkedTimetableSummary, MessageCreateRequest, MessageDetailResponse,
)


async def _resolve_recipients(db: AsyncSession, school_id: str, sender_id: str, req: MessageCreateRequest) -> List[Teacher]:
    if req.msg_type == "ANNOUNCEMENT":
        res = await db.execute(select(Teacher).filter(Teacher.school_id == school_id))
        return [t for t in res.scalars().all() if t.id != sender_id]

    if req.msg_type == "DEPARTMENT":
        dept = await db.get(Department, req.target_department_id)
        if not dept or dept.school_id != school_id:
            raise HTTPException(status_code=400, detail="유효하지 않은 부서입니다.")
        res = await db.execute(
            select(Teacher)
            .join(TeacherDepartment, TeacherDepartment.teacher_id == Teacher.id)
            .filter(TeacherDepartment.department_id == req.target_department_id)
        )
        return [t for t in res.scalars().all() if t.id != sender_id]

    # DIRECT
    res = await db.execute(
        select(Teacher).filter(Teacher.school_id == school_id, Teacher.id.in_(req.recipient_ids or []))
    )
    teachers = res.scalars().all()
    if len(teachers) != len(set(req.recipient_ids or [])):
        raise HTTPException(status_code=400, detail="일부 수신자를 찾을 수 없습니다 (같은 학교 소속인지 확인하세요).")
    return teachers


async def send_message(db: AsyncSession, school_id: str, sender_teacher_id: str, req: MessageCreateRequest) -> Message:
    if req.linked_task_id:
        task = await db.get(Task, req.linked_task_id)
        if not task or task.school_id != school_id:
            raise HTTPException(status_code=400, detail="연결하려는 업무를 찾을 수 없습니다.")
    if req.linked_timetable_id:
        tt = await db.get(Timetable, req.linked_timetable_id)
        if not tt or tt.school_id != school_id:
            raise HTTPException(status_code=400, detail="연결하려는 시간표 항목을 찾을 수 없습니다.")

    recipients = await _resolve_recipients(db, school_id, sender_teacher_id, req)
    if not recipients:
        raise HTTPException(status_code=400, detail="메시지를 받을 수신자가 없습니다.")

    message = Message(
        school_id=school_id,
        sender_id=sender_teacher_id,
        msg_type=req.msg_type,
        target_department_id=req.target_department_id,
        title=req.title,
        content=req.content,
        linked_task_id=req.linked_task_id,
        linked_timetable_id=req.linked_timetable_id,
    )
    db.add(message)
    await db.flush()

    for teacher in recipients:
        db.add(MessageRecipient(message_id=message.id, recipient_id=teacher.id))

    await db.commit()
    await db.refresh(message)
    return message


async def to_detail(db: AsyncSession, message: Message, is_read: bool) -> MessageDetailResponse:
    sender = await db.get(Teacher, message.sender_id)
    dept = await db.get(Department, message.target_department_id) if message.target_department_id else None

    linked_task = None
    if message.linked_task_id:
        t = await db.get(Task, message.linked_task_id)
        if t:
            linked_task = LinkedTaskSummary(id=t.id, title=t.title, due_datetime=t.due_datetime, status=t.status.value)

    linked_timetable = None
    if message.linked_timetable_id:
        tt = await db.get(Timetable, message.linked_timetable_id)
        if tt:
            subject = await db.get(Subject, tt.subject_id)
            room = await db.get(Room, tt.room_id) if tt.room_id else None
            practice_room = await db.get(Room, tt.practice_room_id) if tt.practice_room_id else None
            linked_timetable = LinkedTimetableSummary(
                id=tt.id,
                day_of_week=tt.day_of_week.value,
                period=tt.period,
                subject_name=subject.name if subject else "-",
                room_name=room.room_name if room else None,
                practice_room_name=practice_room.room_name if practice_room else None,
            )

    return MessageDetailResponse(
        id=message.id,
        sender_id=message.sender_id,
        sender_name=sender.name if sender else "교직원",
        msg_type=message.msg_type,
        target_department_id=message.target_department_id,
        target_department_name=dept.name if dept else None,
        title=message.title,
        content=message.content,
        created_at=message.created_at,
        is_read=is_read,
        linked_task=linked_task,
        linked_timetable=linked_timetable,
    )


async def list_inbox(db: AsyncSession, teacher_id: str) -> List[MessageDetailResponse]:
    res = await db.execute(
        select(Message, MessageRecipient)
        .join(MessageRecipient, MessageRecipient.message_id == Message.id)
        .filter(MessageRecipient.recipient_id == teacher_id)
        .order_by(Message.created_at.desc())
        .limit(200)
    )
    return [await to_detail(db, m, mr.is_read) for m, mr in res.all()]


async def list_sent(db: AsyncSession, teacher_id: str) -> List[MessageDetailResponse]:
    res = await db.execute(
        select(Message).filter(Message.sender_id == teacher_id).order_by(Message.created_at.desc()).limit(200)
    )
    return [await to_detail(db, m, True) for m in res.scalars().all()]


async def mark_read(db: AsyncSession, teacher_id: str, message_id: str) -> None:
    res = await db.execute(
        select(MessageRecipient).filter(
            MessageRecipient.message_id == message_id, MessageRecipient.recipient_id == teacher_id
        )
    )
    recipient_row = res.scalars().first()
    if not recipient_row:
        raise HTTPException(status_code=404, detail="수신함에서 해당 메시지를 찾을 수 없습니다.")
    if not recipient_row.is_read:
        recipient_row.is_read = True
        recipient_row.read_at = datetime.datetime.utcnow()
        await db.commit()
