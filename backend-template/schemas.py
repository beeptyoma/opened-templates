from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

# ---------------------------------------------------------------------------------------
# Default
# ---------------------------------------------------------------------------------------

class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampMixin(BaseModel):
    created_at: datetime
    updated_at: datetime | None = None


class StatusResponse(BaseModel):
    ok: bool = True
    detail: str | None = None


class Paginated(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int

# ---------------------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------------------


class UserCreate(ORMBase):
    telegram_id: int
    username: str | None = None


class UserRead(ORMBase, TimestampMixin):
    id: int
    telegram_id: int
    username: str | None = None
