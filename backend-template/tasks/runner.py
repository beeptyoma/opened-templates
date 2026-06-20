import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

import settings
from database import AsyncSessionFactory

logger = logging.getLogger(__name__)

# Почему не Celery указано в README.md

async def _example_task(db: AsyncSession) -> None:
    """Заглушка периодической задачи, заменить на реальную логику."""
    while True:
        try:
            logger.debug("example task tick")

        except Exception as e:
            logger.error("example task failed: %s", e)

        await asyncio.sleep(settings.EXAMPLE_TASK_INTERVAL)


async def run() -> None:
    async with AsyncSessionFactory() as db:
        await asyncio.gather(
            _example_task(db),
        )
