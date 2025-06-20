import logging
import sys

from src.core.settings import Settings


class Logger(logging.Logger):
    def __init__(self, settings: Settings):
        super().__init__(settings.NAME)

        self._setup_console_handler(settings.LOGGING_LEVEL)

    def _setup_console_handler(self, logging_level: int) -> None:
        self.setLevel(logging_level)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging_level)
        console_handler.setFormatter(formatter)
        self.addHandler(console_handler)
