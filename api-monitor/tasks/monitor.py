import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis import get_redis
from core.settings import settings
from database import db
from models import Service, ServiceCheck, ServiceStatistics, ServiceStatus
from modules.checker import CheckResult, perform_check
from modules.notifications import notify_service_down

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 5
LOCK_KEY = "monitor:lock"

_task: asyncio.Task | None = None


def start() -> None:
    global _task
    if _task is None:
        _task = asyncio.create_task(_loop())


async def stop() -> None:
    global _task
    if _task is not None:
        _task.cancel()
        try:
            await _task
        except asyncio.CancelledError:
            pass
        _task = None


async def _loop() -> None:
    while True:
        try:
            if await _acquire_tick_lock():
                await _run_due_checks()
        except Exception:
            logger.exception("monitor loop tick failed")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _acquire_tick_lock() -> bool:
    """NX-лок с TTL.

    При одной реплике апи всегда побеждает сам. При нескольких — за тик
    реально опрашивает сервисы только тот инстанс, что успел поставить ключ
    первым, остальные тик пропускают. TTL = интервал тика, так что лок сам
    протухает к следующему раунду и не виснет, если инстанс упал.
    """
    return bool(await get_redis().set(LOCK_KEY, "1", nx=True, ex=POLL_INTERVAL_SECONDS))


async def _run_due_checks() -> None:
    now = datetime.now(UTC)
    async with db.session_factory() as session:
        rows = (
            await session.execute(
                select(
                    Service.id,
                    Service.check_interval_seconds,
                    ServiceStatistics.last_check_at,
                )
                .join(ServiceStatistics, isouter=True)
                .where(Service.is_enabled.is_(True))
            )
        ).all()

    due_ids = [
        service_id
        for service_id, interval, last_check_at in rows
        if last_check_at is None or (now - last_check_at).total_seconds() >= interval
    ]
    if due_ids:
        await asyncio.gather(*(check_and_store(service_id) for service_id in due_ids))


async def check_and_store(service_id: int) -> None:
    """Полный цикл одного чека: своя сессия на таск, чтобы конкурентные
    gather() чеки не делили один AsyncSession (он не потокобезопасен)."""
    async with db.session_factory() as session:
        service = await session.get(Service, service_id)
        if service is None or not service.is_enabled:
            return

        result = await perform_check(service.endpoint_url)

        session.add(
            ServiceCheck(
                service_id=service_id,
                status_code=result.status_code,
                response_time_ms=result.response_time_ms,
                is_success=result.is_success,
                error_message=result.error_message,
            )
        )

        stats = await session.get(ServiceStatistics, service_id)
        if stats is None:
            stats = ServiceStatistics(service_id=service_id)
            session.add(stats)

        stats.total_checks += 1
        if not result.is_success:
            stats.failed_checks += 1
        stats.uptime_percentage = (stats.total_checks - stats.failed_checks) / stats.total_checks * 100
        stats.last_check_at = datetime.now(UTC)
        stats.last_response_time_ms = result.response_time_ms
        if result.is_success:
            stats.last_success_at = stats.last_check_at

        previous_status = stats.current_status

        # avg по индексированному service_id — дешёвый агрегат, не инкрементальная
        # мат.формула с её edge-case'ами (null'ы на таймаутах и т.п.)
        avg_result = await session.execute(
            select(func.avg(ServiceCheck.response_time_ms)).where(
                ServiceCheck.service_id == service_id,
                ServiceCheck.response_time_ms.is_not(None),
            )
        )
        stats.avg_response_time_ms = avg_result.scalar()

        stats.current_status = await _determine_status(session, service_id, result)

        await session.commit()

        await get_redis().delete(f"stats:{service_id}", "dashboard", "status_page")

        if previous_status != ServiceStatus.offline and stats.current_status == ServiceStatus.offline:
            await notify_service_down(service.name, result.error_message)


async def _determine_status(session: AsyncSession, service_id: int, latest: CheckResult) -> ServiceStatus:
    if not latest.is_success:
        return ServiceStatus.offline

    recent = (
        await session.execute(
            select(ServiceCheck.is_success)
            .where(ServiceCheck.service_id == service_id)
            .order_by(ServiceCheck.checked_at.desc())
            .limit(settings.DEGRADED_LOOKBACK_CHECKS)
        )
    ).scalars().all()

    if any(not ok for ok in recent):
        return ServiceStatus.degraded
    if latest.response_time_ms is not None and latest.response_time_ms > settings.DEGRADED_RESPONSE_TIME_MS:
        return ServiceStatus.degraded
    return ServiceStatus.online
