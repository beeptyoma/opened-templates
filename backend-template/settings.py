import os

from dotenv import load_dotenv

load_dotenv()

EXAMPLE_TASK_INTERVAL = int(os.getenv("EXAMPLE_TASK_INTERVAL", "30"))

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./dev.db")
# PostgreSQL — задать DATABASE_URL в .env при переходе на прод:
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname