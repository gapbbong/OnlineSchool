import datetime
import logging
from typing import List

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Department, Grade, School, SchoolSetting, Teacher, SyncAction, SyncTarget
from app.schemas.admin import SchoolCreateRequest, SchoolCreateResponse, SchoolSummaryResponse
from app.services.sync_queue import enqueue

logger = logging.getLogger("SchoolProvisioning")

# 마스터플랜 4-F 섹션의 Google Drive 폴더 계층과 1:1로 대응하는 기본 부서 템플릿.
# 학교마다 조직 구성이 다르므로 요청 시 department_names로 얼마든지 재정의할 수 있다.
DEFAULT_DEPARTMENTS: List[str] = [
    "교무부", "연구부", "학생부", "교육과정부", "진로진학부", "학년부", "평가", "관리자",
]


class SchoolProvisioningService:
    """타 학교 확장을 코드 변경 없이 API 호출 한 번으로 끝내기 위한 자동화 서비스.
    School/SchoolSetting/기본 학년/기본 부서를 함께 만들고, Drive 루트 폴더 ID가
    있으면 부서별 폴더 생성까지 비동기 큐에 적재한다."""

    @classmethod
    async def provision_school(cls, db: AsyncSession, actor_id: str, req: SchoolCreateRequest) -> SchoolCreateResponse:
        domain = req.workspace_domain.strip().lower()

        dup_domain = await db.execute(select(School).filter(func.lower(School.workspace_domain) == domain))
        if dup_domain.scalars().first():
            raise HTTPException(status_code=400, detail=f"'@{domain}' 도메인은 이미 등록되어 있습니다.")

        dup_code = await db.execute(select(School).filter(School.code == req.code))
        if dup_code.scalars().first():
            raise HTTPException(status_code=400, detail=f"학교 코드 '{req.code}'는 이미 사용 중입니다.")

        school = School(name=req.name, code=req.code, workspace_domain=domain, is_active=True)
        db.add(school)
        await db.flush()

        academic_year = req.academic_year or datetime.datetime.utcnow().year
        setting = SchoolSetting(
            school_id=school.id,
            google_drive_root_folder_id=req.google_drive_root_folder_id,
            google_client_id=req.google_client_id,
            current_academic_year=academic_year,
        )
        db.add(setting)

        # 학교급(초/중/고 등)에 따라 학년 수가 다양하므로 요청값(grade_count)을 그대로 반영한다.
        for grade_number in range(1, req.grade_count + 1):
            db.add(Grade(school_id=school.id, grade_number=grade_number, name=f"{grade_number}학년", academic_year=academic_year))

        dept_names = req.department_names if req.department_names else list(DEFAULT_DEPARTMENTS)
        departments = []
        for idx, dept_name in enumerate(dept_names, start=1):
            dept = Department(school_id=school.id, name=dept_name, sort_order=idx)
            db.add(dept)
            departments.append(dept)
        await db.flush()

        db.add(AuditLog(
            school_id=school.id, actor_id=actor_id, action="PROVISION_SCHOOL",
            target_type="SCHOOL", target_id=school.id,
            details={"name": school.name, "workspace_domain": domain, "department_count": len(departments)},
        ))

        # Drive 루트 폴더가 아직 없는 학교(Workspace 준비 전 단계)는 폴더 생성 작업을
        # 건너뛴다 - 나중에 SchoolSetting에 루트 폴더 ID를 채운 뒤 재실행하면 된다.
        enqueued = 0
        if setting.google_drive_root_folder_id:
            for dept in departments:
                await enqueue(
                    db,
                    school_id=school.id,
                    entity_type="DEPARTMENT",
                    entity_id=dept.id,
                    action=SyncAction.CREATE,
                    target=SyncTarget.DRIVE,
                    payload={
                        "school_root_folder_id": setting.google_drive_root_folder_id,
                        "dept_name": dept.name,
                    },
                )
                enqueued += 1

        await db.commit()

        message = f"'{school.name}' 학교가 등록되었습니다. 부서 {len(departments)}개, 학년 {req.grade_count}개가 자동 생성되었습니다."
        if not setting.google_drive_root_folder_id:
            message += " (Drive 루트 폴더 미설정 - 추후 설정 후 부서 폴더 자동 생성을 진행하세요.)"

        return SchoolCreateResponse(
            school_id=school.id,
            name=school.name,
            workspace_domain=domain,
            grades_created=req.grade_count,
            departments_created=len(departments),
            drive_sync_jobs_enqueued=enqueued,
            message=message,
        )

    @classmethod
    async def list_schools(cls, db: AsyncSession) -> List[SchoolSummaryResponse]:
        """타 학교 확장 현황을 한 화면에서 파악하기 위한 목록 (SUPER_ADMIN 전용)."""
        schools = (await db.execute(select(School).order_by(School.created_at.asc()))).scalars().all()

        summaries: List[SchoolSummaryResponse] = []
        for school in schools:
            teacher_count = (
                await db.execute(select(func.count()).select_from(Teacher).filter(Teacher.school_id == school.id))
            ).scalar_one()
            department_count = (
                await db.execute(select(func.count()).select_from(Department).filter(Department.school_id == school.id))
            ).scalar_one()
            setting = (
                (await db.execute(select(SchoolSetting).filter(SchoolSetting.school_id == school.id))).scalars().first()
            )

            summaries.append(SchoolSummaryResponse(
                school_id=school.id,
                name=school.name,
                code=school.code,
                workspace_domain=school.workspace_domain,
                is_active=school.is_active,
                teacher_count=teacher_count,
                department_count=department_count,
                drive_configured=bool(setting and setting.google_drive_root_folder_id),
                created_at=school.created_at.isoformat() if school.created_at else "",
            ))
        return summaries
