import datetime
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AuditLog, Department, SchoolSetting, SyncAction, SyncTarget, Teacher, TeacherStatus, WorkHandover,
)
from app.schemas.handover import WorkHandoverCreateRequest, WorkHandoverResponse, WorkHandoverTransferRequest
from app.services.sync_queue import enqueue


async def _to_response(db: AsyncSession, h: WorkHandover) -> WorkHandoverResponse:
    dept = await db.get(Department, h.department_id) if h.department_id else None
    teacher = await db.get(Teacher, h.current_teacher_id) if h.current_teacher_id else None
    return WorkHandoverResponse(
        id=h.id,
        work_title=h.work_title,
        department_id=h.department_id,
        department_name=dept.name if dept else None,
        current_teacher_id=h.current_teacher_id,
        current_teacher_name=teacher.name if teacher else None,
        drive_folder_id=h.drive_folder_id,
        drive_folder_url=h.drive_folder_url,
        handover_note=h.handover_note,
        created_at=h.created_at,
        updated_at=h.updated_at,
    )


async def list_handovers(db: AsyncSession, school_id: str, department_id: Optional[str] = None) -> List[WorkHandoverResponse]:
    query = select(WorkHandover).filter(WorkHandover.school_id == school_id)
    if department_id:
        query = query.filter(WorkHandover.department_id == department_id)
    query = query.order_by(WorkHandover.work_title.asc())
    res = await db.execute(query)
    return [await _to_response(db, h) for h in res.scalars().all()]


async def create_handover(
    db: AsyncSession, school_id: str, actor_id: str, req: WorkHandoverCreateRequest
) -> WorkHandoverResponse:
    dept = None
    if req.department_id:
        dept = await db.get(Department, req.department_id)
        if not dept or dept.school_id != school_id:
            raise HTTPException(status_code=400, detail="유효하지 않은 부서입니다.")

    if req.current_teacher_id:
        teacher = await db.get(Teacher, req.current_teacher_id)
        if not teacher or teacher.school_id != school_id:
            raise HTTPException(status_code=400, detail="유효하지 않은 담당자입니다.")
        if teacher.status == TeacherStatus.RETIRED:
            raise HTTPException(status_code=400, detail="퇴직 처리된 교사는 담당자로 지정할 수 없습니다.")

    handover = WorkHandover(
        school_id=school_id,
        department_id=req.department_id,
        work_title=req.work_title,
        current_teacher_id=req.current_teacher_id,
        handover_note=req.handover_note,
    )
    db.add(handover)
    await db.flush()

    db.add(AuditLog(
        school_id=school_id, actor_id=actor_id, action="CREATE_WORK_HANDOVER",
        target_type="WORK_HANDOVER", target_id=handover.id,
        details={"work_title": req.work_title, "department_id": req.department_id},
    ))

    # 부서 자체 Drive 폴더가 있으면 그 아래에, 없으면 학교 Drive 루트 아래에 업무별 하위
    # 폴더 생성을 비동기로 요청한다 (둘 다 없으면 관리자가 나중에 폴더를 직접 연결하면 된다).
    parent_folder_id = None
    if dept and dept.drive_folder_id:
        parent_folder_id = dept.drive_folder_id
    else:
        setting_res = await db.execute(select(SchoolSetting).filter(SchoolSetting.school_id == school_id))
        setting = setting_res.scalars().first()
        if setting and setting.google_drive_root_folder_id:
            parent_folder_id = setting.google_drive_root_folder_id

    if parent_folder_id:
        await enqueue(
            db, school_id=school_id, entity_type="WORK_HANDOVER", entity_id=handover.id,
            action=SyncAction.CREATE, target=SyncTarget.DRIVE,
            payload={"parent_folder_id": parent_folder_id, "work_title": req.work_title},
        )

    await db.commit()
    await db.refresh(handover)
    return await _to_response(db, handover)


async def transfer_handover(
    db: AsyncSession, school_id: str, actor_id: str, handover_id: str, req: WorkHandoverTransferRequest
) -> WorkHandoverResponse:
    handover = await db.get(WorkHandover, handover_id)
    if not handover or handover.school_id != school_id:
        raise HTTPException(status_code=404, detail="해당 인수인계 항목을 찾을 수 없습니다.")

    new_teacher = await db.get(Teacher, req.new_teacher_id)
    if not new_teacher or new_teacher.school_id != school_id:
        raise HTTPException(status_code=400, detail="유효하지 않은 후임자입니다.")
    if new_teacher.status == TeacherStatus.RETIRED:
        raise HTTPException(status_code=400, detail="퇴직 처리된 교사에게는 인수인계할 수 없습니다.")

    prev_teacher = await db.get(Teacher, handover.current_teacher_id) if handover.current_teacher_id else None
    prev_name = prev_teacher.name if prev_teacher else "(담당자 없음)"

    timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    entry = f"[{timestamp}] {prev_name} → {new_teacher.name} 인수인계"
    if req.note:
        entry += f"\n{req.note}"

    handover.handover_note = entry if not handover.handover_note else f"{entry}\n\n{handover.handover_note}"
    handover.current_teacher_id = req.new_teacher_id

    db.add(AuditLog(
        school_id=school_id, actor_id=actor_id, action="TRANSFER_WORK_HANDOVER",
        target_type="WORK_HANDOVER", target_id=handover.id,
        details={"from": prev_teacher.id if prev_teacher else None, "to": new_teacher.id},
    ))

    await db.commit()
    await db.refresh(handover)
    return await _to_response(db, handover)
