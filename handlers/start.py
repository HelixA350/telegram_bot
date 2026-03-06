"""
Хэндлер команды /start.
Регистрирует нового пользователя в API при первом запуске
и отправляет онбординг-сообщение.
"""

import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

import api_client
import storage

logger = logging.getLogger(__name__)

router = Router()

ONBOARDING_TEXT = """👋 Привет! Я AI-консультант.

Я умею отвечать на вопросы по работе в вымышленной компании.

Вот что я умею:
• 💬 Отвечать на текстовые вопросы
• 🎤 Понимать голосовые сообщения (mp3)
• 🖼 Анализировать изображения, приложенные к вопросу

Просто напишите или продиктуйте свой вопрос — и я отвечу.

Например:

💬 Какие KPI и премии у разработчиков
💬 Кто гендиректор компании

Команды:
/reset — начать диалог заново (сбросить контекст)"""


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    """Обрабатывает команду /start: регистрирует пользователя и показывает онбординг."""
    telegram_id = message.from_user.id

    credentials = await storage.get_credentials(telegram_id)
    if credentials is None:
        try:
            user_id, api_key = await api_client.register()
            await storage.save_credentials(telegram_id, user_id, api_key)
            logger.info("Новый пользователь зарегистрирован: telegram_id=%s", telegram_id)
        except api_client.APIError as e:
            logger.error("Ошибка регистрации для telegram_id=%s: %s", telegram_id, e)
            await message.answer("⚠️ Не удалось выполнить регистрацию. Попробуйте позже.")
            return
    else:
        logger.info("Пользователь уже зарегистрирован: telegram_id=%s", telegram_id)

    await message.answer(ONBOARDING_TEXT)
