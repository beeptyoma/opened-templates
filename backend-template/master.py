import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import Base, engine
from modules import api_router
from tasks import runner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s — %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    task = asyncio.create_task(runner.run())

    yield

    task.cancel()
    await engine.dispose()


app = FastAPI(title="backend-template", lifespan=lifespan)
app.include_router(api_router)


@app.get("/")
async def root() -> dict:
    return {"app": "backend-template"}
