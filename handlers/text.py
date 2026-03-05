"""
Хэндлеры текстовых сообщений и изображений с подписью.
Обрабатывает обычные текстовые вопросы и фотографии с текстовой подписью,
отправляя их в API и форматируя ответ для пользователя.
"""

import logging
from io import BytesIO

from aiogram import Bot, Router, F
from aiogram.enums import ChatAction
from aiogram.types import Message

import api_client
import storage

logger = logging.getLogger(__name__)

router = Router()

MAX_MESSAGE_LENGTH = 4096
DEFAULT_PHOTO_CAPTION = "Что изображено на этом фото?"


def _format_response(data: dict) -> str:
    """
    Формирует итоговый текст ответа из данных API.
    Выводит ответ и содержимое только использованных источников в виде свернутых цитат.
    """
    content = data.get("content", "").strip()
    if not content:
        return "Не удалось получить ответ. Попробуйте переформулировать вопрос."

    source_chunks = data.get("source_chunks", [])
    used_indices = data.get("used_chunk_indices", [])
    
    if not source_chunks or not used_indices:
        return content

    # Фильтруем только использованные чанки
    used_chunks = []
    for i, chunk in enumerate(source_chunks):
        if i in used_indices:
            used_chunks.append(chunk)
    
    if not used_chunks:
        return content

    # Формируем блок с источниками
    sources_lines = ["\n\n📎 Источники:"]
    for chunk in used_chunks:
        name = chunk.get("source", chunk.get("filename", "Документ"))
        chunk_content = chunk.get("content", "").strip()
        
        # Очищаем от markdown разметки для компактности
        chunk_content = chunk_content.replace("**", "").replace("*", "").replace("---", "")
        
        # Формируем строку с названием и свернутым содержимым
        sources_lines.append(f"\n<b>{name}</b>")
        sources_lines.append(f"\n<blockquote expandable>{chunk_content}</blockquote>")

    return content + "".join(sources_lines)


def _error_text(e: api_client.APIError) -> str:
    """Возвращает понятное русскоязычное сообщение об ошибке API."""
    if e.status_code == 401:
        return "⚠️ Ошибка авторизации. Попробуйте /start для перерегистрации."
    if e.status_code == 503:
        return "⚠️ Сервис временно недоступен. Попробуйте чуть позже."
    return f"⚠️ Произошла ошибка: {e.detail}"


async def _send_long_message(message: Message, text: str) -> None:
    """Отправляет текст, разбивая на части если он длиннее 4096 символов."""
    for i in range(0, len(text), MAX_MESSAGE_LENGTH):
        await message.answer(text[i : i + MAX_MESSAGE_LENGTH], parse_mode='HTML')


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message, bot: Bot) -> None:
    """Обрабатывает текстовые сообщения пользователя."""
    telegram_id = message.from_user.id
    credentials = await storage.get_credentials(telegram_id)

    if credentials is None:
        await message.answer("Пожалуйста, напишите /start для начала работы.")
        return

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        data = await api_client.send_text(
            user_id=credentials["user_id"],
            api_key=credentials["api_key"],
            message=message.text,
        )
    except api_client.APIError as e:
        logger.error("APIError при обработке текста: %s", e)
        await message.answer(_error_text(e))
        return

    response_text = _format_response(data)
    await _send_long_message(message, response_text)


@router.message(F.photo)
async def handle_photo(message: Message, bot: Bot) -> None:
    """Обрабатывает изображения с опциональной текстовой подписью."""
    telegram_id = message.from_user.id
    credentials = await storage.get_credentials(telegram_id)

    if credentials is None:
        await message.answer("Пожалуйста, напишите /start для начала работы.")
        return

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    # Берём фото с наибольшим разрешением
    photo = message.photo[-1]
    caption = message.caption or DEFAULT_PHOTO_CAPTION

    # Скачиваем изображение
    buf = BytesIO()
    await bot.download(photo.file_id, destination=buf)
    image_bytes = buf.getvalue()

    try:
        data = await api_client.send_text(
            user_id=credentials["user_id"],
            api_key=credentials["api_key"],
            message=caption,
            image_bytes=image_bytes,
            image_mime="image/jpeg",
        )
    except api_client.APIError as e:
        logger.error("APIError при обработке фото: %s", e)
        await message.answer(_error_text(e))
        return

    response_text = _format_response(data)
    await _send_long_message(message, response_text)
