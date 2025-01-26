import logging
from datetime import datetime


def setup_logger(logger_name):
    """Настройка логгеров.

    Returns:
        Logger: Логгер.
    """
    log_filename = datetime.now().strftime("log_%Y-%m-%d_%H-%M-%S.log")

    if len(logging.getLogger().handlers) > 0:
        return logging.getLogger(logger_name)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(f"../data/logs/{log_filename}", mode="w"),
            logging.StreamHandler(),
        ],
    )

    # Custom
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    # Aiogram
    logging.getLogger("aiogram").setLevel(logging.ERROR)

    # SqlAlchemy
    logging.getLogger("sqlalchemy").setLevel(logging.ERROR)

    # Set Uvicorn and FastAPI log levels
    logging.getLogger("uvicorn").setLevel(logging.ERROR)
    logging.getLogger("fastapi").setLevel(logging.INFO)

    return logger
