"""
Модуль хранилища учётных данных пользователей.
Использует SQLite через aiosqlite для асинхронного хранения
пар (user_id, api_key) для каждого Telegram-пользователя.
База данных создаётся автоматически при первом запуске.
"""

import logging
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = "/data/bot.db"


async def init_db() -> None:
    """Создаёт таблицу пользователей, если она ещё не существует."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                user_id     TEXT NOT NULL,
                api_key     TEXT NOT NULL
            )
        """)
        await db.commit()
    logger.info("База данных инициализирована: %s", DB_PATH)


async def get_credentials(telegram_id: int) -> Optional[dict]:
    """
    Возвращает учётные данные пользователя по Telegram ID.

    Returns:
        Словарь {'user_id': ..., 'api_key': ...} или None, если пользователь не найден.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id, api_key FROM users WHERE telegram_id = ?",
            (telegram_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return {"user_id": row[0], "api_key": row[1]}


async def save_credentials(telegram_id: int, user_id: str, api_key: str) -> None:
    """
    Сохраняет учётные данные пользователя.
    Если пользователь уже существует — обновляет данные.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO users (telegram_id, user_id, api_key)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                user_id = excluded.user_id,
                api_key = excluded.api_key
            """,
            (telegram_id, user_id, api_key),
        )
        await db.commit()
    logger.info("Сохранены учётные данные для telegram_id=%s", telegram_id)
