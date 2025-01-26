from aiogram.fsm.state import State, StatesGroup


class Reg(StatesGroup):
    """States для заполнения профиля пользователя.

    Args:
        StatesGroup (_type_): _description_
    """

    full_name = State()
    contact = State()


class Application(StatesGroup):
    """States для отправления обращения.

    Args:
        StatesGroup (_type_): _description_
    """

    category = State()
    address = State()
    body = State()
    police = State()


class PickModerator(StatesGroup):
    """States для выбора модератора.

    Args:
        StatesGroup (_type_): _description_
    """

    id = State()


class BanUser(StatesGroup):
    """States для бана пользователя.

    Args:
        StatesGroup (_type_): _description_
    """

    ids = State()
    reason = State()
    term = State()


class UnbanUser(StatesGroup):
    """States для разбана пользователя.

    Args:
        StatesGroup (_type_): _description_
    """

    ids = State()


# Ключ для вызова отправления обращения сразу после заполнения профиля
waiting_app = "waiting_app"
