from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
import datetime

from app.core.database import get_db
from app.models import (
    School, Teacher, Department, Class, Subject, Room, Timetable,
    Task, Shortcut, Message, MessageRecipient, User, UserRole, VisibilityScope, DayOfWeek
)
from app.schemas.domain import (
    DashboardSummaryResponse, TaskResponse, ShortcutResponse,
    TimetableItemResponse, MessageResponse, TeacherResponse
)
from app.schemas.onboarding import TeacherOnboardingRequest, TeacherOnboardingResponse
from app.services.onboarding_service import TeacherOnboardingService

router = APIRouter()

@router.get("/schools/meta")
async def get_school_metadata(school_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """신규 교사 등록 마법사 및 폼용 메타데이터 (부서, 교실, 과목, 학급 목록)"""
    if not school_id:
        res = await db.execute(select(School).filter(School.is_active == True))
        school = res.scalars().first()
        if not school:
            raise HTTPException(status_code=404, detail="학교 없음")
        school_id = school.id

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
    school_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """신규 교사 원스톱 등록 엔드포인트"""
    if not school_id:
        res = await db.execute(select(School).filter(School.is_active == True))
        school = res.scalars().first()
        if not school:
            raise HTTPException(status_code=404, detail="학교 없음")
        school_id = school.id

    return await TeacherOnboardingService.onboard_teacher(
        school_id=school_id,
        actor_id="admin_system",
        req=req,
        db=db
    )


@router.get("/dashboard", response_model=DashboardSummaryResponse)
async def get_dashboard(
    school_id: Optional[str] = Query(None),
    teacher_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """4분할 대시보드 통합 데이터 조회"""
    # 기본 학교 조회 (지정되지 않은 경우 첫 번째 활성 학교)
    if not school_id:
        result = await db.execute(select(School).filter(School.is_active == True))
        school = result.scalars().first()
        if not school:
            raise HTTPException(status_code=404, detail="등록된 학교가 없습니다.")
        school_id = school.id
    else:
        school = await db.get(School, school_id)
        if not school:
            raise HTTPException(status_code=404, detail="해당 학교를 찾을 수 없습니다.")

    # 1. 1사분면: 업무 캘린더 (오늘의 업무 및 주간 주요 업무)
    tasks_query = select(Task).filter(Task.school_id == school_id).order_by(Task.due_datetime.asc())
    tasks_res = await db.execute(tasks_query)
    tasks_list = tasks_res.scalars().all()
    
    today_tasks = []
    for t in tasks_list:
        assignee = await db.get(Teacher, t.assignee_id) if t.assignee_id else None
        dept = await db.get(Department, t.department_id) if t.department_id else None
        today_tasks.append(TaskResponse(
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
            creator_name="관리자",
            assignee_name=assignee.name if assignee else None,
            department_name=dept.name if dept else None,
            google_drive_folder_id=t.google_drive_folder_id,
            google_sheet_id=t.google_sheet_id
        ))

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
    school_id: Optional[str] = None,
    viewer_role: UserRole = UserRole.TEACHER,
    db: AsyncSession = Depends(get_db)
):
    """교직원 목록 조회 (개인정보 보호 필터링 적용)"""
    query = select(Teacher)
    if school_id:
        query = query.filter(Teacher.school_id == school_id)
    res = await db.execute(query)
    teachers = res.scalars().all()

    result = []
    for t in teachers:
        # 개인정보 보호 필터링
        phone = t.phone_number
        if t.phone_visibility == VisibilityScope.ADMIN_ONLY and viewer_role not in [UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN]:
            phone = "***-****-**** (비공개)"
            
        car = t.car_number
        if t.car_visibility == VisibilityScope.ADMIN_ONLY and viewer_role not in [UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN]:
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
            memo=t.memo if viewer_role in [UserRole.SUPER_ADMIN, UserRole.SCHOOL_ADMIN] else None,
            departments=["교무부"],
            homeroom_class_name="3학년 2반" if t.homeroom_class_id else None
        ))
    return result


@router.get("/timetables/teacher/{teacher_id}", response_model=List[TimetableItemResponse])
async def get_teacher_timetable(teacher_id: str, db: AsyncSession = Depends(get_db)):
    """교사별 시간표 조회"""
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
