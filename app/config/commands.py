from app.roles import Role
from aiogram.types import BotCommand

# Команды ролей
COMMANDS = {
    Role.USER: [
        BotCommand(command="start", description="Обновить бота"),
        BotCommand(command="profile", description="Изменить анкету"),
    ],
    Role.MODERATOR: [
        BotCommand(command="appeals", description="Просмотреть обращения"),
        BotCommand(command="users", description="Управление пользователями"),
    ],
    Role.ADMIN: [
        BotCommand(command="moderators", description="Управление модераторами")
    ],
}
