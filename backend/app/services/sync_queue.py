import asyncio
import logging
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models import SyncAction, SyncOutbox, SyncOutboxStatus, SyncTarget, Task, WorkHandover
from app.services.google_sync import MOCK_FOLDER_ID_PREFIX, GoogleWorkspaceSyncService

logger = logging.getLogger("SyncOutboxWorker")


async def enqueue(
    db: AsyncSession,
    *,
    school_id: str,
    entity_type: str,
    entity_id: str,
    action: SyncAction,
    target: SyncTarget,
    payload: Optional[dict[str, Any]] = None,
) -> SyncOutbox:
    """동기화 작업을 아웃박스에 적재만 하고 즉시 반환한다 (호출부를 절대 막지 않음).
    실제 Google API 호출은 process_pending()을 도는 백그라운드 워커가 수행한다."""
    item = SyncOutbox(
        school_id=school_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        target=target,
        payload=payload or {},
        status=SyncOutboxStatus.PENDING,
    )
    db.add(item)
    await db.flush()
    return item


async def process_pending(db: AsyncSession, batch_size: Optional[int] = None) -> int:
    """대기 중인 아웃박스 항목을 처리한다. 실패해도 다른 항목/서비스 전체에 영향을 주지 않고,
    개별 항목만 재시도 횟수를 늘려 남겨둔다. 반환값은 이번 배치에서 성공 처리된 건수."""
    limit = batch_size or settings.SYNC_WORKER_BATCH_SIZE
    result = await db.execute(
        select(SyncOutbox).filter(SyncOutbox.status == SyncOutboxStatus.PENDING).limit(limit)
    )
    items = result.scalars().all()

    succeeded = 0
    for item in items:
        dispatch_result: Optional[str] = None
        try:
            dispatch_result = await GoogleWorkspaceSyncService.dispatch(
                target=item.target.value,
                action=item.action.value,
                entity_type=item.entity_type,
                payload=item.payload or {},
            )
        except Exception as exc:  # Google API 장애/네트워크 문제 등 - 절대 워커를 죽이지 않는다.
            item.last_error = str(exc)[:1000]

        ok = bool(dispatch_result)
        item.attempts += 1
        if ok:
            item.status = SyncOutboxStatus.SUCCESS
            item.last_error = None
            succeeded += 1
        elif item.attempts >= settings.SYNC_MAX_ATTEMPTS:
            item.status = SyncOutboxStatus.FAILED
            logger.error(
                f"[Sync Outbox] 재시도 한도 초과 - id={item.id} entity={item.entity_type}:{item.entity_id} "
                f"target={item.target.value}"
            )
        # 한도 미만 실패는 status를 PENDING으로 유지해 다음 워커 주기에 재시도한다.

        if item.entity_type == "TASK":
            task = await db.get(Task, item.entity_id)
            if task is not None:
                if ok:
                    task.sync_status = "SYNCED"
                elif item.status == SyncOutboxStatus.FAILED:
                    task.sync_status = "FAILED"
                # 재시도 여지가 남아있으면 PENDING 그대로 둔다.

        if item.entity_type == "WORK_HANDOVER" and ok:
            handover = await db.get(WorkHandover, item.entity_id)
            if handover is not None:
                handover.drive_folder_id = dispatch_result
                # 아직 실제 Google API 연동 전(목 응답)이면 클릭 시 404가 나는 가짜 링크를
                # 만들지 않는다 - 실제 연동이 붙으면 자연히 진짜 URL이 채워진다.
                if dispatch_result and not dispatch_result.startswith(MOCK_FOLDER_ID_PREFIX):
                    handover.drive_folder_url = f"https://drive.google.com/drive/folders/{dispatch_result}"

    if items:
        await db.commit()
    return succeeded


async def sync_worker_loop() -> None:
    """앱 수명 동안 도는 백그라운드 워커. 개별 배치 처리 중 예외가 나도 루프 자체는
    절대 멈추지 않도록 감싼다 (Google 쪽 장애가 온라인 교무실 서비스에 영향을 주지 않는다는
    설계 원칙의 핵심 구현부)."""
    logger.info("Sync outbox worker started.")
    while True:
        try:
            async with AsyncSessionLocal() as db:
                await process_pending(db)
        except asyncio.CancelledError:
            logger.info("Sync outbox worker stopped.")
            raise
        except Exception as exc:
            logger.error(f"[Sync Outbox Worker] 예상치 못한 오류(계속 실행): {exc}")

        await asyncio.sleep(settings.SYNC_WORKER_INTERVAL_SECONDS)
