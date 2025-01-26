import hashlib
from datetime import datetime, timedelta, timezone
from os import getenv

import pandas as pd
from sqlalchemy import and_, func, select, update

from app.database import AppLen, UserInfoLen
from app.database.models import Application, Attachment, User, UserInfo, async_session
from app.logger import setup_logger
from app.roles import Role
from app.utils.errors import DBKeyError, SameDataError

logger = setup_logger(__name__)


async def get_user(user_id):
    """Получение объекта user по id.

    Args:
        user_id (int): Id пользователя.

    Returns:
        User: Объект таблицы User.
    """
    # logger.info(f"Получение user (id={user_id})")
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.id == user_id))
        return user


async def get_users(conditions):
    """Получение списка user по условиям.

    Args:
        conditions (list): Условия.

    Returns:
        Sequence[User]: Список user.
    """
    logger.info("Получение users")
    async with async_session() as session:
        stmt = select(User).where(and_(*conditions))
        users = await session.scalars(stmt)
        return users.all()


async def set_user(user_id):
    """Установка user в случае его отсутствия.

    Args:
        user_id (int): Идентификатор пользователя.
    """
    logger.info(f"Установка user (id={user_id})")
    async with async_session() as session:
        user = await get_user(user_id)

        if not user:
            logger.info(f"User (id={user_id}) не существует. Добавляем...")
            session.add(User(id=user_id))
            await session.commit()
        else:
            logger.info(f"User (id={user_id}) уже существует")


async def ban_user(user_id, data: dict):
    """Блокировка пользователя.

    Args:
        user_id (int): Идентификатор пользователя.
        data (dict): Данные бана.

    Raises:
        DBKeyError: Ошибка отсутствия ключа в БД.

    Returns:
        datetime: Окончание бана.
    """
    logger.info(
        f"Бан user (id={user_id}) на {data.get("term")} дней по причине {data.get("reason")}"
    )
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.id == user_id))
        if not user:
            raise DBKeyError()
        user.banBy = data.get("ban_by")
        ban_start = datetime.now(timezone.utc)
        ban_end = ban_start + timedelta(days=data.get("term"))
        user.banStart = ban_start
        user.banEnd = ban_end
        user.banReason = data.get("reason")
        await session.commit()
        return ban_end.date()


async def update_role(user_id, new_role: Role):
    """Обновление роли пользователя.

    Args:
        user_id (int): Идентификатор пользователя.
        new_role (Role): Новая роль.

    Raises:
        DBKeyError: Ошибка отсутствия ключа в БД.
        SameDataError: Ошибка повторяющихся данных в БД.
    """
    logger.info(f"Установка роли {new_role.name} user (id={user_id})")
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.id == user_id))
        if not user:
            raise DBKeyError()
        if user.role == new_role.value or user.role == Role.ADMIN.value:
            raise SameDataError()
        user.role = new_role.value
        await session.commit()


async def get_profile(user_id):
    """Получение личных данных пользователя.

    Args:
        user_id (int): Идентификатор пользователя.

    Returns:
        UserInfo: Объект таблицы UserInfo.
    """
    logger.info(f"Получение профиля user (id={user_id})")
    async with async_session() as session:
        profile = await session.scalar(select(UserInfo).where(UserInfo.userId == user_id))
        return profile


async def set_profile(user_id, new_profile: dict):
    """Установка личных данных пользователя.

    Args:
        user_id (int): Идентификатор пользователя.
        new_profile (dict): Имя, контакт.
    """
    fullName = new_profile.get("full_name")[: UserInfoLen.FULLNAME]
    contact = new_profile.get("contact")[: UserInfoLen.CONTACT]
    async with async_session() as session:
        profile = await session.scalar(select(UserInfo).where(UserInfo.userId == user_id))
        if profile:
            logger.info(f"Обновление профиля user (id={user_id})")
            profile.fullName = fullName
            profile.contact = contact
        else:
            logger.info(f"Установка профиля user (id={user_id})")
            session.add(
                UserInfo(
                    userId=user_id,
                    fullName=fullName,
                    contact=contact,
                )
            )
        await session.commit()


async def add_application(user_id, msg_id, data: dict):
    """Добавление обращения.

    Args:
        user_id (int): Идентификатор пользователя.
        msg_id (int): Идентификатор сообщения.
        data (dict): Данные обращения.
    """
    logger.info(f"Добавление обращения user (id={user_id})")
    address = data.get("address")[: AppLen.ADDRESS]
    body = data.get("body", "")[: AppLen.BODY]
    police = data.get("police")[: AppLen.POLICE]
    attachments = data.get("attachments", "")[: AppLen.ATTACHMENTS]
    async with async_session() as session:
        session.add(
            Application(
                msgId=msg_id,
                userId=user_id,
                category=data.get("category"),
                address=address,
                body=body,
                police=police,
                attachments=attachments,
            )
        )
        await session.commit()


async def get_role(user_id, quiet=True) -> Role:
    """Получение роли пользователя.

    Args:
        user_id (int): Идентификатор пользователя.
        quiet (bool, optional): Вызов ошибки в случае отсутствия пользователя.. Defaults to True.

    Raises:
        DBKeyError: Ошибка отсутствия ключа в БД.

    Returns:
        Role: Роль пользователя.
    """
    # logger.info(f"Получение роли user (id={user_id}), quiet={quiet}")
    user = await get_user(user_id)
    if not user:
        if quiet:
            return Role.USER
        else:
            raise DBKeyError()
    if getenv("ADMIN") == str(user_id):
        return Role.ADMIN
    return Role.from_value(user.role)


async def get_lastDbReq():
    """Получение даты последнего скачивания БД.

    Returns:
        datetime: Дата последнего скачивания БД.
    """
    logger.info("Получение lastDbReq")
    async with async_session() as session:
        after_date = await session.scalar(select(func.max(User.lastDbReq)))
        if not after_date:
            logger.info("lastDbReq=NULL. Устанавливаем минимальную")
            after_date = datetime.min
        return after_date


async def get_applications(only_new):
    """Получение обращений.

    Args:
        only_new (bool): Только новые.

    Returns:
        Sequence[Application]: Список обращений.
    """
    logger.info(f"Получение обращений (only_new={only_new})")
    async with async_session() as session:
        after_date = datetime.min
        if only_new:
            after_date = await get_lastDbReq()
        stmt = select(Application).where(Application.dt > after_date)
        appeals = await session.scalars(stmt)
        return appeals.all()


async def save_appeals(user_id, only_new):
    """Генерация excel таблицы БД Application.

    Args:
        user_id (int): Идентификатор пользователя.
        only_new (bool): Только новые.

    Returns:
        str: Excel file path.
    """
    logger.info(f"Получение обращений user'ом (id={user_id}) для сохранения (only_new={only_new})")
    async with async_session() as session:
        dt = datetime.now(timezone.utc)
        after_date = datetime.min
        if only_new:
            after_date = await get_lastDbReq()
        query = (
            select(UserInfo, Application)
            .join(UserInfo, Application.userId == UserInfo.userId)
            .where(Application.dt > after_date)
            .order_by(Application.dt.asc())
        )
        appeals = await session.execute(query)
        data = []
        for user_info, application in appeals:
            user_info: UserInfo
            application: Application
            data.append(
                {
                    "Id": user_info.userId,
                    "Полное имя": user_info.fullName,
                    "Контакт": user_info.contact,
                    "Дата обращения": application.dt.replace(tzinfo=None),
                    "Категория": application.category,
                    "Обращение": application.body,
                    "Полиция": application.police,
                    "Приложения": application.attachments,
                }
            )
        if not data:
            return None
        df = pd.DataFrame(data)
        file_name = f"Appeals {dt.strftime('%y.%m.%d_%H-%M-%S')}.xlsx"
        logger.info("Генерация excel")
        df.to_excel(file_name, index=False)
        await session.execute(update(User).where(User.id == user_id).values(lastDbReq=dt))
        await session.commit()
        return file_name


async def save_ban_users(user_id):
    """Генерация excel таблицы БД User.

    Args:
        user_id (int): Идентификатор пользователя.

    Returns:
        str: Excel file path.
    """
    logger.info(f"Получение таблицы excel User user'ом (id={user_id})")
    async with async_session() as session:
        dt = datetime.now(timezone.utc)
        users = await session.scalars(select(User).where(User.banEnd > dt))
        data = []
        for user in users.all():
            data.append(
                {
                    "Id": user.id,
                    "Начало бана": user.banStart.replace(tzinfo=None),
                    "Конец бана": user.banEnd.replace(tzinfo=None),
                    "Причина бана": user.banReason,
                    "Кем забанен": user.banBy,
                }
            )
        if not len(data):
            return ""
        df = pd.DataFrame(data)
        file_name = f"Banned {dt.strftime('%y.%m.%d_%H-%M-%S')}.xlsx"
        logger.info("Генерация excel")
        df.to_excel(file_name, index=False)
        return file_name


async def is_banned(user_id):
    """Проверка на наличие бана у пользователя.

    Args:
        user_id (int): Идентификатор пользователя.

    Returns:
        bool: isBan
    """
    logger.info(f"Проверка бана у user (id={user_id})")
    user = await get_user(user_id)
    return user.regAt and (datetime.now(timezone.utc) < user.regAt)


async def set_hash_link(link: str):
    """Запись соответствия хеш-ссылка на приложения тг.

    Args:
        link (str): Ссылка на приложение тг.

    Returns:
        str: Хеш.
    """
    logger.info(f"Генерация хеша для приложения (link={link})")
    async with async_session() as session:
        hash_str = str(hashlib.md5(link.encode()).hexdigest())
        session.add(Attachment(hash=hash_str, link=link))
        await session.commit()

        return hash_str


async def get_hash_link(hash: str):
    """Получение ссылки на приложение тг по хешу.

    Args:
        link (str): Хеш ссылки.

    Returns:
        str: Ссылка.
    """
    async with async_session() as session:
        link = await session.scalar(select(Attachment.link).where(Attachment.hash == hash))
        return link
