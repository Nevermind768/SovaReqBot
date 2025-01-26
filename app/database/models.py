import os
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, SmallInteger, String
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.database import AppLen, AttachmentLen, UserInfoLen, UserLen

engine = create_async_engine(
    url=f"postgresql+asyncpg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}\
@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}",
    echo=False,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    """Таблица пользователя.

    Args:
        Base (AsyncAttrs, DeclarativeBase): Класс единого обращения.
    """

    __tablename__ = "user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role: Mapped[int] = mapped_column(SmallInteger, default=0)
    regAt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now()
    )
    banStart: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    banEnd: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    banBy: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.id"), nullable=True)
    banReason: Mapped[str] = mapped_column(String(UserLen.BAN_REASON), nullable=True)
    lastDbReq: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class UserInfo(Base):
    """Таблица личных данных пользователя.

    Args:
        Base (AsyncAttrs, DeclarativeBase): Класс единого обращения.
    """

    __tablename__ = "userInfo"

    userId: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.id"), primary_key=True)
    fullName: Mapped[str] = mapped_column(String(UserInfoLen.FULLNAME))
    contact: Mapped[str] = mapped_column(String(UserInfoLen.CONTACT))


class Application(Base):
    """Таблица обращений.

    Args:
        Base (AsyncAttrs, DeclarativeBase): Класс единого обращения.
    """

    __tablename__ = "application"

    msgId: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    userId: Mapped[int] = mapped_column(BigInteger, ForeignKey("user.id"), primary_key=True)
    status: Mapped[int] = mapped_column(SmallInteger, default=0)
    dt: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now())
    category: Mapped[str] = mapped_column(String(AppLen.CATEGORY))
    address: Mapped[str] = mapped_column(String(AppLen.ADDRESS))
    body: Mapped[str] = mapped_column(String(AppLen.BODY), nullable=True)
    police: Mapped[str] = mapped_column(String(AppLen.POLICE))
    attachments: Mapped[str] = mapped_column(String(AppLen.ATTACHMENTS), nullable=True)


class Attachment(Base):
    """Таблица соответствия между файлом тг и реальным.

    Args:
        Base (AsyncAttrs, DeclarativeBase): Класс единого обращения.
    """

    __tablename__ = "attachment"

    hash: Mapped[str] = mapped_column(String(AttachmentLen.HASH), primary_key=True)
    link: Mapped[str] = mapped_column(String(AttachmentLen.LINK), unique=True)


async def async_init():
    """Асинхронная инициализация БД, генерация таблиц."""
    from app.logger import setup_logger

    logger = setup_logger(__name__)

    async with engine.begin() as conn:
        logger.info("Инициализация БД")
        await conn.run_sync(Base.metadata.create_all)
