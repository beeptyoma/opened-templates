from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, HttpUrl
from models import ServiceStatus

class ServiceCreate(BaseModel):
    name: str = Field(max_length=255)
    category: str | None = Field(default=None, max_length=100)
    description: str | None = None
    endpoint_url: HttpUrl
    tags: list[str] = Field(default_factory=list)
    check_interval_seconds: int = Field(default=60, ge=10, le=86400)
    is_enabled: bool = True


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    description: str | None = None
    endpoint_url: HttpUrl | None = None
    tags: list[str] | None = None
    check_interval_seconds: int | None = Field(default=None, ge=10, le=86400)
    is_enabled: bool | None = None


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str | None
    description: str | None
    endpoint_url: str
    tags: list[str]
    check_interval_seconds: int
    is_enabled: bool
    created_at: datetime


class ServiceListItem(ServiceRead):
    current_status: ServiceStatus = ServiceStatus.unknown
    last_response_time_ms: float | None = None


class IncidentItem(BaseModel):
    checked_at: datetime
    status_code: int | None
    error_message: str | None


class ServiceStatsRead(BaseModel):
    service_id: int
    total_checks: int
    failed_checks: int
    avg_response_time_ms: float | None
    uptime_percentage: float
    current_status: ServiceStatus
    last_check_at: datetime | None
    last_success_at: datetime | None
    last_response_time_ms: float | None
    recent_incidents: list[IncidentItem]


class CheckHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status_code: int | None
    response_time_ms: float | None
    is_success: bool
    error_message: str | None
    checked_at: datetime


class DashboardServiceItem(BaseModel):
    id: int
    name: str
    current_status: ServiceStatus
    last_check_at: datetime | None
    last_success_at: datetime | None
    last_response_time_ms: float | None


class DashboardSummary(BaseModel):
    online: int
    degraded: int
    offline: int
    unknown: int


class DashboardRead(BaseModel):
    summary: DashboardSummary
    services: list[DashboardServiceItem]


class PublicServiceStatus(BaseModel):
    name: str
    category: str | None
    current_status: ServiceStatus
    uptime_percentage: float
    last_checked_at: datetime | None


class PublicStatusPage(BaseModel):
    summary: DashboardSummary
    services: list[PublicServiceStatus]
