from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis import get_redis
from core.settings import settings
from database import get_session
from models import Service, ServiceStatistics, ServiceStatus
from schemas import (
    DashboardRead,
    DashboardServiceItem,
    DashboardSummary,
    PublicServiceStatus,
    PublicStatusPage,
)

router = APIRouter(tags=["dashboard"])

DASHBOARD_CACHE_KEY = "dashboard"
STATUS_PAGE_CACHE_KEY = "status_page"


async def _fetch_enabled_services_with_stats(
    session: AsyncSession,
) -> list[tuple[Service, ServiceStatistics | None]]:
    rows = (
        await session.execute(
            select(Service, ServiceStatistics)
            .join(ServiceStatistics, isouter=True)
            .where(Service.is_enabled.is_(True))
        )
    ).all()
    return list(rows)


def _status_counts(rows: list[tuple[Service, ServiceStatistics | None]]) -> dict[ServiceStatus, int]:
    counts: dict[ServiceStatus, int] = dict.fromkeys(ServiceStatus, 0)
    for _service, stats in rows:
        current_status = stats.current_status if stats is not None else ServiceStatus.unknown
        counts[current_status] += 1
    return counts


@router.get("/dashboard", response_model=DashboardRead)
async def get_dashboard(session: AsyncSession = Depends(get_session)) -> DashboardRead:
    cached = await get_redis().get(DASHBOARD_CACHE_KEY)
    if cached is not None:
        return DashboardRead.model_validate_json(cached)

    rows = await _fetch_enabled_services_with_stats(session)
    counts = _status_counts(rows)

    services = [
        DashboardServiceItem(
            id=service.id,
            name=service.name,
            current_status=(stats.current_status if stats else ServiceStatus.unknown),
            last_check_at=stats.last_check_at if stats else None,
            last_success_at=stats.last_success_at if stats else None,
            last_response_time_ms=stats.last_response_time_ms if stats else None,
        )
        for service, stats in rows
    ]

    result = DashboardRead(
        summary=DashboardSummary(
            online=counts[ServiceStatus.online],
            degraded=counts[ServiceStatus.degraded],
            offline=counts[ServiceStatus.offline],
            unknown=counts[ServiceStatus.unknown],
        ),
        services=services,
    )
    await get_redis().set(DASHBOARD_CACHE_KEY, result.model_dump_json(), ex=settings.CACHE_TTL_DASHBOARD_SECONDS)
    return result


@router.get("/status", response_model=PublicStatusPage)
async def get_public_status(session: AsyncSession = Depends(get_session)) -> PublicStatusPage:
    """Публичная status-page: без внутренних id, зато с аптаймом — то, что
    обычно показывают наружу (а-ля status.github.com)."""
    cached = await get_redis().get(STATUS_PAGE_CACHE_KEY)
    if cached is not None:
        return PublicStatusPage.model_validate_json(cached)

    rows = await _fetch_enabled_services_with_stats(session)
    counts = _status_counts(rows)

    services = [
        PublicServiceStatus(
            name=service.name,
            category=service.category,
            current_status=(stats.current_status if stats else ServiceStatus.unknown),
            uptime_percentage=stats.uptime_percentage if stats else 100.0,
            last_checked_at=stats.last_check_at if stats else None,
        )
        for service, stats in rows
    ]

    result = PublicStatusPage(
        summary=DashboardSummary(
            online=counts[ServiceStatus.online],
            degraded=counts[ServiceStatus.degraded],
            offline=counts[ServiceStatus.offline],
            unknown=counts[ServiceStatus.unknown],
        ),
        services=services,
    )
    await get_redis().set(STATUS_PAGE_CACHE_KEY, result.model_dump_json(), ex=settings.CACHE_TTL_DASHBOARD_SECONDS)
    return result
