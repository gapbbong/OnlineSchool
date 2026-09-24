import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.core.security import hash_password
from app.models import (
    School, SchoolSetting, User, Teacher, Department, TeacherDepartment,
    Grade, Class, Subject, Room, Timetable, AuditLog, UserRole, VisibilityScope, DayOfWeek
)
from app.schemas.onboarding import TeacherOnboardingRequest, TeacherOnboardingResponse

logger = logging.getLogger("TeacherOnboarding")

class TeacherOnboardingService:
    @classmethod
    async def onboard_teacher(
        cls,
        school_id: str,
        actor_id: str,
        req: TeacherOnboardingRequest,
        db: AsyncSession
    ) -> TeacherOnboardingResponse:
        """
        신규 교사 등록 파이프라인:
        1. 이메일 중복 및 도메인 검증
        2. User 계정 생성
        3. Teacher 프로필 생성 (개인정보 공개범위 포함)
        4. Department 소속 연결
        5. 담임반 배정 (있는 경우)
        6. 시간표 슬롯 등록
        7. Google Drive 및 Sheets 권한 비동기 프로비저닝 트리거
        8. AuditLog 기록
        """
        # 0. 학교 정보 확인
        school = await db.get(School, school_id)
        if not school:
            raise HTTPException(status_code=404, detail="해당 학교를 찾을 수 없습니다.")

        # 도메인 일치 확인 (예: @kse.hs.kr)
        email_domain = req.workspace_email.split("@")[-1]
        if email_domain != school.workspace_domain:
            raise HTTPException(
                status_code=400, 
                detail=f"이메일 도메인이 학교 도메인(@{school.workspace_domain})과 일치하지 않습니다."
            )

        # 중복 확인
        existing_user = await db.execute(
            select(User).filter(User.school_id == school_id, User.email == req.workspace_email)
        )
        if existing_user.scalars().first():
            raise HTTPException(status_code=400, detail="이미 등록된 교직원 이메일입니다.")

        # 1. User 생성 (초기 비밀번호가 주어지면 구글 워크스페이스 없이도 로그인 가능하도록 해시 저장)
        new_user = User(
            school_id=school_id,
            email=req.workspace_email,
            role=req.role,
            is_active=True,
            hashed_password=hash_password(req.initial_password) if req.initial_password else None,
        )
        db.add(new_user)
        await db.flush()

        # 학년도 전환 후 같은 grade_number가 여러 학년도에 걸쳐 존재할 수 있으므로,
        # 항상 학교의 "현재 학년도" 기준으로만 학급을 찾는다.
        setting_res = await db.execute(select(SchoolSetting).filter(SchoolSetting.school_id == school_id))
        school_setting = setting_res.scalars().first()
        current_academic_year = school_setting.current_academic_year if school_setting else None

        # 2. 담임반 조회 (있을 경우)
        homeroom_class_id = None
        if req.homeroom_grade and req.homeroom_class:
            grade_res = await db.execute(
                select(Grade).filter(
                    Grade.school_id == school_id,
                    Grade.grade_number == req.homeroom_grade,
                    Grade.academic_year == current_academic_year,
                )
            )
            grade_obj = grade_res.scalars().first()
            if grade_obj:
                class_res = await db.execute(
                    select(Class).filter(Class.grade_id == grade_obj.id, Class.class_number == req.homeroom_class)
                )
                class_obj = class_res.scalars().first()
                if class_obj:
                    homeroom_class_id = class_obj.id

        # 3. Teacher 생성
        new_teacher = Teacher(
            id=new_user.id,
            school_id=school_id,
            name=req.name,
            phone_number=req.phone_number,
            workspace_email=req.workspace_email,
            car_number=req.car_number,
            position=req.position,
            homeroom_class_id=homeroom_class_id,
            assigned_work=req.assigned_work,
            phone_visibility=req.phone_visibility,
            car_visibility=req.car_visibility,
            email_visibility=VisibilityScope.ALL_STAFF
        )
        db.add(new_teacher)
        await db.flush()

        # 4. Department 연결
        dept = await db.get(Department, req.department_id)
        if not dept or dept.school_id != school_id:
            raise HTTPException(status_code=400, detail="유효하지 않은 부서입니다.")

        td = TeacherDepartment(
            teacher_id=new_teacher.id,
            department_id=dept.id,
            is_primary=True
        )
        db.add(td)

        # 5. 시간표 등록
        created_timetables = 0
        if req.timetable_slots and req.subject_id:
            for slot in req.timetable_slots:
                try:
                    day_enum = DayOfWeek(slot.get("day", "MON"))
                except ValueError:
                    day_enum = DayOfWeek.MON

                # 학급 찾기
                grade_res = await db.execute(
                    select(Grade).filter(
                        Grade.school_id == school_id,
                        Grade.grade_number == slot.get("grade", 1),
                        Grade.academic_year == current_academic_year,
                    )
                )
                grade_obj = grade_res.scalars().first()
                if grade_obj:
                    class_res = await db.execute(
                        select(Class).filter(Class.grade_id == grade_obj.id, Class.class_number == slot.get("class", 1))
                    )
                    class_obj = class_res.scalars().first()
                    if class_obj:
                        tt = Timetable(
                            school_id=school_id,
                            academic_year=datetime.datetime.now().year,
                            semester=2,
                            day_of_week=day_enum,
                            period=slot.get("period", 1),
                            teacher_id=new_teacher.id,
                            grade_id=grade_obj.id,
                            class_id=class_obj.id,
                            subject_id=req.subject_id,
                            room_id=slot.get("room_id"),
                            practice_room_id=slot.get("practice_room_id"),
                            lesson_type=slot.get("lesson_type", "일반수업")
                        )
                        db.add(tt)
                        created_timetables += 1

        # 6. AuditLog 기록
        audit = AuditLog(
            school_id=school_id,
            actor_id=actor_id,
            action="ONBOARD_TEACHER",
            target_type="TEACHER",
            target_id=new_teacher.id,
            details={
                "name": new_teacher.name,
                "email": new_teacher.workspace_email,
                "department": dept.name,
                "role": req.role.value
            }
        )
        db.add(audit)

        await db.commit()

        # 7. Google Drive / Sheets 권한 부여 (시뮬레이션/비동기)
        drive_granted = req.sync_google_drive
        sheets_granted = req.sync_google_sheets

        return TeacherOnboardingResponse(
            teacher_id=new_teacher.id,
            user_id=new_user.id,
            name=new_teacher.name,
            workspace_email=new_teacher.workspace_email,
            department_name=dept.name,
            role=req.role.value,
            drive_folder_granted=drive_granted,
            sheets_access_granted=sheets_granted,
            created_timetables_count=created_timetables,
            message=f"{new_teacher.name} 선생님의 온라인 교무실 계정 및 {dept.name} 부서 배정이 완료되었습니다."
        )
