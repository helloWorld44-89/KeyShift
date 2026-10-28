import os
import re

LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
_START = re.compile(r"^\[[^\]]+\] (DEBUG|INFO|WARNING|ERROR|CRITICAL)\b")

# Only the end of the file is read, so a big log never loads into memory
MAX_BYTES = 512 * 1024


def readLog(path: str, lines: int = 200, minLevel: str = "ALL") -> list[str]:
    """
    Return the last `lines` log entries at or above minLevel ("ALL" = everything).

    An entry is a log line plus any continuation lines (such as a traceback).
    Returns [] if the file doesn't exist yet.
    """
    try:
        with open(path, "rb") as f:
            size = f.seek(0, os.SEEK_END)
            f.seek(max(0, size - MAX_BYTES))
            raw = f.read().decode("utf-8", errors="replace")
            truncated = size > MAX_BYTES
    except FileNotFoundError:
        return []

    text = raw.split("\n", 1)[1] if truncated and "\n" in raw else raw  # drop the cut-off first line
    entries = []  # [severity, text]
    for line in text.splitlines():
        m = _START.match(line)
        if m:
            entries.append([LEVELS[m.group(1)], line])
        elif entries:
            entries[-1][1] += "\n" + line
        # lines before the first entry (rotation debris) are ignored

    floor = LEVELS.get(minLevel, 0)
    return [t for sev, t in entries if sev >= floor][-lines:]
