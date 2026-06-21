import time
import httpx

from dataclasses import dataclass
from core.settings import settings

_client: httpx.AsyncClient | None = None

def init_http_client() -> None:
    global _client
    _client = httpx.AsyncClient(
        timeout=httpx.Timeout(
            connect=settings.HTTP_CONNECT_TIMEOUT_SECONDS,
            read=settings.HTTP_READ_TIMEOUT_SECONDS,
            write=settings.HTTP_READ_TIMEOUT_SECONDS,
            pool=settings.HTTP_CONNECT_TIMEOUT_SECONDS,
        ),
        follow_redirects=True,
    )

async def close_http_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None

def get_http_client() -> httpx.AsyncClient:
    assert _client is not None, "http client not initialized — call init_http_client() on startup"
    return _client

@dataclass
class CheckResult:
    status_code: int | None
    response_time_ms: float | None
    is_success: bool
    error_message: str | None

async def perform_check(endpoint_url: str) -> CheckResult:
    """Дергаем внешний сервис.

    5xx — "сервис жив, но плохо себя чувствует": is_success=False, но
    response_time всё равно меряем, т.к. ответ реально пришёл. Сетевой
    таймаут/обрыв соединения — отдельная ветка, там времени нет вообще.
    """
    started = time.perf_counter()
    try:
        response = await get_http_client().get(endpoint_url)
        elapsed_ms = (time.perf_counter() - started) * 1000
        return CheckResult(
            status_code=response.status_code,
            response_time_ms=round(elapsed_ms, 2),
            is_success=response.status_code < 500,
            error_message=None,
        )
    except httpx.TimeoutException:
        return CheckResult(None, None, False, "timeout")
    except httpx.HTTPError as exc:
        return CheckResult(None, None, False, str(exc))
