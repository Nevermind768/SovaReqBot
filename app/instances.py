import asyncio
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
import os

# Global event loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

bot = Bot(
    token=os.getenv("TOKEN_BOT"),
    default=DefaultBotProperties(parse_mode="markdown"),
)
