from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BotCommandScopeChat
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from app.filters import RoleFilter
from app.roles import Role
from app.keyboards import get_moderators, get_manage_panel, manage_moderator
from app.states import PickModerator
from app.database.requests import update_role
from app.utils.errors import SameDataError, DBKeyError
from app.utils.parser import get_commands
import app.config.labels as label
from app.database.requests import get_users, get_user
from app.database.models import User
from app.roles.moderator import return_main
from app.logger import setup_logger

admin = Router()

# Установка фильтра для входящих сообщений
admin.message.filter(RoleFilter(Role.ADMIN))

for_moder = Role.MODERATOR.name

logger = setup_logger(__name__)


@admin.message(Command("moderators"))
async def moderators(message: Message, state: FSMContext):
    """Вызов панели админа для управления модераторами.

    Args:
        message (Message): _description_
        state (FSMContext): _description_
    """

    await state.clear()
    await message.answer(
        label.CHOOSE_ACTION, reply_markup=await get_manage_panel(for_moder)
    )


@admin.message(PickModerator.id)
async def apply_new_moderator(message: Message, state: FSMContext):
    """Получение id нового модератора.

    Args:
        message (Message): _description_
        state (FSMContext): _description_
    """
    await state.clear()
    logger.info("Получение id нового модератора")
    try:
        user_id = int(message.text)
        await update_role(user_id, Role.MODERATOR)

        user = await message.bot.get_chat(user_id)
        await message.answer(label.MODER_APPOINTED.format(user.username))
        await message.bot.send_message(user_id, label.YOU_MODER)
        logger.info(f"Установка команд модератора user (id={user_id})")
        await message.bot.set_my_commands(
            await get_commands(Role.MODERATOR),
            scope=BotCommandScopeChat(chat_id=user_id),
        )

    except SameDataError:
        logger.info("User уже является модератором")
        await message.answer(label.ALREADY_MODER)
    except Exception as ex:
        logger.error(f"Некорректный user_id - {ex}")
        await message.answer(label.BAD_ID)
    finally:
        await message.bot.delete_messages(
            message.chat.id, [message.message_id - 1, message.message_id]
        )


@admin.callback_query(F.data.startswith(f"page_{for_moder}_"))
async def show_moderator_page(callback: CallbackQuery):
    """Показ страницы с модераторами.

    Args:
        callback (CallbackQuery): _description_
    """
    logger.info("Показ страницы с модераторами")
    moders = await get_users([User.role == Role.MODERATOR.value])
    if len(moders) > 0:
        await callback.answer()
        await callback.message.edit_text(
            label.CHOOSE_ACTION,
            reply_markup=await get_moderators(
                moders, int(callback.data.split("_")[-1]), callback.bot
            ),
        )
    else:
        await callback.answer(label.EMPTY_MODERS)


@admin.callback_query(F.data.startswith(f"{for_moder}_"))
async def moderator_info(callback: CallbackQuery):
    """Показ профиля модератора.

    Args:
        callback (CallbackQuery): _description_
    """
    await callback.answer()
    user_id = int(callback.data.split("_")[1])
    logger.info(f"Показ профиля модератора (id={user_id})")
    page = int(callback.data.split("_")[2])

    user = await get_user(user_id)
    user_info = await callback.bot.get_chat(user_id)
    await callback.message.edit_text(
        label.MODER_INFO.format(tag=f"@{user_info.username}", last_bd=user.lastDbReq),
        reply_markup=await manage_moderator(user_id, page),
    )


@admin.callback_query(F.data.startswith("demote_"))
async def demote_moderator(callback: CallbackQuery, state: FSMContext):
    """Разжалование модератора.

    Args:
        callback (CallbackQuery): _description_
        state (FSMContext): _description_
    """
    await callback.answer()
    user_id = int(callback.data.split("_")[1])
    logger.info(f"Разжалование модератора (id={user_id})")
    try:
        await update_role(user_id, Role.USER)

        user = await callback.bot.get_chat(user_id)
        await callback.message.answer(label.MODER_DEMOTE.format(user.username))
        await callback.bot.send_message(user_id, label.YOU_USER)
        await callback.bot.set_my_commands(
            await get_commands(Role.USER),
            scope=BotCommandScopeChat(chat_id=user_id),
        )
    except DBKeyError:
        logger.info("Отсутствует user_id в БД")
        await callback.message.answer(label.BAD_ID)
    except Exception as ex:
        logger.error(f"Неожиданная ошибка - {ex}")
        await callback.message.answer(label.UNEXPECTED_ERROR)
    await return_main(callback, state)


@admin.callback_query(F.data == "_")
async def page_index(callback: CallbackQuery):
    """Функция-затычка.

    Args:
        callback (CallbackQuery): _description_
    """
    await callback.answer()
