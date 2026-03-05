"""
Модуль клиента для взаимодействия с API AI-консультанта.
Все HTTP-запросы к бэкенду инкапсулированы здесь.
При ошибках 4xx/5xx выбрасывается APIError с деталями из ответа сервера.
"""

import logging
from typing import Optional

import aiohttp

import config

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Исключение при ошибочном ответе API (4xx / 5xx)."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API error {status_code}: {detail}")


async def _raise_for_status(response: aiohttp.ClientResponse) -> None:
    """Бросает APIError, если статус ответа указывает на ошибку."""
    if response.status >= 400:
        try:
            body = await response.json()
            detail = body.get("detail", str(body))
        except Exception:
            detail = await response.text()
        raise APIError(status_code=response.status, detail=detail)


async def register() -> tuple[str, str]:
    """
    Регистрирует нового пользователя в API.

    Returns:
        Кортеж (user_id, api_key).

    Raises:
        APIError: При ошибке на стороне сервера.
    """
    url = f"{config.API_BASE_URL}/auth/register"
    async with aiohttp.ClientSession() as session:
        async with session.post(url) as response:
            await _raise_for_status(response)
            data = await response.json()
            logger.info("Зарегистрирован новый пользователь: user_id=%s", data.get("user_id"))
            return data["user_id"], data["api_key"]


async def send_text(
    user_id: str,
    api_key: str,
    message: str,
    image_bytes: Optional[bytes] = None,
    image_mime: Optional[str] = None,
) -> dict:
    """
    Отправляет текстовый запрос (с опциональным изображением) в API.

    Args:
        user_id: Идентификатор пользователя.
        api_key: Ключ API.
        message: Текст вопроса.
        image_bytes: Байты изображения (опционально).
        image_mime: MIME-тип изображения, например 'image/jpeg' (опционально).

    Returns:
        Полный JSON-ответ от API (content, source_chunks, …).

    Raises:
        APIError: При ошибке на стороне сервера.
    """
    url = f"{config.API_BASE_URL}/chat/text"
    headers = {"X-User-ID": user_id, "X-API-Key": api_key}

    form = aiohttp.FormData()
    form.add_field("message", message)
    if image_bytes is not None and image_mime is not None:
        form.add_field(
            "image",
            image_bytes,
            content_type=image_mime,
            filename="image.jpg",
        )

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=form) as response:
            await _raise_for_status(response)
            return await response.json()


async def send_audio(
    user_id: str,
    api_key: str,
    audio_bytes: bytes,
    image_bytes: Optional[bytes] = None,
    image_mime: Optional[str] = None,
) -> dict:
    """
    Отправляет голосовое сообщение (mp3) в API.

    Args:
        user_id: Идентификатор пользователя.
        api_key: Ключ API.
        audio_bytes: Байты аудио в формате mp3.
        image_bytes: Байты изображения (опционально).
        image_mime: MIME-тип изображения (опционально).

    Returns:
        JSON-ответ с полями transcription, content, source_chunks.

    Raises:
        APIError: При ошибке на стороне сервера.
    """
    url = f"{config.API_BASE_URL}/chat/audio"
    headers = {"X-User-ID": user_id, "X-API-Key": api_key}

    form = aiohttp.FormData()
    form.add_field(
        "audio",
        audio_bytes,
        content_type="audio/mpeg",
        filename="voice.mp3",
    )
    if image_bytes is not None and image_mime is not None:
        form.add_field(
            "image",
            image_bytes,
            content_type=image_mime,
            filename="image.jpg",
        )

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=form) as response:
            await _raise_for_status(response)
            return await response.json()


async def reset_memory(user_id: str, api_key: str) -> None:
    """
    Сбрасывает контекст диалога пользователя в API.

    Args:
        user_id: Идентификатор пользователя.
        api_key: Ключ API.

    Raises:
        APIError: При ошибке на стороне сервера.
    """
    url = f"{config.API_BASE_URL}/chat/memory"
    headers = {"X-User-ID": user_id, "X-API-Key": api_key}

    async with aiohttp.ClientSession() as session:
        async with session.delete(url, headers=headers) as response:
            await _raise_for_status(response)
            logger.info("Память сброшена для user_id=%s", user_id)
