from aiogram.types import ContentType, Message

from app.config.commands import COMMANDS, Role

accepted_types = [ContentType.VIDEO, ContentType.VOICE, ContentType.VIDEO_NOTE]


async def get_files(messages: list[Message]):
    """Получение пути файлов из объектов Message

    Args:
        messages (list[Message]): Список сообщений.

    Returns:
        list: Список путей файлов.
    """
    res = []

    for msg in messages:
        msg_type: ContentType = msg.content_type
        file_info = None
        if msg_type == ContentType.PHOTO:
            file_info = getattr(msg, msg_type.value)[-1]
        elif msg_type in accepted_types:
            file_info = getattr(msg, msg_type.value)

        if file_info:
            res.append(file_info.file_id)
    return res


async def get_commands(user_role: Role):
    """Получение доступных команд для заданной роли.

    Args:
        user_role (Role): Роль пользователя.

    Returns:
        list: Доступные команды.
    """
    cmds = []
    for role in Role:
        if role.value <= user_role.value:
            cmds.extend(COMMANDS.get(role))
    return cmds
