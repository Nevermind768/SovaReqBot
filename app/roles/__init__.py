from enum import Enum


class Role(Enum):
    """Класс Enum ролей пользователей."""

    USER = 0
    MODERATOR = 1
    ADMIN = 2

    @classmethod
    def from_value(cls, value: int):
        """_summary_

        Args:
            value (int): Номер роли.

        Raises:
            ValueError: Отсутствует роли по значению.

        Returns:
            Role: Роль пользователя.
        """
        for role in cls:
            if role.value == value:
                return role
        raise ValueError(f"No {cls.__name__} with value {value}")

    @property
    def name(self):
        """Переопределение property.

        Returns:
            str: name в lower case
        """
        return super().name.lower()
