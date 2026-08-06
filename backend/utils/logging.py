import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from typing import ClassVar

DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FILE = "backend.log"
DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(lineno)d | %(message)s"


class LogManager:
    _instance: ClassVar["LogManager | None"] = None
    _loggers: ClassVar[dict[str, logging.Logger]] = {}

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._configure_root_logger()
        return cls._instance

    def _configure_root_logger(self):
        root_logger = logging.getLogger()
        root_logger.setLevel(DEFAULT_LOG_LEVEL)
        formatter = logging.Formatter(DEFAULT_LOG_FORMAT)

        has_console = any(
            isinstance(handler, logging.StreamHandler)
            for handler in root_logger.handlers
        )
        if not has_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

        has_file = any(
            isinstance(handler, TimedRotatingFileHandler)
            for handler in root_logger.handlers
        )
        if not has_file:
            file_handler = TimedRotatingFileHandler(
                DEFAULT_LOG_FILE,
                when="midnight",
                interval=1,
                backupCount=7,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

    def get_logger(self, name: str) -> logging.Logger:
        if name not in self._loggers:
            logger = logging.getLogger(name)
            logger.setLevel(DEFAULT_LOG_LEVEL)
            self._loggers[name] = logger
        return self._loggers[name]


log_manager = LogManager()


def get_app_logger(name: str = __name__) -> logging.Logger:
    return log_manager.get_logger(name)
