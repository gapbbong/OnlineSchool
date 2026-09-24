from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import datetime

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user, get_current_user_optional, require_roles
from app.models import (
    School, Teacher, Department, Class, Subject, Room, Timetable,
    Task, Shortcut, Message, MessageRecipient, User, UserRole, VisibilityScope, DayOfWeek,
    TaskStatus, SyncAction, SyncTarget
)
from app.schemas.domain import (
    DashboardSummaryResponse, TaskResponse, TaskCreateRequest, TaskUpdateRequest, ShortcutResponse,
    TimetableItemResponse, MessageResponse, TeacherResponse
)
from app.schemas.onboarding import TeacherOnboardingRequest, TeacherOnboardingResponse
from app.services.onboarding_service import TeacherOnboardingService
from app.services.sync_queue import enqueue

router = APIRouter()


async def _resolve_school_id(
    db: AsyncSession, current: Optional[CurrentUser], school_id_param: Optional[str]
) -> str:
    """로그인 상태면 토큰의 school_id가 항상 우선한다 (다른 학교 school_id를 쿼리로
    넘겨도 무시 - IDOR 방지). 비로그인 상태에서는 데모/부트스트랩 편의를 위해 쿼리
    파라미터 또는 첫 번째 활성 학교로 폴백한다."""
    if current:
        return current.school_id
    if school_id_param:
        return school_id_param
    res = await db.execute(select(School).filter(School.is_active == True))
    school = res.scalars().first()
    if not school:
        raise HTTPException(status_code=404, detail="등록된 학교가 없습니다.")
    return school.id


async def _task_to_response(db: AsyncSession, t: Task) -> TaskResponse:
    assignee = await db.get(Teacher, t.assignee_id) if t.assignee_id else None
    dept = await db.get(Department, t.department_id) if t.department_id else None
    creator_teacher = await db.get(Teacher, t.creator_id) if t.creator_id else None
    return TaskResponse(
        id=t.id,
        school_id=t.school_id,
        title=t.title,
        description=t.description,
        department_id=t.department_id,
        assignee_id=t.assignee_id,
        start_datetime=t.start_datetime,
        due_datetime=t.due_datetime,
        priority=t.priority,
        status=t.status,
        visibility=t.visibility,
        creator_name=creator_teacher.name if creator_teacher else None,
        assignee_name=assignee.name if assignee else None,
        department_name=dept.name if dept else None,
        google_drive_folder_id=t.google_drive_folder_id,
        google_sheet_id=t.google_sheet_id,
    )


async def _validate_task_refs(db: AsyncSession, school_id: str, department_id: Optional[str], assignee_id: Optional[str]) -> None:
    if department_id:
        dept = await db.get(Department, department_id)
        if not dept or dept.school_id != school_id:
            raise HTTPException(status_code=400, detail="유효하지 않은 부서입니다.")
    if assignee_id:
        assignee = await db.get(Teacher, assignee_id)
        if not assignee or assignee.school_id != school_id:
            raise HTTPException(status_code=400, detail="유효하지 않은 담당자입니다.")


@router.get("/schools/meta")
async def get_school_metadata(
    school_id: Optional[str] = None,
    current: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """신규 교사 등록 마법사 및 폼용 메타데이터 (부서, 교실, 과목, 학급 목록)"""
    school_id = await _resolve_school_id(db, current, school_id)

    depts = (await db.execute(select(Department).filter(Department.school_id == school_id))).scalars().all()
    rooms = (await db.execute(select(Room).filter(Room.school_id == school_id))).scalars().all()
    subjects = (await db.execute(select(Subject).filter(Subject.school_id == school_id))).scalars().all()

    return {
        "school_id": school_id,
        "departments": [{"id": d.id, "name": d.name} for d in depts],
        "rooms": [{"id": r.id, "name": r.room_name, "type": r.room_type} for r in rooms],
        "subjects": [{"id": s.id, "name": s.name} for s in subjects]
    }

@router.post("/teachers/onboarding", response_model=TeacherOnboardingResponse)
async def onboard_new_teacher(
    req: TeacherOnboardingRequest,
    current: CurrentUser = Depends(require_roles(UserRole.SCHOOL_ADMIN, UserRole.DEPARTMENT_HEAD)),
    db: AsyncSession = Depends(get_db)
):
    """신규 교사 원스톱 등록 엔드포인트 (관리자/부서장 전용, 로그인한 본인 학교에만 등록 가능)"""
    return await TeacherOnboardingService.onboard_teacher(
        school_id=current.school_id,
        actor_id=current.user_id,
        req=req,
        db=db
    )


@router.get("/dashboard", response_model=DashboardSummaryResponse)
async def get_dashboard(
    school_id: Optional[str] = Query(None),
    teacher_id: Optional[str] = Query(None),
    current: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """4분할 대시보드 통합 데이터 조회"""
    school_id = await _resolve_school_id(db, current, school_id)
    school = await db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="해당 학교를 찾을 수 없습니다.")

    # 1. 1사분면: 업무 캘린더 (오늘의 업무 및 주간 주요 업무)
    tasks_query = select(Task).filter(Task.school_id == school_id).order_by(Task.due_datetime.asc())
    tasks_res = await db.execute(tasks_query)
    tasks_list = tasks_res.scalars().all()
    
    today_tasks = [await _task_to_response(db, t) for t in tasks_list]

    # 2. 2사분면: 자주 쓰는 바로가기
    sc_query = select(Shortcut).filter(Shortcut.school_id == school_id).order_by(Shortcut.sort_order.asc())
    sc_res = await db.execute(sc_query)
    shortcuts = [
        ShortcutResponse(
            id=s.id,
            title=s.title,
            url=s.url,
            icon=s.icon,
            category=s.category,
            sort_order=s.sort_order
        ) for s in sc_res.scalars().all()
    ]

    # 3. 3사분면: 시간표 (오늘 요일 또는 기본 화요일 기준)
    tt_query = select(Timetable).filter(Timetable.school_id == school_id).order_by(Timetable.period.asc())
    if teacher_id:
        tt_query = tt_query.filter(Timetable.teacher_id == teacher_id)
    tt_res = await db.execute(tt_query)
    
    today_timetables = []
    for row in tt_res.scalars().all():
        tch = await db.get(Teacher, row.teacher_id)
        cls = await db.get(Class, row.class_id)
        sbj = await db.get(Subject, row.subject_id)
        rm = await db.get(Room, row.room_id) if row.room_id else None
        prm = await db.get(Room, row.practice_room_id) if row.practice_room_id else None
        
        today_timetables.append(TimetableItemResponse(
            id=row.id,
            day_of_week=row.day_of_week,
            period=row.period,
            subject_name=sbj.name if sbj else "-",
            teacher_name=tch.name if tch else "-",
            grade_number=3, # 데모 학년
            class_number=cls.class_number if cls else 1,
            room_name=rm.room_name if rm else None,
            practice_room_name=prm.room_name if prm else None,
            lesson_type=row.lesson_type
        ))

    # 4. 4사분면: 교직원 메시지
    msg_query = select(Message).filter(Message.school_id == school_id).order_by(Message.created_at.desc()).limit(10)
    msg_res = await db.execute(msg_query)
    
    recent_messages = []
    for m in msg_res.scalars().all():
        snd = await db.get(Teacher, m.sender_id)
        recent_messages.append(MessageResponse(
            id=m.id,
            sender_name=snd.name if snd else "교직원",
            msg_type=m.msg_type,
            title=m.title,
            content=m.content,
            created_at=m.created_at,
            is_read=False
        ))

    return DashboardSummaryResponse(
        school_name=school.name,
        today_tasks=today_tasks,
        shortcuts=shortcuts,
        today_timetables=today_timetables,
        recent_messages=recent_messages
    )


@router.get("/teachers", response_model=List[TeacherResponse])
async def get_teachers(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """교직원 목록 조회 (로그인한 본인 학교만, 개인정보 보호 필터링은 서버가 토큰의
    역할(role)로만 판단한다 - 클라이언트가 조회 권한을 자칭할 수 없다)"""
    is_admin = current.role in (UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN)
    query = select(Teacher).filter(Teacher.school_id == current.school_id)
    res = await db.execute(query)
    teachers = res.scalars().all()

    result = []
    for t in teachers:
        # 개인정보 보호 필터링
        phone = t.phone_number
        if t.phone_visibility == VisibilityScope.ADMIN_ONLY and not is_admin:
            phone = "***-****-**** (비공개)"

        car = t.car_number
        if t.car_visibility == VisibilityScope.ADMIN_ONLY and not is_admin:
            car = "(관리자 전용 비공개)"

        result.append(TeacherResponse(
            id=t.id,
            school_id=t.school_id,
            name=t.name,
            photo_url=t.photo_url,
            phone_number=phone,
            workspace_email=t.workspace_email,
            car_number=car,
            position=t.position,
            assigned_work=t.assigned_work,
            status=t.status,
            phone_visibility=t.phone_visibility,
            car_visibility=t.car_visibility,
            email_visibility=t.email_visibility,
            memo=t.memo if is_admin else None,
            departments=["교무부"],
            homeroom_class_name="3학년 2반" if t.homeroom_class_id else None
        ))
    return result


@router.get("/timetables/teacher/{teacher_id}", response_model=List[TimetableItemResponse])
async def get_teacher_timetable(
    teacher_id: str,
    current: Optional[CurrentUser] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """교사별 시간표 조회"""
    teacher = await db.get(Teacher, teacher_id)
    if not teacher or (current and teacher.school_id != current.school_id):
        raise HTTPException(status_code=404, detail="해당 교사를 찾을 수 없습니다.")

    query = select(Timetable).filter(Timetable.teacher_id == teacher_id).order_by(Timetable.period.asc())
    res = await db.execute(query)
    items = []
    for row in res.scalars().all():
        tch = await db.get(Teacher, row.teacher_id)
        cls = await db.get(Class, row.class_id)
        sbj = await db.get(Subject, row.subject_id)
        rm = await db.get(Room, row.room_id) if row.room_id else None
        prm = await db.get(Room, row.practice_room_id) if row.practice_room_id else None
        items.append(TimetableItemResponse(
            id=row.id,
            day_of_week=row.day_of_week,
            period=row.period,
            subject_name=sbj.name if sbj else "-",
            teacher_name=tch.name if tch else "-",
            grade_number=3,
            class_number=cls.class_number if cls else 1,
            room_name=rm.room_name if rm else None,
            practice_room_name=prm.room_name if prm else None,
            lesson_type=row.lesson_type
        ))
    return items


# --- 업무 & 캘린더 CRUD (1사분면) -------------------------------------------------
# 학교 범위는 항상 로그인 토큰의 school_id로만 결정한다 (다른 학교 데이터 접근 원천 차단).

_TASK_WRITE_ROLES = (UserRole.TEACHER, UserRole.STAFF, UserRole.DEPARTMENT_HEAD, UserRole.SCHOOL_ADMIN)


@router.get("/tasks", response_model=List[TaskResponse])
async def list_tasks(
    department_id: Optional[str] = Query(None),
    assignee_id: Optional[str] = Query(None),
    status: Optional[TaskStatus] = Query(None),
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """업무/캘린더 목록 조회 (월간/주간/일간/목록 뷰의 공통 데이터 소스)"""
    query = select(Task).filter(Task.school_id == current.school_id)
    if department_id:
        query = query.filter(Task.department_id == department_id)
    if assignee_id:
        query = query.filter(Task.assignee_id == assignee_id)
    if status:
        query = query.filter(Task.status == status)
    query = query.order_by(Task.due_datetime.asc()).limit(500)

    res = await db.execute(query)
    return [await _task_to_response(db, t) for t in res.scalars().all()]


@router.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(
    req: TaskCreateRequest,
    current: CurrentUser = Depends(require_roles(*_TASK_WRITE_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """업무 생성. Google Sheets 동기화는 SyncOutbox에 적재되어 백그라운드에서
    비동기 처리되며, Google 쪽 장애가 있어도 업무 생성 자체는 즉시 성공한다."""
    await _validate_task_refs(db, current.school_id, req.department_id, req.assignee_id)

    task = Task(
        school_id=current.school_id,
        department_id=req.department_id,
        creator_id=current.user_id,
        assignee_id=req.assignee_id,
        title=req.title,
        description=req.description,
        start_datetime=req.start_datetime,
        end_datetime=req.end_datetime,
        due_datetime=req.due_datetime,
        priority=req.priority,
        status=TaskStatus.PENDING,
        visibility=req.visibility,
        sync_status="PENDING",
    )
    db.add(task)
    await db.flush()

    await enqueue(
        db,
        school_id=current.school_id,
        entity_type="TASK",
        entity_id=task.id,
        action=SyncAction.CREATE,
        target=SyncTarget.SHEETS,
        payload={
            "title": task.title,
            "status": task.status.value,
            "due_datetime": task.due_datetime.isoformat() if task.due_datetime else None,
            "department_id": task.department_id,
            "assignee_id": task.assignee_id,
            "google_sheet_id": task.google_sheet_id,
        },
    )
    await db.commit()
    await db.refresh(task)
    return await _task_to_response(db, task)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    req: TaskUpdateRequest,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """업무 수정. 생성자/담당자 본인 또는 부서장 이상만 가능하다."""
    task = await db.get(Task, task_id)
    if not task or task.school_id != current.school_id:
        raise HTTPException(status_code=404, detail="해당 업무를 찾을 수 없습니다.")

    is_privileged = current.role in (UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN, UserRole.DEPARTMENT_HEAD)
    is_owner = current.user_id == task.creator_id or current.teacher_id == task.assignee_id
    if not (is_privileged or is_owner):
        raise HTTPException(status_code=403, detail="본인이 생성했거나 담당자로 지정된 업무만 수정할 수 있습니다.")

    if req.department_id is not None:
        await _validate_task_refs(db, current.school_id, req.department_id or None, None)
        task.department_id = req.department_id or None
    if req.assignee_id is not None:
        await _validate_task_refs(db, current.school_id, None, req.assignee_id or None)
        task.assignee_id = req.assignee_id or None

    for field in ("title", "description", "start_datetime", "end_datetime", "due_datetime", "priority", "status", "visibility"):
        value = getattr(req, field)
        if value is not None:
            setattr(task, field, value)

    task.sync_status = "PENDING"
    await db.flush()

    await enqueue(
        db,
        school_id=current.school_id,
        entity_type="TASK",
        entity_id=task.id,
        action=SyncAction.UPDATE,
        target=SyncTarget.SHEETS,
        payload={
            "title": task.title,
            "status": task.status.value,
            "due_datetime": task.due_datetime.isoformat() if task.due_datetime else None,
            "department_id": task.department_id,
            "assignee_id": task.assignee_id,
            "google_sheet_id": task.google_sheet_id,
        },
    )
    await db.commit()
    await db.refresh(task)
    return await _task_to_response(db, task)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """업무 삭제. 생성자 본인 또는 부서장 이상만 가능하다."""
    task = await db.get(Task, task_id)
    if not task or task.school_id != current.school_id:
        raise HTTPException(status_code=404, detail="해당 업무를 찾을 수 없습니다.")

    is_privileged = current.role in (UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN, UserRole.DEPARTMENT_HEAD)
    if not (is_privileged or current.user_id == task.creator_id):
        raise HTTPException(status_code=403, detail="본인이 생성한 업무이거나 부서장 이상만 삭제할 수 있습니다.")

    await db.delete(task)
    await db.commit()
