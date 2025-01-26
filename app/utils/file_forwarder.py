import asyncio
import os

import requests
import uvicorn
from fastapi import FastAPI, HTTPException, Response

from app.database.requests import get_hash_link
from app.instances import bot, loop
from app.logger import setup_logger
from app.utils.errors import FileForwarder

forwarder = FastAPI()

TELEGRAM_API = f"https://api.telegram.org/file/bot{os.getenv('TOKEN_BOT')}/"

logger = setup_logger(__name__)


def run_forwarder():
    """Запуск сервера для переадресации обращений к приложений из тг."""
    logger.info("Запуск FastAPI сервера в новом потоке")
    uvicorn.run(
        forwarder,
        host="0.0.0.0",
        port=int(os.getenv("SERVER_PORT")),
        ssl_keyfile="../data/key.pem",
        ssl_certfile="../data/cert.pem",
    )


@forwarder.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return None


@forwarder.get("/{hash}")
async def get_media(hash):
    logger.info(f"Получено новое обращение за файлом (hash={hash})")
    try:
        future = asyncio.run_coroutine_threadsafe(get_hash_link(hash), loop)
        file_id: str = future.result()
        if not file_id:
            raise FileForwarder("Неверный хеш")
        future = asyncio.run_coroutine_threadsafe(bot.get_file(file_id), loop)
        file_obj = future.result()
        if (not file_obj) or (not file_obj.file_path):
            raise FileForwarder("Не удалось получить путь к файлу")
        link = file_obj.file_path

        media_type, filename = link.split("/")
        file_url = f"{TELEGRAM_API}{media_type}/{filename}"

        response = requests.get(file_url, stream=True)

        if response.status_code != 200:
            raise FileForwarder("Не найден файл")

        headers = {
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        }

        return Response(content=response.content, headers=headers)
    except FileForwarder as ex:
        logger.info(ex)
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as ex:
        logger.error(ex)
        raise HTTPException(status_code=500, detail="Internal server error")
