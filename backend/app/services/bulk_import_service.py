from io import BytesIO
from typing import Any, Optional

from fastapi import HTTPException
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Department, Subject, UserRole
from app.schemas.bulk_import import BulkImportResponse, BulkImportRowResult
from app.schemas.onboarding import TeacherOnboardingRequest
from app.services.onboarding_service import TeacherOnboardingService

# 학교마다 부서/과목 구성이 달라 값 자체는 검증하지 않고, 참고 시트로 현재 학교의
# 실제 부서/과목 명칭을 함께 내려준다 - 오탈자로 인한 실패를 줄이기 위함.
TEMPLATE_HEADERS = [
    "이름*", "휴대폰번호*", "Workspace 이메일*", "차량번호", "부서명*",
    "직책", "담당업무", "담임학년", "담임반", "담당과목명",
    "권한(TEACHER/STAFF/DEPARTMENT_HEAD)",
]

SHEET_NAME = "교사일괄등록"


async def build_template_workbook(db: AsyncSession, school_id: str) -> bytes:
    """해당 학교의 실제 부서/과목 목록을 참고 시트로 포함한 일괄등록 엑셀 양식 생성."""
    wb = Workbook()
    ws = wb.active
    ws.title = SHEET_NAME
    ws.append(TEMPLATE_HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for col_idx in range(1, len(TEMPLATE_HEADERS) + 1):
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = 18

    dept_ws = wb.create_sheet("참고-부서목록")
    dept_ws.append(["부서명"])
    depts = (
        await db.execute(select(Department).filter(Department.school_id == school_id).order_by(Department.sort_order))
    ).scalars().all()
    for d in depts:
        dept_ws.append([d.name])

    subj_ws = wb.create_sheet("참고-과목목록")
    subj_ws.append(["과목명"])
    subjects = (await db.execute(select(Subject).filter(Subject.school_id == school_id))).scalars().all()
    for s in subjects:
        subj_ws.append([s.name])

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


async def _resolve_department_id(db: AsyncSession, school_id: str, dept_name: str) -> str:
    res = await db.execute(select(Department).filter(Department.school_id == school_id, Department.name == dept_name))
    dept = res.scalars().first()
    if not dept:
        raise ValueError(f"'{dept_name}' 부서를 찾을 수 없습니다. '참고-부서목록' 시트의 이름을 그대로 사용하세요.")
    return dept.id


async def _resolve_subject_id(db: AsyncSession, school_id: str, subject_name: str) -> str:
    res = await db.execute(select(Subject).filter(Subject.school_id == school_id, Subject.name == subject_name))
    subject = res.scalars().first()
    if not subject:
        raise ValueError(f"'{subject_name}' 과목을 찾을 수 없습니다. '참고-과목목록' 시트의 이름을 그대로 사용하세요.")
    return subject.id


def _to_int_or_none(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        raise ValueError(f"숫자여야 하는 값이 올바르지 않습니다: {value}")


async def _row_to_request(db: AsyncSession, school_id: str, row: dict) -> TeacherOnboardingRequest:
    name = str(row.get("이름*") or "").strip()
    phone = str(row.get("휴대폰번호*") or "").strip()
    email = str(row.get("Workspace 이메일*") or "").strip()
    dept_name = str(row.get("부서명*") or "").strip()

    missing = [
        label for label, value in [("이름", name), ("휴대폰번호", phone), ("Workspace 이메일", email), ("부서명", dept_name)]
        if not value
    ]
    if missing:
        raise ValueError(f"필수 항목 누락: {', '.join(missing)}")

    department_id = await _resolve_department_id(db, school_id, dept_name)

    subject_name = str(row.get("담당과목명") or "").strip()
    subject_id = await _resolve_subject_id(db, school_id, subject_name) if subject_name else None

    role_raw = str(row.get("권한(TEACHER/STAFF/DEPARTMENT_HEAD)") or "TEACHER").strip().upper()
    try:
        role = UserRole(role_raw)
    except ValueError:
        raise ValueError(f"알 수 없는 권한 값입니다: {role_raw} (TEACHER/STAFF/DEPARTMENT_HEAD/SCHOOL_ADMIN 중 하나)")

    return TeacherOnboardingRequest(
        name=name,
        phone_number=phone,
        workspace_email=email,
        car_number=(str(row.get("차량번호")).strip() if row.get("차량번호") else None),
        department_id=department_id,
        position=(str(row.get("직책")).strip() if row.get("직책") else "교과교사"),
        assigned_work=(str(row.get("담당업무")).strip() if row.get("담당업무") else None),
        homeroom_grade=_to_int_or_none(row.get("담임학년")),
        homeroom_class=_to_int_or_none(row.get("담임반")),
        subject_id=subject_id,
        role=role,
    )


async def parse_and_onboard_bulk(
    db: AsyncSession, school_id: str, actor_id: str, file_bytes: bytes
) -> BulkImportResponse:
    """업로드된 엑셀을 행 단위로 처리한다. 한 행이 실패해도(오탈자, 중복 이메일 등)
    나머지 행은 계속 처리되며, 실패 행만 세션을 롤백해 이전 성공 건에 영향을 주지 않는다."""
    try:
        wb = load_workbook(BytesIO(file_bytes), data_only=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="엑셀 파일을 읽을 수 없습니다. 올바른 .xlsx 파일인지 확인하세요.") from exc

    ws = wb[SHEET_NAME] if SHEET_NAME in wb.sheetnames else wb.worksheets[0]
    rows_iter = ws.iter_rows(min_row=1, values_only=True)
    try:
        header_row = list(next(rows_iter))
    except StopIteration:
        raise HTTPException(status_code=400, detail="빈 엑셀 파일입니다.")

    results: list[BulkImportRowResult] = []
    for excel_row_num, raw_row in enumerate(rows_iter, start=2):
        if raw_row is None or all(v is None or str(v).strip() == "" for v in raw_row):
            continue  # 빈 행은 건너뜀

        row = dict(zip(header_row, raw_row))
        name = str(row.get("이름*") or "").strip() or None

        try:
            req = await _row_to_request(db, school_id, row)
        except ValueError as exc:
            results.append(BulkImportRowResult(row=excel_row_num, name=name, success=False, error=str(exc)))
            continue

        try:
            onboarded = await TeacherOnboardingService.onboard_teacher(
                school_id=school_id, actor_id=actor_id, req=req, db=db
            )
            results.append(BulkImportRowResult(row=excel_row_num, name=req.name, success=True, message=onboarded.message))
        except HTTPException as exc:
            await db.rollback()
            results.append(BulkImportRowResult(row=excel_row_num, name=req.name, success=False, error=str(exc.detail)))
        except Exception as exc:
            await db.rollback()
            results.append(BulkImportRowResult(row=excel_row_num, name=req.name, success=False, error=str(exc)))

    succeeded = sum(1 for r in results if r.success)
    return BulkImportResponse(
        total_rows=len(results), succeeded=succeeded, failed=len(results) - succeeded, results=results
    )
