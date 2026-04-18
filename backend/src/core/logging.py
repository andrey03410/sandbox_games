import logging
from contextvars import ContextVar
from logging.config import dictConfig

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def setup_logging(level: str = "INFO") -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "request_id": {"()": RequestIdFilter},
            },
            "formatters": {
                "default": {
                    "format": (
                        "%(asctime)s | %(levelname)-7s | %(name)s "
                        "| rid=%(request_id)s | %(message)s"
                    ),
                    "datefmt": "%Y-%m-%dT%H:%M:%S",
                },
            },
            "handlers": {
                "stderr": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "filters": ["request_id"],
                    "stream": "ext://sys.stderr",
                },
            },
            "loggers": {
                "src": {"level": level, "handlers": ["stderr"], "propagate": False},
                "uvicorn": {"level": "INFO", "handlers": ["stderr"], "propagate": False},
                "uvicorn.error": {"level": "INFO", "handlers": ["stderr"], "propagate": False},
                "uvicorn.access": {"level": "INFO", "handlers": ["stderr"], "propagate": False},
            },
            "root": {"level": level, "handlers": ["stderr"]},
        }
    )
