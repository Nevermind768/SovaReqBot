from math import ceil

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import app.config.labels as label
from app.config import KEYBOARD_PAGE_SIZE
from app.database.models import User
from app.database.requests import get_applications
from app.logger import setup_logger
from app.roles import Role

logger = setup_logger(__name__)


# Клавиатура для отправления обращения
applicationKb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=label.SEND_APPEAL, callback_data="application")]
    ]
)

# Клавиатура для возвращения на один шаг назад при заполнении обращения
applicationBackKb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text=label.RETURN, callback_data="app_stepback")]
    ]
)

# Клавиатура для изменения профиля
profileKb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text=label.CHANGE_PROFILE, callback_data="change_profile"
            )
        ]
    ]
)

# Клавиатура о том, что не обращался в полицию
policeKb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text=label.DONT_CONTACT_POLICE, callback_data="dont_contact_police"
            ),
        ]
    ]
    + applicationBackKb.inline_keyboard
)


async def get_categories():
    """Клавиатура категорий обращения.

    Returns:
        InlineKeyboardMarkup: Inline кнопки.
    """
    keyboard = InlineKeyboardBuilder()
    for i in range(len(label.CATEGORIES)):
        keyboard.row(
            InlineKeyboardButton(
                text=label.CATEGORIES[i], callback_data=f"category_{i}"
            )
        )
    return keyboard.as_markup()


async def get_ban_reasons():
    """Клавиатура причин бана.

    Returns:
        InlineKeyboardMarkup: Inline кнопки.
    """
    keyboard = InlineKeyboardBuilder()
    for i in range(len(label.BAN_REASONS)):
        keyboard.row(
            InlineKeyboardButton(text=label.BAN_REASONS[i], callback_data=f"reason_{i}")
        )
    keyboard.row(
        InlineKeyboardButton(text=label.RETURN, callback_data="return_panel_user")
    )
    return keyboard.as_markup()


async def get_manage_panel(user_type):
    """Клавиатура управления пользователями.

    Returns:
        InlineKeyboardMarkup: Inline кнопки.
    """
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(
            text=label.ADD if user_type == Role.MODERATOR.name else label.BAN,
            callback_data=f"add_{user_type}",
        )
    )
    if user_type == Role.MODERATOR.name:
        keyboard.row(
            InlineKeyboardButton(text=label.LIST, callback_data="page_moderator_1")
        )
    else:
        keyboard.row(
            InlineKeyboardButton(text=label.BAN_LIST, callback_data="user_list")
        )
        keyboard.row(InlineKeyboardButton(text=label.UNBAN, callback_data="unban"))
    keyboard.row(InlineKeyboardButton(text=label.CLOSE, callback_data="close"))
    return keyboard.as_markup()


async def get_moderators(moders: list[User], cur_page, bot: Bot):
    """Клавиатура с модераторами.

    Returns:
        InlineKeyboardMarkup: Inline кнопки.
    """
    pages_num = ceil(len(moders) / KEYBOARD_PAGE_SIZE)
    from_i = KEYBOARD_PAGE_SIZE * (cur_page - 1)
    to_i = min(len(moders), KEYBOARD_PAGE_SIZE * cur_page)
    keyboard = InlineKeyboardBuilder()

    for i in range(from_i, to_i):
        user = await bot.get_chat(moders[i].id)
        keyboard.row(
            InlineKeyboardButton(
                text=f"@{user.username}",
                callback_data=f"moderator_{user.id}_{cur_page}",
            )
        )

    keyboard.row(
        InlineKeyboardButton(
            text=label.BACK,
            callback_data=f"page_moderator_{cur_page - 1}" if cur_page - 1 > 0 else "_",
        ),
        InlineKeyboardButton(text=f"{cur_page}/{pages_num}", callback_data="_"),
        InlineKeyboardButton(
            text=label.FORWARD,
            callback_data=(
                f"page_moderator_{cur_page + 1}" if cur_page < pages_num else "_"
            ),
        ),
    )

    keyboard.row(
        InlineKeyboardButton(
            text=label.RETURN, callback_data=f"return_panel_{Role.MODERATOR.name}"
        ),
        InlineKeyboardButton(text=label.CLOSE, callback_data="close"),
    )
    return keyboard.as_markup()


async def manage_moderator(user_id, back_page):
    """Клавиатура для управления модераторами.

    Returns:
        InlineKeyboardMarkup: Inline кнопки.
    """
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(text=label.DEMOTE, callback_data=f"demote_{user_id}")
    )
    keyboard.row(
        InlineKeyboardButton(
            text=label.RETURN, callback_data=f"page_moderator_{back_page}"
        ),
        InlineKeyboardButton(text=label.CLOSE, callback_data="close"),
    )
    return keyboard.as_markup()


async def get_ban_terms():
    """Клавиатура со сроками бана.

    Returns:
        InlineKeyboardMarkup: Inline кнопки.
    """
    keyboard = InlineKeyboardBuilder()
    for key, value in label.BAN_TERMS.items():
        keyboard.row(InlineKeyboardButton(text=key, callback_data=f"ban_{value}"))
    keyboard.row(
        InlineKeyboardButton(text=label.RETURN, callback_data="return_panel_user")
    )
    return keyboard.as_markup()


async def get_download_appeals():
    """Клавиатура с выбором загрузки бд.

    Returns:
        InlineKeyboardMarkup: Inline кнопки.
    """
    new_count = len(await get_applications(True))
    all_count = len(await get_applications(False))
    keyboard = InlineKeyboardBuilder()
    keyboard.row(
        InlineKeyboardButton(
            text=label.DOWNLOAD_NEW.format(new_count),
            callback_data="download_new",
        )
    )
    keyboard.row(
        InlineKeyboardButton(
            text=label.DOWNLOAD_ALL.format(all_count),
            callback_data="download_all",
        )
    )
    keyboard.row(InlineKeyboardButton(text=label.CLOSE, callback_data="close"))
    return keyboard.as_markup()
