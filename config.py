"""
Модуль конфигурации бота.
Загружает переменные окружения из .env файла и предоставляет их остальным модулям.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    """Возвращает значение переменной окружения или выбрасывает ошибку ValueError."""
    value = os.getenv(name)
    if not value:
        raise ValueError(
            f"Переменная окружения '{name}' не задана. "
            f"Проверьте файл .env или переменные среды."
        )
    return value


BOT_TOKEN: str = _require("BOT_TOKEN")
API_BASE_URL: str = _require("API_BASE_URL")
