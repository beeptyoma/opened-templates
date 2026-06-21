from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from core.rate_limit import limiter
from core.redis import close_redis, init_redis
from core.settings import settings
from modules.checker import close_http_client, init_http_client
from modules.dashboard import router as dashboard_router
from modules.services import router as services_router
from modules.stats import router as stats_router
from tasks import monitor

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_http_client()
    init_redis()
    monitor.start()
    yield
    await monitor.stop()
    await close_redis()
    await close_http_client()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(services_router)
app.include_router(stats_router)
app.include_router(dashboard_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
