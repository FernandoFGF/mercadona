"""
Configuración de logging. Llamar a setup_logging() una vez al arrancar.
"""
import logging
import logging.handlers
from pathlib import Path

import config


_LOGGER_NAME = "mercadona_grocery"
_FMT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if logger.handlers:
        return logger
    logger.setLevel(level)
    fmt = logging.Formatter(_FMT, datefmt=_DATEFMT)

    # Fichero rotativo: 1MB x 3 backups
    log_path = config.DATA_DIR / "app.log"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    except OSError:
        pass  # Si no se puede escribir el log, seguimos sin él

    # Consola solo para WARNING+
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.WARNING)
    stream_handler.setFormatter(fmt)
    logger.addHandler(stream_handler)

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    base = logging.getLogger(_LOGGER_NAME)
    return base.getChild(name) if name else base
