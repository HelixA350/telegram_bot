"""
Точка входа Telegram-бота AI-консультанта.
Инициализирует базу данных, подключает все роутеры и запускает polling.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher

import config
import storage
from handlers import start, text, voice, reset


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Основная асинхронная функция: настройка и запуск бота."""
    await storage.init_db()

    bot = Bot(token=config.BOT_TOKEN)

    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(reset.router)
    dp.include_router(voice.router)
    dp.include_router(text.router)

    logger.info("Бот запущен. Начинаю polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Бот остановлен.")


if __name__ == "__main__":
    asyncio.run(main())
