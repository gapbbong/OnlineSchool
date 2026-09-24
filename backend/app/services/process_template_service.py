from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Department, ProcessTemplate, Teacher
from app.schemas.process_template import (
    ProcessTemplateCreateRequest,
    ProcessTemplateResponse,
    ProcessTemplateUpdateRequest,
)


async def _to_response(db: AsyncSession, t: ProcessTemplate) -> ProcessTemplateResponse:
    dept = await db.get(Department, t.department_id) if t.department_id else None
    teacher = await db.get(Teacher, t.contact_teacher_id) if t.contact_teacher_id else None
    return ProcessTemplateResponse(
        id=t.id,
        school_id=t.school_id,
        department_id=t.department_id,
        department_name=dept.name if dept else None,
        category=t.category,
        title=t.title,
        description=t.description,
        required_items=t.required_items,
        form_doc_url=t.form_doc_url,
        contact_teacher_id=t.contact_teacher_id,
        contact_teacher_name=teacher.name if teacher else None,
        created_by=t.created_by,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


async def _validate_refs(
    db: AsyncSession, school_id: str, department_id: Optional[str], contact_teacher_id: Optional[str]
) -> None:
    if department_id:
        dept = await db.get(Department, department_id)
        if not dept or dept.school_id != school_id:
            raise HTTPException(status_code=400, detail="유효하지 않은 부서입니다.")

    if contact_teacher_id:
        teacher = await db.get(Teacher, contact_teacher_id)
        if not teacher or teacher.school_id != school_id:
            raise HTTPException(status_code=400, detail="유효하지 않은 담당자입니다.")


async def list_templates(
    db: AsyncSession, school_id: str, category: Optional[str] = None
) -> List[ProcessTemplateResponse]:
    query = select(ProcessTemplate).filter(ProcessTemplate.school_id == school_id)
    if category:
        query = query.filter(ProcessTemplate.category == category)
    query = query.order_by(ProcessTemplate.category.asc(), ProcessTemplate.title.asc())
    res = await db.execute(query)
    return [await _to_response(db, t) for t in res.scalars().all()]


async def create_template(
    db: AsyncSession, school_id: str, actor_id: str, req: ProcessTemplateCreateRequest
) -> ProcessTemplateResponse:
    await _validate_refs(db, school_id, req.department_id, req.contact_teacher_id)

    template = ProcessTemplate(
        school_id=school_id,
        department_id=req.department_id,
        category=req.category,
        title=req.title,
        description=req.description,
        required_items=req.required_items,
        form_doc_url=req.form_doc_url,
        contact_teacher_id=req.contact_teacher_id,
        created_by=actor_id,
    )
    db.add(template)
    await db.flush()

    db.add(AuditLog(
        school_id=school_id, actor_id=actor_id, action="CREATE_PROCESS_TEMPLATE",
        target_type="PROCESS_TEMPLATE", target_id=template.id,
        details={"category": req.category, "title": req.title, "department_id": req.department_id},
    ))

    await db.commit()
    await db.refresh(template)
    return await _to_response(db, template)


async def update_template(
    db: AsyncSession, school_id: str, actor_id: str, template_id: str, req: ProcessTemplateUpdateRequest
) -> ProcessTemplateResponse:
    template = await db.get(ProcessTemplate, template_id)
    if not template or template.school_id != school_id:
        raise HTTPException(status_code=404, detail="해당 프로세스 템플릿을 찾을 수 없습니다.")

    updates = req.model_dump(exclude_unset=True)

    department_id = updates.get("department_id", template.department_id)
    contact_teacher_id = updates.get("contact_teacher_id", template.contact_teacher_id)
    await _validate_refs(db, school_id, department_id, contact_teacher_id)

    for field, value in updates.items():
        setattr(template, field, value)
    template.created_by = actor_id

    db.add(AuditLog(
        school_id=school_id, actor_id=actor_id, action="UPDATE_PROCESS_TEMPLATE",
        target_type="PROCESS_TEMPLATE", target_id=template.id,
        details=updates,
    ))

    await db.commit()
    await db.refresh(template)
    return await _to_response(db, template)


async def delete_template(db: AsyncSession, school_id: str, actor_id: str, template_id: str) -> None:
    template = await db.get(ProcessTemplate, template_id)
    if not template or template.school_id != school_id:
        raise HTTPException(status_code=404, detail="해당 프로세스 템플릿을 찾을 수 없습니다.")

    db.add(AuditLog(
        school_id=school_id, actor_id=actor_id, action="DELETE_PROCESS_TEMPLATE",
        target_type="PROCESS_TEMPLATE", target_id=template.id,
        details={"category": template.category, "title": template.title},
    ))

    await db.delete(template)
    await db.commit()
