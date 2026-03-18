Вижу структуру репозитория. Подтяну ключевые файлы для полноты.Достаточно данных. Вот README:

---

# AI Consultant — Telegram Bot

Telegram-бот на Aiogram 3, который предоставляет пользователям доступ к [RAG-сервису AI-консультанта](https://github.com/HelixA350/ai_consultant). Поддерживает текстовые и голосовые сообщения, опциональную отправку изображений.

**Стек:** Aiogram 3 · aiosqlite · Python 3.11 · Docker

---

## Что реализовано

### Хранилище учётных данных (SQLite)

При первом обращении бот автоматически регистрирует пользователя через API и сохраняет пару `(telegram_id → user_id, api_key)` в локальную SQLite-базу через `aiosqlite`. При последующих запросах учётные данные читаются локально — без лишних сетевых обращений. Upsert через `ON CONFLICT` — дублей не возникает.

### Роутеры и команды

| Роутер | Описание |
|---|---|
| `start` | `/start` — регистрация или приветствие зарегистрированного пользователя |
| `text` | Текстовые сообщения (+ опциональное изображение) → `POST /api/v1/chat/text` |
| `voice` | Голосовые сообщения (+ опциональное изображение) → `POST /api/v1/chat/audio` |
| `reset` | `/reset` — очистка диалоговой памяти → `DELETE /api/v1/chat/memory` |

### API-клиент

`api_client.py` инкапсулирует всё общение с бэкендом: передаёт `X-API-Key` и `X-User-ID` в заголовках, сериализует файлы как `multipart/form-data`. Бот не знает ничего об устройстве RAG-пайплайна — только вызывает клиент и отдаёт ответ пользователю.

---

## Структура

```
telegram_bot/
├── handlers/
│   ├── start.py     # /start, регистрация
│   ├── text.py      # текстовые сообщения
│   ├── voice.py     # голосовые сообщения
│   └── reset.py     # /reset, сброс памяти
├── main.py          # точка входа, polling
├── api_client.py    # HTTP-клиент к RAG API
├── storage.py       # aiosqlite: хранение user_id и api_key
├── config.py        # переменные окружения
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Быстрый старт

**1. Переменные окружения**

```bash
cp .env.example .env
```

```env
BOT_TOKEN=<токен от @BotFather>
API_BASE_URL=http://localhost:8000   # адрес RAG-сервиса
```

**2. Запуск**

```bash
docker compose up --build
```

SQLite-база создаётся автоматически при первом запуске в `/data/bot.db`.

> Для работы бота необходим запущенный [AI Consultant API](https://github.com/HelixA350/ai_consultant).

---

## Связанный репозиторий

[HelixA350/Demo](https://github.com/HelixA350/Demo) — FastAPI RAG-бэкенд, к которому обращается этот бот.