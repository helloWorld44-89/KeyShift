"""
Per-SSID password lists: rotation picks the next password from a list instead of generating one.

Picking never changes anything. The list position moves only when the controller accepted
the password (inside rotate()'s success transaction), so a failed change doesn't skip an
entry, and a retry re-uses the same entry.
"""
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime

from app import db
from app.config.crontab import deleteCron
from app.models import SSID, PasswordListEntry
from app.rotation import alert, rotate, RotationResult

log = logging.getLogger("passwordList")

MODES = ("sequential", "random", "random-norepeat")
END_ACTIONS = ("restart", "stop")
MAX_ENTRIES = 500


class ListUnavailable(Exception):
    """The list can't supply a password right now (empty, or finished with 'stop')."""


@dataclass
class Pick:
    entry: PasswordListEntry
    newIndex: int


def mode(ssid: SSID) -> str:
    return ssid.listMode if ssid.listMode in MODES else "sequential"


def onEnd(ssid: SSID) -> str:
    return ssid.listOnEnd if ssid.listOnEnd in END_ACTIONS else "restart"


def isFinished(ssid: SSID) -> bool:
    """A sequential list set to 'stop' whose last entry has been used."""
    return bool(ssid.listEnabled and ssid.entries and mode(ssid) == "sequential"
                and onEnd(ssid) == "stop" and (ssid.listIndex or 0) >= len(ssid.entries))


def pickNext(ssid: SSID) -> Pick | None:
    """The entry to apply next, or None if the list is empty or finished."""
    entries = list(ssid.entries)
    if not entries:
        return None
    if ssid.pendingPW:  # an earlier attempt didn't reach the controller: try the same password again
        for pos, entry in enumerate(entries):
            if entry.password == ssid.pendingPW:
                return Pick(entry, pos + 1)
    if mode(ssid) == "sequential":
        index = ssid.listIndex or 0
        if index >= len(entries):
            if onEnd(ssid) == "stop":
                return None
            index = 0
        return Pick(entries[index], index + 1)
    candidates = entries
    if mode(ssid) == "random-norepeat" and len(entries) > 1:
        candidates = [e for e in entries if e.id != ssid.listCurrentId]
    entry = secrets.choice(candidates)
    return Pick(entry, entries.index(entry) + 1)


def _markUsed(ssid: SSID, pick: Pick) -> bool:
    """Record a successful change. Returns True if this was the last entry of a 'stop' list."""
    ssid.listIndex = pick.newIndex
    ssid.listCurrentId = pick.entry.id
    pick.entry.lastUsed = datetime.now()
    if isFinished(ssid):
        ssid.pwRotate = False
        ssid.rotateFrequency = None
        return True
    return False


def rotateFromList(ssid: SSID, attempts: int = 3, **kwargs) -> RotationResult:
    """Change the SSID to the next password in its list. Raises ListUnavailable if there is none."""
    pick = pickNext(ssid)
    if pick is None:
        if not ssid.entries:
            raise ListUnavailable("The password list is empty.")
        raise ListUnavailable("The password list has been used up. Add entries or reset it.")
    stopped = []
    result = rotate(ssid, pick.entry.password, attempts=attempts,
                    onSuccess=lambda: stopped.append(_markUsed(ssid, pick)), **kwargs)
    if result.ok and stopped and stopped[0]:
        deleteCron(ssid)
        log.warning(f"Password list for {ssid.ssidName} is used up; rotation stopped")
        alert(f"KeyShift: the last password in the list for SSID '{ssid.ssidName}' is now active "
              f"and rotation has stopped. Add entries or reset the list, then set a schedule.")
    return result


def rotateScheduled(ssid: SSID, attempts: int = 3, **kwargs) -> RotationResult | None:
    """What the cron job runs: the list if the SSID uses one, otherwise a generated password."""
    if not ssid.listEnabled:
        return rotate(ssid, attempts=attempts, **kwargs)
    try:
        return rotateFromList(ssid, attempts=attempts, **kwargs)
    except ListUnavailable as e:
        if isFinished(ssid):  # the list was changed to 'stop' after it had already run past its end
            ssid.pwRotate = False
            ssid.rotateFrequency = None
            db.session.commit()
            deleteCron(ssid)
        alert(f"KeyShift: scheduled rotation of '{ssid.ssidName}' skipped: {e}")
        return None
