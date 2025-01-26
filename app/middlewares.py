import asyncio
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from typing import Callable, Dict, Any
from app.logger import setup_logger

logger = setup_logger(__name__)


class AlbumMiddleware(BaseMiddleware):
    """Middleware для обработки альбомов.

    Args:
        BaseMiddleware (_type_): _description_
    """

    def __init__(self, latency: float = 0.5):
        """Инициализация middleware для обработки альбомов.

        Args:
            latency (float, optional): Задержка между сообщениями в группе. Defaults to 0.5.
        """
        logger.info("Инициализация middleware для обработки альбомов")
        self.latency = latency
        self.album_data: Dict[str, list] = {}
        super().__init__()

    async def __call__(self, handler: Callable, event: Message, data: Dict[str, Any]):
        if not event.media_group_id:
            return await handler(event, data)
        logger.info("Обнаружено медиа в сообщении")
        try:
            self.album_data[event.media_group_id].append(event)

        except KeyError:
            logger.info("Добавление первого медиа")
            self.album_data[event.media_group_id] = [event]
            await asyncio.sleep(self.latency)

            data["is_last"] = True
            data["album"] = self.album_data[event.media_group_id]

            return await handler(event, data)

    async def after(self, handler, event: Message, data: Dict[str, Any]):
        if event.media_group_id and data.get("is_last"):
            logger.info("Освобождение данных")
            del self.album_data[event.media_group_id]


class LoggingMiddleware(BaseMiddleware):
    """Middleware для логгирования.

    Args:
        BaseMiddleware (_type_): _description_
    """
    async def __call__(self, handler: Callable, event: TelegramObject, data: Dict[str, Any]):
        """Логгирование Message и CallbackQuery.

        Args:
            handler (Callable): _description_
            event (TelegramObject): _description_
            data (Dict[str, Any]): _description_

        Returns:
            _type_: _description_
        """
        user_id = event.from_user.id
        if isinstance(event, Message):
            logger.info(f"Message (user_id={user_id}): {event.text}")
        elif isinstance(event, CallbackQuery):
            logger.info(f"CallbackQuery (user_id={user_id}): {event.data}")
        return await handler(event, data)
