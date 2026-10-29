"""
Changing a Wi-Fi password on the controller without losing track of it.

The new password is written to the database (as pendingPW) *before* the controller
is called, so a crash or a lost response never leaves a password only the
controller knows. A failed change keeps the pending password, is retried, counted,
logged and reported; the next attempt re-uses the pending password instead of
inventing another one.
"""
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime

import requests

from app import db
from app.api.omada import OMADA
from app.api.unifi import UNIFI
from app.config.config import getConfig
from app.models import SSID
from app.settings import getPolicy
from app.utilities.passwordPolicy import generate
from app.utilities.genQR import genQRCode

log = logging.getLogger("rotation")


@dataclass
class RotationResult:
    ok: bool
    error: str | None = None


def _controllerChange(ssid: SSID, newPW: str):
    """Ask the controller to set the password. True on success, otherwise an error string."""
    apiType = getConfig()["apiType"]
    if apiType == "unifi":
        return UNIFI.changePW(ssid, newPW)
    if apiType == "omada":
        return OMADA.changePW(ssid, newPW)
    return f"Unknown API type: {apiType}"


def alert(message: str):
    """Log an error and, if ALERT_WEBHOOK_URL is set, post it there (Slack/Discord-style JSON)."""
    log.error(message)
    url = os.environ.get("ALERT_WEBHOOK_URL")
    if not url:
        return
    try:
        requests.post(url, json={"text": message, "content": message}, timeout=5)
    except Exception as e:
        log.error(f"Could not send rotation alert: {e}")


def rotate(ssid: SSID, newPW: str | None = None, attempts: int = 3, delay: float = 5,
           sleep=time.sleep) -> RotationResult:
    """
    Change the password of an SSID. Uses newPW if given, else a password left pending
    by an earlier failed attempt, else a freshly generated one. Never raises for a
    controller failure; check the result.
    """
    password = newPW or ssid.pendingPW or generate(getPolicy())

    ssid.pendingPW = password
    ssid.lastAttempt = datetime.now()
    db.session.commit()

    result = None
    for attempt in range(1, attempts + 1):
        result = _controllerChange(ssid, password)
        if result is True:
            break
        log.warning(f"Password change for {ssid.ssidName} failed (attempt {attempt}/{attempts})")
        if attempt < attempts:
            sleep(delay * attempt)

    if result is True:
        ssid.ssidPW = password
        ssid.pendingPW = None
        ssid.lastChanged = datetime.now()
        ssid.failCount = 0
        ssid.lastError = None
        db.session.commit()
        log.info(f"Password changed for {ssid.ssidName}")
        genQRCode(ssid)
        return RotationResult(True)

    ssid.failCount = (ssid.failCount or 0) + 1
    ssid.lastError = str(result)[:500]
    db.session.commit()
    alert(f"KeyShift: password rotation for SSID '{ssid.ssidName}' failed "
          f"({ssid.failCount} in a row). The new password is saved and will be retried. "
          f"Last error: {ssid.lastError}")
    return RotationResult(False, ssid.lastError)
