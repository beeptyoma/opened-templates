from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis import get_redis
from core.settings import settings
from database import get_session
from models import Service, ServiceCheck, ServiceStatistics
from schemas import CheckHistoryItem, IncidentItem, ServiceStatsRead

router = APIRouter(prefix="/services", tags=["stats"])

@router.get("/{service_id}/stats", response_model=ServiceStatsRead)
async def get_service_stats(service_id: int, session: AsyncSession = Depends(get_session)) -> ServiceStatsRead:
    cache_key = f"stats:{service_id}"
    cached = await get_redis().get(cache_key)
    if cached is not None:
        return ServiceStatsRead.model_validate_json(cached)

    service = await session.get(Service, service_id)
    if service is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found")

    stats = await session.get(ServiceStatistics, service_id)
    if stats is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No statistics yet for this service")

    incidents = (
        await session.execute(
            select(ServiceCheck)
            .where(ServiceCheck.service_id == service_id, ServiceCheck.is_success.is_(False))
            .order_by(ServiceCheck.checked_at.desc())
            .limit(5)
        )
    ).scalars().all()

    result = ServiceStatsRead(
        service_id=service_id,
        total_checks=stats.total_checks,
        failed_checks=stats.failed_checks,
        avg_response_time_ms=stats.avg_response_time_ms,
        uptime_percentage=stats.uptime_percentage,
        current_status=stats.current_status,
        last_check_at=stats.last_check_at,
        last_success_at=stats.last_success_at,
        last_response_time_ms=stats.last_response_time_ms,
        recent_incidents=[
            IncidentItem(checked_at=row.checked_at, status_code=row.status_code, error_message=row.error_message)
            for row in incidents
        ],
    )
    await get_redis().set(cache_key, result.model_dump_json(), ex=settings.CACHE_TTL_STATS_SECONDS)
    return result

@router.get("/{service_id}/history", response_model=list[CheckHistoryItem])
async def get_service_history(
    service_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    only_failures: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
) -> list[ServiceCheck]:
    service = await session.get(Service, service_id)
    if service is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found")

    stmt = select(ServiceCheck).where(ServiceCheck.service_id == service_id)
    if only_failures:
        stmt = stmt.where(ServiceCheck.is_success.is_(False))
    stmt = stmt.order_by(ServiceCheck.checked_at.desc()).limit(limit)

    return (await session.execute(stmt)).scalars().all()
