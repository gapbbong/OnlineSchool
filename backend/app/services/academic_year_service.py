from typing import List

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, Class, Grade, SchoolSetting
from app.schemas.admin import (
    AcademicYearStructureResponse, AcademicYearTransitionRequest, AcademicYearTransitionResponse,
    GradeClassCount,
)


async def _get_setting_or_404(db: AsyncSession, school_id: str) -> SchoolSetting:
    res = await db.execute(select(SchoolSetting).filter(SchoolSetting.school_id == school_id))
    setting = res.scalars().first()
    if not setting:
        raise HTTPException(status_code=404, detail="학교 설정을 찾을 수 없습니다.")
    return setting


async def get_current_structure(db: AsyncSession, school_id: str) -> AcademicYearStructureResponse:
    """새 학년도 전환 마법사의 기본값(현재 학년도 반 개수)을 보여주기 위한 조회."""
    setting = await _get_setting_or_404(db, school_id)

    grades_res = await db.execute(
        select(Grade).filter(Grade.school_id == school_id, Grade.academic_year == setting.current_academic_year)
        .order_by(Grade.grade_number.asc())
    )
    grades = grades_res.scalars().all()

    counts: List[GradeClassCount] = []
    for grade in grades:
        class_count_res = await db.execute(select(func.count()).select_from(Class).filter(Class.grade_id == grade.id))
        counts.append(GradeClassCount(grade_number=grade.grade_number, class_count=class_count_res.scalar_one()))

    return AcademicYearStructureResponse(academic_year=setting.current_academic_year, grades=counts)


async def transition_academic_year(
    db: AsyncSession, school_id: str, actor_id: str, req: AcademicYearTransitionRequest
) -> AcademicYearTransitionResponse:
    """새 학년도용 Grade/Class를 새로 생성한다. 이전 학년도 Grade/Class/Timetable은
    academic_year로 구분되어 그대로 남아있어 나중에도 조회할 수 있다 (담임/시간표
    재배정은 관리자가 별도 화면에서 명시적으로 다시 지정 - 자동 승계하지 않음)."""
    setting = await _get_setting_or_404(db, school_id)
    previous_year = setting.current_academic_year

    if req.new_academic_year <= previous_year:
        raise HTTPException(status_code=400, detail=f"새 학년도는 현재 학년도({previous_year})보다 커야 합니다.")

    grade_class_counts = req.grade_class_counts
    if not grade_class_counts:
        current = await get_current_structure(db, school_id)
        grade_class_counts = current.grades
        if not grade_class_counts:
            raise HTTPException(status_code=400, detail="기준으로 삼을 이전 학년도 반 구조가 없습니다. grade_class_counts를 직접 지정해주세요.")

    grades_created = 0
    classes_created = 0
    for gc in grade_class_counts:
        grade = Grade(
            school_id=school_id,
            grade_number=gc.grade_number,
            name=f"{gc.grade_number}학년",
            academic_year=req.new_academic_year,
        )
        db.add(grade)
        await db.flush()
        grades_created += 1

        for class_number in range(1, gc.class_count + 1):
            db.add(Class(grade_id=grade.id, class_number=class_number, name=f"{class_number}반"))
            classes_created += 1

    setting.current_academic_year = req.new_academic_year

    db.add(AuditLog(
        school_id=school_id, actor_id=actor_id, action="ACADEMIC_YEAR_TRANSITION",
        target_type="SCHOOL_SETTING", target_id=setting.id,
        details={
            "previous_academic_year": previous_year,
            "new_academic_year": req.new_academic_year,
            "grades_created": grades_created,
            "classes_created": classes_created,
        },
    ))

    await db.commit()

    return AcademicYearTransitionResponse(
        previous_academic_year=previous_year,
        new_academic_year=req.new_academic_year,
        grades_created=grades_created,
        classes_created=classes_created,
        message=(
            f"{req.new_academic_year}학년도 반 구조가 생성되었습니다 (학년 {grades_created}개, 반 {classes_created}개). "
            f"{previous_year}학년도 데이터는 이력으로 그대로 조회 가능합니다. 담임/시간표는 별도로 새로 배정해주세요."
        ),
    )
