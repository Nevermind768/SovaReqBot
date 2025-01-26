import threading

from aiogram import Dispatcher

from app.database.models import async_init
from app.instances import bot, loop
from app.logger import setup_logger
from app.middlewares import AlbumMiddleware, LoggingMiddleware
from app.roles.admin import admin
from app.roles.moderator import moderator
from app.roles.user import user
from app.utils.file_forwarder import run_forwarder

logger = setup_logger(__name__)


async def main():
    """Настройка конфигурации бота и подключение роутеров."""
    user.message.middleware(AlbumMiddleware())

    dp = Dispatcher()
    dp.include_routers(user, moderator, admin)
    dp.callback_query.middleware(LoggingMiddleware())
    dp.message.middleware(LoggingMiddleware())

    # Инициализация БД
    await async_init()

    logger.info("Старт бота")
    await dp.start_polling(bot)


if __name__ == "__main__":
    """Точка входа в программу."""

    # Запуск сервера для переадресации запросов на получение приложение из тг
    logger.info("Запуск сервера в отдельном потоке")
    forwarder_thread = threading.Thread(target=run_forwarder)
    forwarder_thread.daemon = True
    forwarder_thread.start()

    try:
        logger.info("Асинхронный запуск бота")
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Работа бота прервана")
    except Exception as ex:
        logger.error(f"Неожиданная ошибка - {ex}")
    finally:
        logger.info("Остановка event loop")
        loop.stop()
