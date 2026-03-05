"""
Хэндлер команды /reset.
Сбрасывает контекст диалога пользователя через API,
позволяя начать разговор с чистого листа.
"""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

import api_client
import storage

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("reset"))
async def handle_reset(message: Message) -> None:
    """Обрабатывает команду /reset: сбрасывает память диалога в API."""
    telegram_id = message.from_user.id
    credentials = await storage.get_credentials(telegram_id)

    if credentials is None:
        await message.answer("Пожалуйста, напишите /start для начала работы.")
        return

    try:
        await api_client.reset_memory(
            user_id=credentials["user_id"],
            api_key=credentials["api_key"],
        )
        await message.answer("🔄 Диалог сброшен. Можете начать новый разговор с чистого листа.")
        logger.info("Память сброшена для telegram_id=%s", telegram_id)
    except api_client.APIError as e:
        logger.error("APIError при сбросе памяти: %s", e)
        if e.status_code == 401:
            await message.answer("⚠️ Ошибка авторизации. Попробуйте /start для перерегистрации.")
        elif e.status_code == 503:
            await message.answer("⚠️ Сервис временно недоступен. Попробуйте чуть позже.")
        else:
            await message.answer(f"⚠️ Не удалось сбросить диалог: {e.detail}")
