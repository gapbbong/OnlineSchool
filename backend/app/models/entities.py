import uuid
import datetime
from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, ForeignKey, 
    Text, Enum as SAEnum, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

# ----------------- Enums -----------------
class UserRole(str, enum.Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    SCHOOL_ADMIN = "SCHOOL_ADMIN"
    DEPARTMENT_HEAD = "DEPARTMENT_HEAD"
    TEACHER = "TEACHER"
    STAFF = "STAFF"
    READ_ONLY = "READ_ONLY"

class TeacherStatus(str, enum.Enum):
    EMPLOYED = "EMPLOYED"       # 재직
    ON_LEAVE = "ON_LEAVE"       # 휴직
    RETIRED = "RETIRED"         # 퇴직

class VisibilityScope(str, enum.Enum):
    ALL_STAFF = "ALL_STAFF"
    SAME_DEPT = "SAME_DEPT"
    ADMIN_ONLY = "ADMIN_ONLY"
    SPECIFIC = "SPECIFIC"

class TaskPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"         # 예정
    IN_PROGRESS = "IN_PROGRESS" # 진행중
    COMPLETED = "COMPLETED"     # 완료
    ON_HOLD = "ON_HOLD"         # 보류
    CANCELLED = "CANCELLED"     # 취소

class DayOfWeek(str, enum.Enum):
    MON = "MON"
    TUE = "TUE"
    WED = "WED"
    THU = "THU"
    FRI = "FRI"
    SAT = "SAT"

class RoomType(str, enum.Enum):
    GENERAL = "GENERAL"         # 일반교실
    SPECIAL = "SPECIAL"         # 특별실
    LAB = "LAB"                 # 실습실
    COMPUTER = "COMPUTER"       # 컴퓨터실
    GYM = "GYM"                 # 체육관
    OTHER = "OTHER"             # 기타

class SyncTarget(str, enum.Enum):
    SHEETS = "SHEETS"
    DRIVE = "DRIVE"

class SyncAction(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"

class SyncOutboxStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"          # 재시도 한도 초과 - 수동 확인 필요

# ----------------- Models -----------------

class School(Base):
    """학교 (Tenant 원본)"""
    __tablename__ = "schools"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, nullable=False, index=True)
    workspace_domain = Column(String(100), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    settings = relationship("SchoolSetting", back_populates="school", uselist=False, cascade="all, delete-orphan")
    users = relationship("User", back_populates="school", cascade="all, delete-orphan")
    departments = relationship("Department", back_populates="school", cascade="all, delete-orphan")
    grades = relationship("Grade", back_populates="school", cascade="all, delete-orphan")
    rooms = relationship("Room", back_populates="school", cascade="all, delete-orphan")
    subjects = relationship("Subject", back_populates="school", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="school", cascade="all, delete-orphan")
    shortcuts = relationship("Shortcut", back_populates="school", cascade="all, delete-orphan")


class SchoolSetting(Base):
    """학교별 상세 설정 (Google Workspace, Drive Root ID 등 하드코딩 제거 대상)"""
    __tablename__ = "school_settings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    school_id = Column(String(36), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Google Workspace / Drive / Sheets
    google_drive_root_folder_id = Column(String(200), nullable=True)
    google_workspace_enabled = Column(Boolean, default=True)
    google_drive_enabled = Column(Boolean, default=True)
    google_sheets_enabled = Column(Boolean, default=True)
    google_calendar_enabled = Column(Boolean, default=True)
    
    # OAuth Credentials (학교별 별도 클라이언트 사용 시 암호화 저장)
    google_client_id = Column(String(200), nullable=True)
    google_client_secret = Column(String(200), nullable=True)

    # 개인정보 기본 공개 정책 (JSON)
    privacy_policy = Column(JSON, default=lambda: {
        "phone_default": "ALL_STAFF",
        "car_default": "ADMIN_ONLY"
    })

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    school = relationship("School", back_populates="settings")


class User(Base):
    """시스템 계정"""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    school_id = Column(String(36), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(120), nullable=False, index=True)
    hashed_password = Column(String(200), nullable=True)
    role = Column(SAEnum(UserRole), default=UserRole.TEACHER, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("school_id", "email", name="uq_user_school_email"),
    )

    school = relationship("School", back_populates="users")
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Teacher(Base):
    """교직원 상세 프로필"""
    __tablename__ = "teachers"

    id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    school_id = Column(String(36), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(50), nullable=False, index=True)
    photo_url = Column(String(255), nullable=True)
    phone_number = Column(String(30), nullable=True)
    workspace_email = Column(String(120), nullable=True)
    car_number = Column(String(30), nullable=True)
    position = Column(String(50), nullable=True)  # 부장, 기획, 계원 등
    
    # 담임 / 부담임 반 연결
    homeroom_class_id = Column(String(36), ForeignKey("classes.id", ondelete="SET NULL"), nullable=True)
    vice_homeroom_class_id = Column(String(36), ForeignKey("classes.id", ondelete="SET NULL"), nullable=True)
    
    assigned_work = Column(String(200), nullable=True) # 담당업무 (예: 방과후학교, 정보보안 등)
    status = Column(SAEnum(TeacherStatus), default=TeacherStatus.EMPLOYED)
    
    # 개인정보 공개범위 설정
    phone_visibility = Column(SAEnum(VisibilityScope), default=VisibilityScope.ALL_STAFF)
    car_visibility = Column(SAEnum(VisibilityScope), default=VisibilityScope.ADMIN_ONLY)
    email_visibility = Column(SAEnum(VisibilityScope), default=VisibilityScope.ALL_STAFF)
    
    memo = Column(Text, nullable=True)
    hire_date = Column(DateTime, nullable=True)
    retire_date = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    user = relationship("User", back_populates="teacher_profile")
    departments = relationship("TeacherDepartment", back_populates="teacher", cascade="all, delete-orphan")
    timetables = relationship("Timetable", back_populates="teacher")


class Department(Base):
    """교무부, 연구부, 학생부 등 교직원 부서"""
    __tablename__ = "departments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    school_id = Column(String(36), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), nullable=True)
    drive_folder_id = Column(String(200), nullable=True)  # Google Drive 전용 부서 폴더
    head_teacher_id = Column(String(36), ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    sort_order = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    school = relationship("School", back_populates="departments")
    members = relationship("TeacherDepartment", back_populates="department", cascade="all, delete-orphan")


class TeacherDepartment(Base):
    """교사-부서 M:N 연결 (주 소속부서 여부 플래그 포함)"""
    __tablename__ = "teacher_departments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    teacher_id = Column(String(36), ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    department_id = Column(String(36), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    is_primary = Column(Boolean, default=True)

    teacher = relationship("Teacher", back_populates="departments")
    department = relationship("Department", back_populates="members")


class Grade(Base):
    """학년 (1학년, 2학년, 3학년)"""
    __tablename__ = "grades"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    school_id = Column(String(36), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    grade_number = Column(Integer, nullable=False)  # 1, 2, 3
    name = Column(String(50), nullable=False)       # "1학년"

    school = relationship("School", back_populates="grades")
    classes = relationship("Class", back_populates="grade", cascade="all, delete-orphan")


class Class(Base):
    """반 (1반, 2반, ...)"""
    __tablename__ = "classes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    grade_id = Column(String(36), ForeignKey("grades.id", ondelete="CASCADE"), nullable=False)
    class_number = Column(Integer, nullable=False)
    name = Column(String(50), nullable=False)  # "1반", "2반"
    
    grade = relationship("Grade", back_populates="classes")
    timetables = relationship("Timetable", back_populates="class_obj")


class Subject(Base):
    """교과목 (국어, 수학, 정보 등)"""
    __tablename__ = "subjects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    school_id = Column(String(36), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), nullable=True)

    school = relationship("School", back_populates="subjects")


class Room(Base):
    """교실 / 실습실 / 특별실"""
    __tablename__ = "rooms"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    school_id = Column(String(36), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    room_name = Column(String(100), nullable=False)  # 302호, 컴퓨터실 B
    building = Column(String(50), nullable=True)     # 본관, 신관 등
    floor = Column(Integer, nullable=True)           # 3층
    capacity = Column(Integer, default=30)
    room_type = Column(SAEnum(RoomType), default=RoomType.GENERAL)
    equipment = Column(String(255), nullable=True)   # 전자칠판, 빔프로젝터, PC 35대 등
    description = Column(Text, nullable=True)

    school = relationship("School", back_populates="rooms")


class Timetable(Base):
    """시간표 (핵심 관계형 엔티티)"""
    __tablename__ = "timetables"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    school_id = Column(String(36), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    academic_year = Column(Integer, default=2026, nullable=False)
    semester = Column(Integer, default=1, nullable=False)
    
    day_of_week = Column(SAEnum(DayOfWeek), nullable=False)
    period = Column(Integer, nullable=False)  # 1~7교시

    teacher_id = Column(String(36), ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    grade_id = Column(String(36), ForeignKey("grades.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(String(36), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(String(36), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    
    room_id = Column(String(36), ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True) # 기본교실
    practice_room_id = Column(String(36), ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True) # 실습실
    lesson_type = Column(String(50), default="일반수업")

    teacher = relationship("Teacher", back_populates="timetables")
    class_obj = relationship("Class", back_populates="timetables")
    subject = relationship("Subject")
    room = relationship("Room", foreign_keys=[room_id])
    practice_room = relationship("Room", foreign_keys=[practice_room_id])


class Task(Base):
    """업무 & 캘린더 일정 (1사분면)"""
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    school_id = Column(String(36), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id = Column(String(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    creator_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assignee_id = Column(String(36), ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=True)
    due_datetime = Column(DateTime, nullable=True)

    priority = Column(SAEnum(TaskPriority), default=TaskPriority.MEDIUM)
    status = Column(SAEnum(TaskStatus), default=TaskStatus.PENDING)
    visibility = Column(SAEnum(VisibilityScope), default=VisibilityScope.ALL_STAFF)

    # Google Workspace 비동기 동기화 필드
    google_drive_folder_id = Column(String(200), nullable=True)
    google_sheet_id = Column(String(200), nullable=True)
    google_calendar_event_id = Column(String(200), nullable=True)
    sync_status = Column(String(20), default="SYNCED") # PENDING, SYNCED, FAILED

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    school = relationship("School", back_populates="tasks")
    department = relationship("Department")
    creator = relationship("User", foreign_keys=[creator_id])
    assignee = relationship("Teacher", foreign_keys=[assignee_id])


class Shortcut(Base):
    """자주 쓰는 바로가기 (2사분면)"""
    __tablename__ = "shortcuts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    school_id = Column(String(36), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(100), nullable=False)
    url = Column(String(500), nullable=False)
    icon = Column(String(50), default="link") # Lucide 아이콘 이름
    category = Column(String(50), default="학교공통")
    sort_order = Column(Integer, default=0)
    visibility = Column(SAEnum(VisibilityScope), default=VisibilityScope.ALL_STAFF)
    target_department_id = Column(String(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)

    school = relationship("School", back_populates="shortcuts")


class Message(Base):
    """교직원 메시지 및 공지 (4사분면)"""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    school_id = Column(String(36), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(String(36), ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    
    msg_type = Column(String(20), default="ANNOUNCEMENT") # ANNOUNCEMENT, DEPARTMENT, DIRECT
    target_department_id = Column(String(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)

    title = Column(String(200), nullable=True)
    content = Column(Text, nullable=False)
    attachment_url = Column(String(500), nullable=True)

    # 업무 캘린더/시간표(교실·실습실 포함)를 메시지에 바로 첨부해 링크로 보여주기 위한 참조.
    # 기존 학교 메신저 대체를 위해, 딱딱한 텍스트 대신 클릭 가능한 카드로 노출한다.
    linked_task_id = Column(String(36), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    linked_timetable_id = Column(String(36), ForeignKey("timetables.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    sender = relationship("Teacher", foreign_keys=[sender_id])
    recipients = relationship("MessageRecipient", back_populates="message", cascade="all, delete-orphan")
    linked_task = relationship("Task", foreign_keys=[linked_task_id])
    linked_timetable = relationship("Timetable", foreign_keys=[linked_timetable_id])


class MessageRecipient(Base):
    """수신자 및 읽음 여부"""
    __tablename__ = "message_recipients"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    message_id = Column(String(36), ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    recipient_id = Column(String(36), ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)

    message = relationship("Message", back_populates="recipients")


class SyncOutbox(Base):
    """Google Sheets/Drive 비동기 동기화 아웃박스 (재시도 큐).

    교무실 DB를 원본(Source of Truth)으로 유지하기 위해, Google API 호출은 요청
    처리 흐름과 분리된 별도 워커가 이 테이블을 폴링하며 비동기로 수행한다.
    Google 측 장애/지연이 있어도 본 서비스의 쓰기 트랜잭션은 절대 막히지 않는다.
    """
    __tablename__ = "sync_outbox"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    school_id = Column(String(36), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)

    entity_type = Column(String(50), nullable=False)   # TASK, DEPARTMENT 등
    entity_id = Column(String(36), nullable=False)
    action = Column(SAEnum(SyncAction), nullable=False)
    target = Column(SAEnum(SyncTarget), nullable=False)
    payload = Column(JSON, nullable=True)

    status = Column(SAEnum(SyncOutboxStatus), default=SyncOutboxStatus.PENDING, nullable=False, index=True)
    attempts = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class WorkHandover(Base):
    """업무 인수인계 단위 (담당업무 기준).

    담당자(교사)가 바뀌어도 Google Drive 폴더와 인수인계 메모가 그대로 이어지도록,
    사람이 아니라 "업무" 자체를 기준으로 폴더/메모를 관리한다. 연말 인사이동 시
    current_teacher_id만 새 담당자로 바꾸면 폴더/이력이 자동으로 승계된다."""
    __tablename__ = "work_handovers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    school_id = Column(String(36), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    department_id = Column(String(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    work_title = Column(String(200), nullable=False)  # 예: "방과후학교 담당", "정보보안 담당"
    current_teacher_id = Column(String(36), ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)

    drive_folder_id = Column(String(200), nullable=True)
    drive_folder_url = Column(String(500), nullable=True)

    # 인수인계 메모 - 새 항목이 맨 위에 쌓이는 타임스탬프 로그 형식 텍스트
    handover_note = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    school = relationship("School")
    department = relationship("Department")
    current_teacher = relationship("Teacher", foreign_keys=[current_teacher_id])


class AuditLog(Base):
    """감사 로그"""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    school_id = Column(String(36), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(String(36), nullable=False) # User ID
    action = Column(String(50), nullable=False)   # e.g., UPDATE_TEACHER, DELETE_TASK
    target_type = Column(String(50), nullable=False)
    target_id = Column(String(36), nullable=False)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class UsageEvent(Base):
    """기능 사용 로그 (감사 로그와 별개) - 어떤 화면/기능이 실제로 얼마나 쓰이는지
    파악해 개선 우선순위를 잡기 위한 용도. 감사 로그처럼 '누가 무엇을 바꿨는지'가
    아니라 '무엇을 얼마나 자주 보고/썼는지'를 기록한다."""
    __tablename__ = "usage_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    school_id = Column(String(36), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True)
    teacher_id = Column(String(36), ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True)
    event_type = Column(String(50), nullable=False, index=True)  # 예: VIEW_CALENDAR_WEEK, SEND_MESSAGE_DIRECT
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
