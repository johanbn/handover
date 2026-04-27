"""
Central logging configuration.

Usage:

    from ruter_chatbot.logger import get_logger

    logger = get_logger(__name__)
"""

import logging
import logging.config
import sys
from pathlib import Path
from typing import Optional

DEFAULT_LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,  # important: do NOT disable root/3rd-party loggers
    "formatters": {
        "console": {
            "format": "%(asctime)s  %(levelname)-8s  %(name)-22s  %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "console_short": {
            "format": "%(levelname)-8s  %(name)-22s  %(message)s",
            "datefmt": "%H:%M:%S",
        },
        "file": {
            "format": "%(asctime)s  %(levelname)-8s  %(name)-30s  %(message)s  (%(filename)s:%(lineno)d)",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "console",
            "stream": "ext://sys.stderr",  # better visibility in many terminals
        },
        "console_debug": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "console_short",
            "stream": "ext://sys.stderr",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "file",
            "filename": "logs/app.log", # placement not final
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "encoding": "utf-8",
        },
    },
    "loggers": {
        # Root logger - catch-all
        "": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        # Debug for the project
        "ruter_chatbot": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False,
        },
        # Very noisy packages – usually turned down
        "urllib3": {"level": "WARNING"},
        "httpx": {"level": "WARNING"},
        "httpcore": {"level": "WARNING"},
        "asyncio": {"level": "WARNING"},
        "aiobotocore": {"level": "WARNING"},
    },
}

def get_logger(name: str, *, force_level: Optional[str | int] = None) -> logging.Logger:
    """
    Get a configured logger for a module.

    Usage:

        # straightforward
        logger = get_logger(__name__)

        # with forced log level - works with any of the aliases in Python's logging library if you know them.
        leveled_logger = get_logger(__name__, force_level=logging.DEBUG) # or "DEBUG", or 10, for same effect.
    """
    if not logging.getLogger().handlers:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)

        logging.config.dictConfig(DEFAULT_LOGGING)

        if force_level is not None:
            logging.getLogger().setLevel(force_level)
            logging.getLogger("ruter_chatbot").setLevel(force_level)
    
    return logging.getLogger(name)
