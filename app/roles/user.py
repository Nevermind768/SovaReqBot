import os

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommandScopeChat, CallbackQuery, Message

import app.config.labels as label
from app.database.requests import (
    add_application,
    get_profile,
    get_role,
    is_banned,
    set_hash_link,
    set_profile,
    set_user,
)
from app.keyboards import (
    applicationBackKb,
    applicationKb,
    get_categories,
    policeKb,
    profileKb,
)
from app.logger import setup_logger
from app.states import Application, Reg, waiting_app
from app.utils.parser import get_commands, get_files

user = Router()

logger = setup_logger(__name__)


@user.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """/start. Запуск бота.

    Args:
        message (Message): _description_
        state (FSMContext): _description_
    """
    await state.clear()
    user_id = message.from_user.id
    await set_user(user_id)
    msg = await message.answer(label.HELLO, reply_markup=applicationKb)
    try:
        await message.bot.unpin_chat_message(message.chat.id)
    except Exception:
        pass
    await message.bot.pin_chat_message(
        chat_id=message.chat.id, message_id=msg.message_id
    )

    user_role = await get_role(user_id)
    await message.bot.set_my_commands(
        await get_commands(user_role),
        scope=BotCommandScopeChat(chat_id=message.chat.id),
    )


@user.message(Command("myid"))
async def show_id(message: Message, state: FSMContext):
    """Теневая команда для получения user_id в tg.

    Args:
        message (Message): _description_
        state (FSMContext): _description_
    """
    await state.clear()
    await message.answer(label.YOUR_ID.format(message.from_user.id))


# Работа с обращением
@user.callback_query(F.data == "application")
async def application(callback: CallbackQuery, state: FSMContext):
    """Начало для отправки обращения.

    Args:
        callback (CallbackQuery): _description_
        state (FSMContext): _description_
    """
    await state.clear()
    await callback.answer()
    if not await get_profile(callback.from_user.id):
        await state.set_data({waiting_app: True})
        await change_profile(callback, state)
    else:
        await choose_appeal_category(callback.message, state)


async def choose_appeal_category(message: Message, state: FSMContext):
    """Выбор категории обращения.

    Args:
        message (Message): _description_
        state (FSMContext): _description_
    """
    await state.set_state(Application.category)
    await message.answer(label.PICK_CATEGORY, reply_markup=await get_categories())


@user.callback_query(F.data.startswith("category_"), Application.category)
async def get_appeal_category(callback: CallbackQuery, state: FSMContext):
    """Получение категории обращения.

    Args:
        callback (CallbackQuery): _description_
        state (FSMContext): _description_
    """
    if await state.get_state() == Application.category:
        await callback.answer()
        await state.update_data({"main_msg": callback.message.message_id})
        picked_category = label.CATEGORIES[int(callback.data.split("_")[1])]
        await state.update_data(category=picked_category)

    await state.set_state(Application.address)
    await callback.message.answer(label.INPUT_ADDRESS, reply_markup=applicationBackKb)


@user.message(Application.address)
async def get_appeal_address(message: Message, state: FSMContext):
    """Получение адреса происшествия.

    Args:
        message (Message): _description_
        state (FSMContext): _description_
    """
    if await state.get_state() == Application.address:
        await state.update_data(address=message.text)
        data = await state.get_data()

        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=data.get("main_msg"),
            text=label.MIDDLE_APPEAL.format(
                category=data.get("category"), address=data.get("address")
            ),
        )
        await message.bot.delete_messages(
            message.chat.id, [message.message_id - 1, message.message_id]
        )

    await state.set_state(Application.body)
    await message.answer(label.BODY_START, reply_markup=applicationBackKb)


@user.message(Application.body)
async def get_appeal_body(message: Message, state: FSMContext, album: list = None):
    """Окончание заполнения обращения.

    Args:
        message (Message): _description_
        state (FSMContext): _description_
        album (list, optional): _description_. Defaults to None.
    """
    await state.update_data(body=message.md_text)

    if not await is_banned(message.from_user.id):
        attachments = await get_files(album if album else [message])
        if attachments:
            links = [
                f'https://{os.getenv("SERVER_HOST")}:{os.getenv("SERVER_PORT")}\
/{await set_hash_link(link)}'
                for link in attachments
            ]
            await state.update_data({"attachments": "\n".join(links)})

    await state.set_state(Application.police)
    await message.answer(label.CONTACT_POLICE, reply_markup=policeKb)
    await message.bot.delete_message(message.chat.id, message.message_id - 1)


@user.callback_query(F.data == "dont_contact_police", Application.police)
async def dont_contact_police(callback: CallbackQuery, state: FSMContext):
    callback.answer()
    await state.update_data(police=label.DONT_CONTACT_POLICE)
    await complete_application(
        callback.from_user.id, callback.message, state, [callback.message.message_id]
    )


@user.message(Application.police)
async def contact_police(message: Message, state: FSMContext):
    await state.update_data(police=message.text)
    await complete_application(
        message.from_user.id,
        message,
        state,
        [message.message_id - 1, message.message_id],
    )


async def complete_application(
    user_id, message: Message, state: FSMContext, msgs_delete
):
    data = await state.get_data()
    await state.clear()
    await message.answer(label.BODY_END)
    await message.bot.delete_messages(message.chat.id, msgs_delete)
    await message.bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=data.get("main_msg"),
        text=label.FULL_APPEAL.format(
            category=data.get("category"),
            address=data.get("address"),
            police=data.get("police"),
        ),
    )

    if await is_banned(user_id):
        return

    if data.get("body") or data.get("attachments"):
        await add_application(user_id, message.message_id, data)


@user.callback_query(F.data == "app_stepback")
async def step_back(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    last_state = await state.get_state()
    await callback.bot.delete_message(
        callback.message.chat.id, callback.message.message_id
    )
    if last_state == Application.address:
        data = await state.get_data()
        await callback.bot.delete_message(callback.message.chat.id, data["main_msg"])
        await choose_appeal_category(callback.message, state)
    elif last_state == Application.body:
        await get_appeal_category(callback, state)
    elif last_state == Application.police:
        await callback.bot.delete_message(
            callback.message.chat.id, callback.message.message_id - 1
        )
        await get_appeal_address(callback.message, state)


# Работа с профилем
@user.message(Command("profile"))
async def show_profile(message: Message, state: FSMContext):
    """Показ профиля пользователя.

    Args:
        message (Message): _description_
        state (FSMContext): _description_
    """
    await state.clear()
    profile_obj = await get_profile(message.from_user.id)
    if profile_obj:
        await message.answer(
            label.YOUR_PROFILE.format(
                name=profile_obj.fullName, contact=profile_obj.contact
            ),
            reply_markup=profileKb,
        )
    else:
        await state.set_state(Reg.full_name)
        await message.answer(label.INPUT_NAME)


@user.callback_query(F.data == "change_profile")
async def change_profile(callback: CallbackQuery, state: FSMContext):
    """Начало изменения профиля.

    Args:
        callback (CallbackQuery): _description_
        state (FSMContext): _description_
    """
    data = await state.get_data()
    await state.set_state(Reg.full_name)
    await callback.answer()
    await callback.message.answer(label.INPUT_NAME)
    if not data.get(waiting_app):
        await callback.bot.delete_message(
            callback.message.chat.id, callback.message.message_id
        )


@user.message(Reg.full_name)
async def profile_full_name(message: Message, state: FSMContext):
    """Получение имени.

    Args:
        message (Message): _description_
        state (FSMContext): _description_
    """
    await state.update_data(full_name=message.text)
    await state.set_state(Reg.contact)
    await message.answer(label.INPUT_CONTACT)


@user.message(Reg.contact)
async def profile_contact(message: Message, state: FSMContext):
    """Получение контакта.

    Args:
        message (Message): _description_
        state (FSMContext): _description_
    """
    await state.update_data(contact=message.text)
    data = await state.get_data()
    await set_profile(message.from_user.id, data)
    await state.clear()
    await message.answer(
        label.YOUR_PROFILE.format(
            name=data.get("full_name"), contact=data.get("contact")
        )
    )
    msg_ids = [i for i in range(message.message_id, message.message_id - 4, -1)]
    await message.bot.delete_messages(chat_id=message.chat.id, message_ids=msg_ids)
    if data.get(waiting_app):
        logger.info("Вызов заполнения обращения.")
        await choose_appeal_category(message, state)
