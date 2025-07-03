from logging import Filter, LogRecord
from typing import Any


class EndpointFilter(Filter):
    def __init__(
        self,
        paths: str | list[str],
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        if isinstance(paths, str):
            paths = [paths]

        self._paths = [path if path.startswith("/") else f"/{path}" for path in paths]

    def filter(self, record: LogRecord) -> bool:
        message = record.getMessage()

        for path in self._paths:
            if f" {path} " in message or f" {path}?" in message:
                return False

        return True
