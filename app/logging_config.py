import logging
import logging.config
import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "default": {
            "format": "[%(asctime)s] %(levelname)s in %(name)s: %(message)s",
        },
        "debug": {
            "format": "[%(asctime)s] %(levelname)s %(name)s:%(lineno)d — %(message)s",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "debug" if LOG_LEVEL == "DEBUG" else "default",
            "stream": "ext://sys.stdout",
        }
    },

    "root": {
        "level": LOG_LEVEL,
        "handlers": ["console"],
    },
}
