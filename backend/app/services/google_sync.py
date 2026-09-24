import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("GoogleWorkspaceSync")


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
            return f"mock_folder_id_for_{dept_name}"
        except Exception as e:
            logger.error(f"[Drive Sync Failed] {e}")
            return None

    @classmethod
    async def dispatch(cls, target: str, action: str, entity_type: str, payload: Dict[str, Any]) -> bool:
        """SyncOutbox 워커에서 호출하는 단일 진입점.

        target/action/entity_type 조합이 늘어나도(신규 학교의 특수 요구사항 등)
        이 메서드 하나만 확장하면 되도록 라우팅을 한곳에 모아 둔다.
        """
        if target == "SHEETS" and entity_type == "TASK":
            return await cls.sync_task_to_sheets(payload, sheet_id=payload.get("google_sheet_id"))

        if target == "DRIVE" and entity_type == "DEPARTMENT" and action == "CREATE":
            folder_id = await cls.create_department_drive_folder(
                payload.get("school_root_folder_id", ""), payload.get("dept_name", "")
            )
            return folder_id is not None

        logger.warning(f"[Sync Dispatch] 처리 규칙이 없는 조합: target={target} action={action} entity_type={entity_type}")
        return False
