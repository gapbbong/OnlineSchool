import asyncio
from app.core.database import engine, Base
from app.models import (
    School, SchoolSetting, User, Teacher, Department, TeacherDepartment,
    Grade, Class, Subject, Room, Timetable, Task, Shortcut, Message,
    MessageRecipient, AuditLog, UserRole, TeacherStatus, VisibilityScope,
    TaskPriority, TaskStatus, DayOfWeek, RoomType
)
from app.core.database import AsyncSessionLocal
import datetime

async def init_db():
    print("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created successfully.")

    # 기본 시드 데이터 생성 (KSE 고등학교)
    async with AsyncSessionLocal() as session:
        # 1. School & Settings
        school = School(
            name="한국과학기술고등학교",
            code="KSE_HS",
            workspace_domain="kse.hs.kr",
            is_active=True
        )
        session.add(school)
        await session.flush()

        settings = SchoolSetting(
            school_id=school.id,
            google_drive_root_folder_id="1sulAaa2WDVqxePp3SlM7dmX3ofiww8pt",
            google_workspace_enabled=True,
            google_drive_enabled=True,
            google_sheets_enabled=True,
            google_calendar_enabled=True
        )
        session.add(settings)

        # 2. Rooms (교실 및 실습실)
        room_302 = Room(school_id=school.id, room_name="302호", building="본관", floor=3, room_type=RoomType.GENERAL)
        room_303 = Room(school_id=school.id, room_name="303호", building="본관", floor=3, room_type=RoomType.GENERAL)
        room_comp_b = Room(school_id=school.id, room_name="컴퓨터실 B", building="정보관", floor=2, room_type=RoomType.COMPUTER, equipment="PC 35대, 빔프로젝터")
        session.add_all([room_302, room_303, room_comp_b])
        await session.flush()

        # 3. Departments (부서)
        dept_gyomu = Department(school_id=school.id, name="교무부", code="GYOMU", sort_order=1)
        dept_yeongu = Department(school_id=school.id, name="연구부", code="YEONGU", sort_order=2)
        dept_haksaeng = Department(school_id=school.id, name="학생부", code="HAKSAENG", sort_order=3)
        session.add_all([dept_gyomu, dept_yeongu, dept_haksaeng])
        await session.flush()

        # 4. Grades & Classes (학년 및 반)
        grade_3 = Grade(school_id=school.id, grade_number=3, name="3학년")
        session.add(grade_3)
        await session.flush()

        class_3_2 = Class(grade_id=grade_3.id, class_number=2, name="2반")
        session.add(class_3_2)
        await session.flush()

        # 5. Subjects (과목)
        subj_korean = Subject(school_id=school.id, name="국어", code="KOR")
        subj_info = Subject(school_id=school.id, name="정보", code="INFO")
        subj_eng = Subject(school_id=school.id, name="영어", code="ENG")
        session.add_all([subj_korean, subj_info, subj_eng])
        await session.flush()

        # 6. Teachers & Users (교사 계정 및 프로필)
        # 관리자/교사: 홍길동
        user_hong = User(school_id=school.id, email="hong@kse.hs.kr", role=UserRole.SCHOOL_ADMIN)
        session.add(user_hong)
        await session.flush()

        teacher_hong = Teacher(
            id=user_hong.id,
            school_id=school.id,
            name="홍길동",
            phone_number="010-1234-5678",
            workspace_email="hong@kse.hs.kr",
            car_number="12가 3456",
            position="교무기획",
            homeroom_class_id=class_3_2.id,
            assigned_work="교무기획, 학적 관리",
            phone_visibility=VisibilityScope.ALL_STAFF,
            car_visibility=VisibilityScope.ADMIN_ONLY
        )
        session.add(teacher_hong)

        td_hong = TeacherDepartment(teacher_id=teacher_hong.id, department_id=dept_gyomu.id, is_primary=True)
        session.add(td_hong)

        # 교사: 김철수
        user_kim = User(school_id=school.id, email="kim@kse.hs.kr", role=UserRole.TEACHER)
        session.add(user_kim)
        await session.flush()

        teacher_kim = Teacher(
            id=user_kim.id,
            school_id=school.id,
            name="김철수",
            phone_number="010-2345-6789",
            workspace_email="kim@kse.hs.kr",
            position="교과교사",
            assigned_work="정보 교육, 정보화기기 관리"
        )
        session.add(teacher_kim)

        td_kim = TeacherDepartment(teacher_id=teacher_kim.id, department_id=dept_yeongu.id, is_primary=True)
        session.add(td_kim)
        await session.flush()

        # 플랫폼 관리자 (SUPER_ADMIN) - 신규 학교 온보딩(/api/v1/admin/schools) 등
        # 플랫폼 전역 관리 기능을 위한 부트스트랩 계정. 실제 운영에서는 최초 1회만
        # 수동으로 role을 SUPER_ADMIN으로 지정해주면 된다.
        user_platform_admin = User(school_id=school.id, email="platform-admin@kse.hs.kr", role=UserRole.SUPER_ADMIN)
        session.add(user_platform_admin)
        await session.flush()

        teacher_platform_admin = Teacher(
            id=user_platform_admin.id,
            school_id=school.id,
            name="플랫폼 관리자",
            workspace_email="platform-admin@kse.hs.kr",
            position="시스템 관리자",
            assigned_work="플랫폼 운영 및 타 학교 온보딩",
        )
        session.add(teacher_platform_admin)

        # 7. Timetable (시간표)
        # 화요일 1교시: 홍길동 - 3학년 2반 - 국어 - 302호
        tt_1 = Timetable(
            school_id=school.id,
            academic_year=2026,
            semester=2,
            day_of_week=DayOfWeek.TUE,
            period=1,
            teacher_id=teacher_hong.id,
            grade_id=grade_3.id,
            class_id=class_3_2.id,
            subject_id=subj_korean.id,
            room_id=room_302.id,
            lesson_type="일반수업"
        )
        # 화요일 3교시: 김철수 - 3학년 2반 - 정보 - 302호(기본교실) + 컴퓨터실 B(실습실)
        tt_2 = Timetable(
            school_id=school.id,
            academic_year=2026,
            semester=2,
            day_of_week=DayOfWeek.TUE,
            period=3,
            teacher_id=teacher_kim.id,
            grade_id=grade_3.id,
            class_id=class_3_2.id,
            subject_id=subj_info.id,
            room_id=room_302.id,
            practice_room_id=room_comp_b.id,
            lesson_type="실습수업"
        )
        session.add_all([tt_1, tt_2])

        # 8. Tasks (업무 및 일정 - 1사분면)
        now = datetime.datetime.utcnow()
        task_1 = Task(
            school_id=school.id,
            department_id=dept_gyomu.id,
            creator_id=user_hong.id,
            assignee_id=teacher_hong.id,
            title="교직원 회의 및 주간 업무 공유",
            description="2학기 학사일정 점검 및 부서별 협의",
            start_datetime=now.replace(hour=9, minute=0),
            due_datetime=now.replace(hour=10, minute=0),
            priority=TaskPriority.HIGH,
            status=TaskStatus.PENDING,
            visibility=VisibilityScope.ALL_STAFF
        )
        task_2 = Task(
            school_id=school.id,
            department_id=dept_yeongu.id,
            creator_id=user_hong.id,
            assignee_id=teacher_kim.id,
            title="3학년 2학기 평가계획서 제출",
            description="수행평가 및 지필평가 세부 기준 취합",
            start_datetime=now.replace(hour=10, minute=0),
            due_datetime=now.replace(hour=17, minute=0),
            priority=TaskPriority.URGENT,
            status=TaskStatus.IN_PROGRESS,
            visibility=VisibilityScope.ALL_STAFF
        )
        session.add_all([task_1, task_2])

        # 9. Shortcuts (바로가기 - 2사분면)
        shortcuts = [
            Shortcut(school_id=school.id, title="교무자료실", url="https://drive.google.com/drive/u/0/folders/1sulAaa2WDVqxePp3SlM7dmX3ofiww8pt", icon="folder", category="업무드라이브", sort_order=1),
            Shortcut(school_id=school.id, title="학교 업무 Sheets", url="https://docs.google.com/spreadsheets", icon="file-spreadsheet", category="공통문서", sort_order=2),
            Shortcut(school_id=school.id, title="NEIS (나이스)", url="https://neis.go.kr", icon="book-open", category="교육행정", sort_order=3),
            Shortcut(school_id=school.id, title="Gmail", url="https://mail.google.com", icon="mail", category="Google Workspace", sort_order=4),
            Shortcut(school_id=school.id, title="Google Calendar", url="https://calendar.google.com", icon="calendar", category="Google Workspace", sort_order=5),
            Shortcut(school_id=school.id, title="Google Drive", url="https://drive.google.com", icon="cloud", category="Google Workspace", sort_order=6)
        ]
        session.add_all(shortcuts)

        # 10. Messages (교직원 메시지 - 4사분면)
        msg_1 = Message(
            school_id=school.id,
            sender_id=teacher_kim.id,
            msg_type="ANNOUNCEMENT",
            title="컴퓨터실 사용 안내",
            content="오늘 3~4교시 컴퓨터실 B 수업 진행 예정입니다. 교재 준비 부탁드립니다."
        )
        session.add(msg_1)
        await session.flush()

        msg_rec = MessageRecipient(
            message_id=msg_1.id,
            recipient_id=teacher_hong.id,
            is_read=False
        )
        session.add(msg_rec)

        await session.commit()
    print("Database seeded with sample data successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
