from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from core.settings import settings

class Database:
    _instance: "Database | None" = None

    def __init__(self) -> None:
        self.engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, pool_pre_ping=True)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    @classmethod
    def get(cls) -> "Database":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def dispose(self) -> None:
        await self.engine.dispose()


db = Database.get()

async def get_session() -> AsyncIterator[AsyncSession]:
    async with db.session_factory() as session:
        yield session
