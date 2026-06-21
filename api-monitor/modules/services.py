from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from models import Service, ServiceStatistics
from schemas import ServiceCreate, ServiceListItem, ServiceRead, ServiceUpdate

router = APIRouter(prefix="/services", tags=["services"])

@router.post("", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
async def create_service(payload: ServiceCreate, session: AsyncSession = Depends(get_session)) -> Service:
    existing = await session.scalar(select(Service).where(Service.name == payload.name))
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Service '{payload.name}' already exists")

    service = Service(
        name=payload.name,
        category=payload.category,
        description=payload.description,
        endpoint_url=str(payload.endpoint_url),
        tags=payload.tags,
        check_interval_seconds=payload.check_interval_seconds,
        is_enabled=payload.is_enabled,
    )
    session.add(service)
    await session.flush()
    # сразу заводим строку статистики — чтобы /stats не падал 404 на свежесозданном сервисе
    session.add(ServiceStatistics(service_id=service.id))
    await session.commit()
    await session.refresh(service)
    return service


@router.get("", response_model=list[ServiceListItem])
async def list_services(
    category: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    enabled_only: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
) -> list[ServiceListItem]:
    stmt = select(Service, ServiceStatistics).join(ServiceStatistics, isouter=True)
    if category:
        stmt = stmt.where(Service.category == category)
    if tag:
        stmt = stmt.where(Service.tags.contains([tag]))
    if enabled_only:
        stmt = stmt.where(Service.is_enabled.is_(True))
    stmt = stmt.order_by(Service.id)

    rows = (await session.execute(stmt)).all()
    result: list[ServiceListItem] = []
    for service, stats in rows:
        item = ServiceListItem.model_validate(service)
        if stats is not None:
            item.current_status = stats.current_status
            item.last_response_time_ms = stats.last_response_time_ms
        result.append(item)
    return result


@router.get("/{service_id}", response_model=ServiceRead)
async def get_service(service_id: int, session: AsyncSession = Depends(get_session)) -> Service:
    service = await session.get(Service, service_id)
    if service is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found")
    return service


@router.patch("/{service_id}", response_model=ServiceRead)
async def update_service(
    service_id: int, payload: ServiceUpdate, session: AsyncSession = Depends(get_session)
) -> Service:
    service = await session.get(Service, service_id)
    if service is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found")

    data = payload.model_dump(exclude_unset=True)
    if "endpoint_url" in data:
        data["endpoint_url"] = str(data["endpoint_url"])
    for field, value in data.items():
        setattr(service, field, value)

    await session.commit()
    await session.refresh(service)
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(service_id: int, session: AsyncSession = Depends(get_session)) -> None:
    service = await session.get(Service, service_id)
    if service is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found")
    await session.delete(service)
    await session.commit()
