import logging

from core.settings import settings
from modules.checker import get_http_client

logger = logging.getLogger(__name__)


async def notify_service_down(service_name: str, error_message: str | None) -> None:
    """Шлёт сообщение в Telegram, если в settings заданы токен и chat_id.

    Без конфига — молча no-op (фича опциональная и должна быть выключена by
    default). Падение самой отправки не должно ронять цикл мониторинга,
    поэтому исключения здесь только логируются.
    """
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return

    text = f"\U0001f534 {service_name} is DOWN"
    if error_message:
        text += f"\n{error_message}"

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        await get_http_client().post(url, json={"chat_id": settings.TELEGRAM_CHAT_ID, "text": text})
    except Exception:
        logger.exception("failed to send telegram notification")
