from aiogram.filters import Filter
from aiogram.types import Message

from app.database.requests import get_role
from app.roles import Role


class RoleFilter(Filter):
    """Фильтрация сообщений по роли.

    Args:
        Filter (_type_): _description_
    """

    def __init__(self, role: Role):
        """Назначение роли.

        Args:
            role (Role): Роль.
        """
        self.role = role

    async def __call__(self, message: Message):
        """Фильтрация роли.

        Args:
            message (Message): Объект сообщения.

        Returns:
            bool: Доступность для заданной роли.
        """
        user_role = await get_role(message.from_user.id)
        return user_role.value >= self.role.value
