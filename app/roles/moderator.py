import os

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

import app.config.labels as label
from app.database.requests import ban_user, get_role, save_appeals, save_ban_users
from app.filters import RoleFilter
from app.keyboards import (
    get_ban_reasons,
    get_ban_terms,
    get_download_appeals,
    get_manage_panel,
)
from app.logger import setup_logger
from app.roles import Role
from app.states import BanUser, PickModerator, UnbanUser

moderator = Router()

# Установка фильтра для входящих сообщений
moderator.message.filter(RoleFilter(Role.MODERATOR))

for_user = Role.USER.name

logger = setup_logger(__name__)


# Общие методы
@moderator.callback_query(F.data == "close")
async def close(callback: CallbackQuery):
    """Удаление двух последних сообщений.

    Args:
        callback (CallbackQuery): _description_
    """
    await callback.answer()
    await callback.bot.delete_messages(
        callback.message.chat.id,
        [callback.message.message_id, callback.message.message_id - 1],
    )


@moderator.callback_query(F.data.startswith("add_"))
async def add_any(callback: CallbackQuery, state: FSMContext):
    """Добавление модератора или бан пользователя.

    Args:
        callback (CallbackQuery): _description_
        state (FSMContext): _description_
    """
    await state.clear()
    await callback.answer()
    user_type = callback.data.split("_")[1]
    if user_type == for_user:
        await state.set_state(BanUser.term)
        await callback.message.edit_text(label.CHOOSE_BAN_TERM, reply_markup=await get_ban_terms())
    elif user_type == Role.MODERATOR.name:
        await state.set_state(PickModerator.id)
        await callback.message.answer(label.INPUT_MODER_ID)
        await callback.bot.delete_message(callback.message.chat.id, callback.message.message_id)


@moderator.callback_query(F.data.startswith("return_panel_"))
async def return_main(callback: CallbackQuery, state: FSMContext):
    """Возврат на меню управления.

    Args:
        callback (CallbackQuery): _description_
        state (FSMContext): _description_
    """
    await state.clear()
    await callback.answer()
    user_type = callback.data.split("_")[-1]
    if callback.data.startswith("demote_"):
        user_type = Role.MODERATOR.name
    await callback.message.edit_text(
        label.CHOOSE_ACTION, reply_markup=await get_manage_panel(user_type)
    )


@moderator.message(Command("users"))
async def users(message: Message, state: FSMContext):
    """Панель управления пользователями для модератора.

    Args:
        message (Message): _description_
        state (FSMContext): _description_
    """
    await state.clear()
    await message.answer(label.CHOOSE_ACTION, reply_markup=await get_manage_panel(for_user))


# Блокировка пользователя
@moderator.callback_query(F.data.startswith("ban_"), BanUser.term)
async def choose_ban_term(callback: CallbackQuery, state: FSMContext):
    """Получение срока бана пользователя.

    Args:
        callback (CallbackQuery): _description_
        state (FSMContext): _description_
    """
    await callback.answer()
    await state.update_data(term=int(callback.data.split("_")[1]))
    await state.set_state(BanUser.reason)
    await callback.message.edit_text(label.INPUT_BAN_REASON, reply_markup=await get_ban_reasons())


@moderator.callback_query(F.data.startswith("reason_"), BanUser.reason)
async def get_ban_reason(callback: CallbackQuery, state: FSMContext):
    """Получение причины бана.

    Args:
        callback (CallbackQuery): _description_
        state (FSMContext): _description_
    """
    await callback.answer()
    await state.update_data(reason=label.BAN_REASONS[int(callback.data.split("_")[1])])
    await state.set_state(BanUser.ids)
    await callback.message.answer(label.INPUT_USER_ID_BAN)
    await callback.bot.delete_message(callback.message.chat.id, callback.message.message_id)


@moderator.message(StateFilter(BanUser.ids, UnbanUser.ids))
async def get_ban_ids(message: Message, state: FSMContext):
    """Получение ids для бана.

    Args:
        message (Message): _description_
        state (FSMContext): _description_
    """
    role = await get_role(message.from_user.id)
    data = await state.get_data()
    last_state = await state.get_state()
    is_unbanning = last_state == UnbanUser.ids
    if is_unbanning:
        data["term"] = 0
    data["ban_by"] = message.from_user.id
    await state.clear()
    valid_ids = []
    ban_end = None
    for user_id in message.text.split():
        user_role = None
        try:
            user_id = int(user_id)
            user_role = await get_role(user_id, False)
            if (user_id == message.from_user.id) or (user_role.value >= role.value):
                continue

            ban_end = await ban_user(user_id, data)
            user = await message.bot.get_chat(user_id)
            valid_ids.append(f"@{user.username}")
        except Exception:
            pass

    if is_unbanning:
        await message.answer(label.SUCCESSFUL_UNBAN.format(", ".join(valid_ids)))
    else:
        await message.answer(
            label.SUCCESSFUL_BAN.format(
                ids=", ".join(valid_ids),
                term=data.get("term"),
                banEnd=ban_end,
                reason=data.get("reason"),
            )
        )
    await message.bot.delete_messages(
        message.chat.id, [message.message_id - 1, message.message_id]
    )


@moderator.callback_query(F.data == "user_list")
async def download_ban_users(callback: CallbackQuery):
    """Скачивание таблицы с пользователями.

    Args:
        callback (CallbackQuery): _description_
        state (FSMContext): _description_
    """

    file_name = await save_ban_users(callback.from_user.id)
    if not file_name:
        await callback.answer(label.EMPTY_BANS)
        return
    await callback.answer()
    file_path = os.path.join(os.getcwd(), file_name)
    try:
        await callback.message.answer_document(
            document=FSInputFile(file_path),
            caption=label.BAN_LIST,
        )
    except Exception as ex:
        logger.error(f"Невозможно загрузить список пользователей - {ex}")
        await callback.message.answer(label.DOWNLOAD_FAIL)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# Разбан
@moderator.callback_query(F.data == "unban")
async def unban_user(callback: CallbackQuery, state: FSMContext):
    """Разбан пользователей.

    Args:
        callback (CallbackQuery): _description_
        state (FSMContext): _description_
    """
    await callback.answer()
    await state.set_state(UnbanUser.ids)
    await callback.message.answer(label.INPUT_USER_ID_UNBAN)

    await callback.bot.delete_message(callback.message.chat.id, callback.message.message_id)


# Работа с обращениями
@moderator.message(Command("appeals"))
async def appeals(message: Message, state: FSMContext):
    """Вызов меню управления обращениями.

    Args:
        message (Message): _description_
        state (FSMContext): _description_
    """
    await state.clear()
    await message.answer(label.CHOOSE_ACTION, reply_markup=await get_download_appeals())


@moderator.callback_query(F.data.startswith("download_"))
async def download_appeals(callback: CallbackQuery):
    """Загрузка обращений.

    Args:
        callback (CallbackQuery): _description_
    """
    download_mode = callback.data.split("_")[-1]
    is_new = download_mode == "new"
    file_path = ""
    try:
        file_name = await save_appeals(callback.from_user.id, is_new)
        if not file_name:
            await callback.answer(label.EMPTY_NEW_APPEALS if is_new else label.EMPTY_ALL_APPEALS)
            logger.info(f"Список обращений (is_new={is_new}) пуст")
            return
        await callback.answer()
        file_path = os.path.join(os.getcwd(), file_name)
        await callback.message.answer_document(
            document=FSInputFile(file_path),
            caption=label.NEW_APPEALS if is_new else label.ALL_APPEALS,
        )
    except Exception as ex:
        logger.error(f"Невозможно загрузить БД - {ex}")
        await callback.message.answer(label.DOWNLOAD_FAIL)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        await close(callback)
