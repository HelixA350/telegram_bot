"""
Хэндлер голосовых сообщений.
Скачивает голосовое сообщение (.ogg/OPUS), конвертирует его в mp3 через pydub+ffmpeg
и отправляет в API для расшифровки и получения ответа AI-консультанта.
"""

import logging
from io import BytesIO

from aiogram import Bot, Router, F
from aiogram.enums import ChatAction
from aiogram.types import Message
from pydub import AudioSegment

import api_client
import storage

logger = logging.getLogger(__name__)

router = Router()

MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024  # 25 МБ
MAX_MESSAGE_LENGTH = 4096


def _ogg_to_mp3(ogg_bytes: bytes) -> bytes:
    """Конвертирует аудио из формата OGG (OPUS) в MP3."""
    audio = AudioSegment.from_ogg(BytesIO(ogg_bytes))
    mp3_buf = BytesIO()
    audio.export(mp3_buf, format="mp3")
    return mp3_buf.getvalue()


def _format_voice_response(data: dict) -> str:
    """Форматирует ответ API для голосового сообщения."""
    transcription = data.get("transcription", "").strip()
    content = data.get("content", "").strip()

    if not content:
        content = "Не удалось получить ответ. Попробуйте переформулировать вопрос."

    lines = []
    if transcription:
        lines.append(f'🎤 Распознано: "{transcription}"\n')
    lines.append(content)

    source_chunks = data.get("source_chunks", [])
    if source_chunks:
        lines.append("\n📎 Источники:")
        for chunk in source_chunks:
            name = chunk.get("source", chunk.get("filename", "неизвестный файл"))
            score = chunk.get("score", chunk.get("relevance"))
            if score is not None:
                try:
                    percent = round(float(score) * 100) if float(score) <= 1 else round(float(score))
                    lines.append(f"• {name} (релевантность: {percent}%)")
                except (ValueError, TypeError):
                    lines.append(f"• {name}")
            else:
                lines.append(f"• {name}")

    return "\n".join(lines)


def _error_text(e: api_client.APIError) -> str:
    """Возвращает понятное русскоязычное сообщение об ошибке API."""
    if e.status_code == 401:
        return "⚠️ Ошибка авторизации. Попробуйте /start для перерегистрации."
    if e.status_code == 503:
        return "⚠️ Сервис временно недоступен. Попробуйте чуть позже."
    return f"⚠️ Произошла ошибка: {e.detail}"


@router.message(F.voice)
async def handle_voice(message: Message, bot: Bot) -> None:
    """Обрабатывает голосовые сообщения: конвертирует ogg→mp3 и отправляет в API."""
    telegram_id = message.from_user.id
    credentials = await storage.get_credentials(telegram_id)

    if credentials is None:
        await message.answer("Пожалуйста, напишите /start для начала работы.")
        return

    file_size = message.voice.file_size or 0
    if file_size > MAX_AUDIO_SIZE_BYTES:
        await message.answer("⚠️ Голосовое сообщение слишком большое (макс. 25 МБ).")
        return

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.RECORD_VOICE)

    buf = BytesIO()
    await bot.download(message.voice.file_id, destination=buf)

    try:
        mp3_bytes = _ogg_to_mp3(buf.getvalue())
    except Exception as e:
        logger.error("Ошибка конвертации аудио: %s", e)
        await message.answer("⚠️ Не удалось обработать голосовое сообщение. Попробуйте ещё раз.")
        return

    await bot.send_chat_action(chat_id=message.chat.id, action=ChatAction.TYPING)

    try:
        data = await api_client.send_audio(
            user_id=credentials["user_id"],
            api_key=credentials["api_key"],
            audio_bytes=mp3_bytes,
        )
    except api_client.APIError as e:
        logger.error("APIError при обработке голосового: %s", e)
        await message.answer(_error_text(e))
        return

    response_text = _format_voice_response(data)
    for i in range(0, len(response_text), MAX_MESSAGE_LENGTH):
        await message.answer(response_text[i : i + MAX_MESSAGE_LENGTH])
