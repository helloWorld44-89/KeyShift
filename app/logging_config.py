import logging
import logging.config
import logging.handlers
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


def logFilePath(app) -> str:
    """Where the application log is written (and read back by the admin log viewer)."""
    return app.config.get("LOG_FILE") or os.path.join(app.instance_path, "logs", "keyshift.log")


def addFileHandler(app):
    """
    Also write the application log to a rotating file, so admins can read it in the UI.
    Idempotent. Each process (Gunicorn, cron rotation jobs) appends to the same file;
    at 1 MB it rotates, keeping 3 old files.
    """
    path = os.path.abspath(logFilePath(app))
    root = logging.getLogger()
    if any(getattr(h, "baseFilename", None) == path for h in root.handlers):
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3)
    handler.setFormatter(logging.Formatter(
        LOGGING_CONFIG["formatters"]["debug" if LOG_LEVEL == "DEBUG" else "default"]["format"]))
    root.addHandler(handler)
