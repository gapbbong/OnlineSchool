import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("GoogleWorkspaceSync")

# 실제 Google API 연동 전까지 반환되는 목(mock) 폴더 ID 접두사. sync_queue가 이 접두사를
# 보고 "실제 Drive에 존재하지 않는 폴더"를 구분해, 클릭하면 404가 나는 가짜 링크를
# 사용자에게 보여주지 않도록 한다.
MOCK_FOLDER_ID_PREFIX = "mock_folder_id_for_"


class GoogleWorkspaceSyncService:
    """
    Google Workspace 비동기 동기화 서비스 (Outbox & Non-blocking)

    핵심 원칙:
    1. 온라인 교무실 DB가 Source of Truth
    2. Google Drive / Sheets 연동 실패 시에도 메인 서비스는 100% 정상 작동
    3. 실패 건은 SyncOutbox 비동기 재시도 큐에 적재 (app.services.sync_queue)

    실제 Google API 호출부(sheets/drive 클라이언트 초기화 및 요청)는 학교별
    google_client_id/secret, 서비스 계정 연동 방식이 정해지는 대로 이 클래스
    내부에서만 교체하면 되도록 인터페이스를 고정해 둔다.
    """

    @classmethod
    async def sync_task_to_sheets(cls, task_data: Dict[str, Any], sheet_id: Optional[str] = None) -> bool:
        """업무 생성/수정 시 Google Sheets '학교업무관리'에 한 행 추가/동기화"""
        try:
            # Google Sheets API 연동 로직
            # 컬럼: 날짜 | 부서 | 업무명 | 담당자 | 마감일 | 상태
            logger.info(f"[Sheets Sync] Syncing Task '{task_data.get('title')}' to Sheet ID: {sheet_id or 'DEFAULT_SHEET'}")
            return True
        except Exception as e:
            logger.error(f"[Sheets Sync Failed] {e}")
            return False

    @classmethod
    async def create_department_drive_folder(cls, school_root_folder_id: str, dept_name: str) -> Optional[str]:
        """부서 생성 시 Google Drive 내 전용 부서 폴더 자동 프로비저닝"""
        try:
            logger.info(f"[Drive Sync] Creating folder '{dept_name}' under root '{school_root_folder_id}'")
            # Google Drive API files.create(mimeType='application/vnd.google-apps.folder')
            return f"{MOCK_FOLDER_ID_PREFIX}{dept_name}"
        except Exception as e:
            logger.error(f"[Drive Sync Failed] {e}")
            return None

    @classmethod
    async def dispatch(cls, target: str, action: str, entity_type: str, payload: Dict[str, Any]) -> Optional[str]:
        """SyncOutbox 워커에서 호출하는 단일 진입점.

        target/action/entity_type 조합이 늘어나도(신규 학교의 특수 요구사항 등)
        이 메서드 하나만 확장하면 되도록 라우팅을 한곳에 모아 둔다.
        반환값이 falsy(None)이면 실패, truthy면 성공이며 - Drive 폴더 생성류는 생성된
        folder_id를 그대로 반환해 호출부(sync_queue)가 엔티티에 다시 기록할 수 있게 한다.
        """
        if target == "SHEETS" and entity_type == "TASK":
            ok = await cls.sync_task_to_sheets(payload, sheet_id=payload.get("google_sheet_id"))
            return "SYNCED" if ok else None

        if target == "DRIVE" and entity_type == "DEPARTMENT" and action == "CREATE":
            return await cls.create_department_drive_folder(
                payload.get("school_root_folder_id", ""), payload.get("dept_name", "")
            )

        if target == "DRIVE" and entity_type == "WORK_HANDOVER" and action == "CREATE":
            return await cls.create_department_drive_folder(
                payload.get("parent_folder_id", ""), payload.get("work_title", "")
            )

        logger.warning(f"[Sync Dispatch] 처리 규칙이 없는 조합: target={target} action={action} entity_type={entity_type}")
        return None
