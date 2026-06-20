from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from schemas import UserCreate, UserRead


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def create_or_fetch(self, data: UserCreate) -> User:
        """Upsert: вернуть существующего пользователя либо создать нового
        (Создано как пример)"""

        user = await self.get_by_telegram_id(data.telegram_id)
        if user is not None:
            return user

        user = User(telegram_id=data.telegram_id, username=data.username)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user


router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(data: UserCreate, session: AsyncSession = Depends(get_db)) -> User:
    return await UserService(session).create_or_fetch(data)


@router.get("/{telegram_id}", response_model=UserRead)
async def get_user(telegram_id: int, session: AsyncSession = Depends(get_db)) -> User:
    user = await UserService(session).get_by_telegram_id(telegram_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
