class DBKeyError(Exception):
    """Ошибка отсутствия ключа в БД.

    Args:
        Exception (_type_): _description_
    """
    pass


class SameDataError(Exception):
    """Ошибка повторяющихся данных.

    Args:
        Exception (_type_): _description_
    """
    pass


class FileForwarder(Exception):
    """Ошибка при обработке запроса Flask.

    Args:
        Exception (_type_): _description_
    """
    pass
