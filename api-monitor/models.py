import enum
from datetime import datetime
from sqlalchemy import ARRAY, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class ServiceStatus(str, enum.Enum):
    online = "online"
    degraded = "degraded"
    offline = "offline"
    unknown = "unknown"  # ни одного чека


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    endpoint_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    check_interval_seconds: Mapped[int] = mapped_column(Integer, default=60, server_default="60")

    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    checks: Mapped[list["ServiceCheck"]] = relationship(
        back_populates="service", cascade="all, delete-orphan", passive_deletes=True
    )
    statistics: Mapped["ServiceStatistics"] = relationship(
        back_populates="service", cascade="all, delete-orphan", passive_deletes=True, uselist=False
    )


class ServiceCheck(Base):
    """Сырой результат одного чека. Источник для /history и для расследования инцидентов."""

    __tablename__ = "service_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    service: Mapped["Service"] = relationship(back_populates="checks")


class ServiceStatistics(Base):
    """Агрегат 1:1 с Service, обновляется инкрементально на каждом чеке.

    Так стата читается за O(1) без сканирования service_checks; сами чеки
    остаются в истории отдельно для /history и инцидентов.
    """

    __tablename__ = "service_statistics"

    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), primary_key=True
    )
    total_checks: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    failed_checks: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    avg_response_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    uptime_percentage: Mapped[float] = mapped_column(Float, default=100.0, server_default="100")
    current_status: Mapped[ServiceStatus] = mapped_column(
        Enum(ServiceStatus, name="service_status"),
        default=ServiceStatus.unknown,
        server_default=ServiceStatus.unknown.value,
    )
    last_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_response_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    service: Mapped["Service"] = relationship(back_populates="statistics")
