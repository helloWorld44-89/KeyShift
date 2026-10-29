"""Admin management of per-SSID password lists. Every route returns the list's current state as JSON."""
import logging

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app import db
from app.models import SSID, PasswordListEntry
from app.passwordList import MAX_ENTRIES, MODES, END_ACTIONS, isFinished, mode, onEnd
from app.routes.auth import admin_required
from app.settings import getPolicy
from app.utilities.passwordPolicy import checkPassword

bp = Blueprint("passwordLists", __name__, url_prefix="/ssid/<int:id>/passwords")
log = logging.getLogger(__name__)


def _state(ssid: SSID):
    entries = list(ssid.entries)
    body = {
        "enabled": bool(ssid.listEnabled),
        "mode": mode(ssid),
        "onEnd": onEnd(ssid),
        "index": ssid.listIndex or 0,
        "finished": isFinished(ssid),
        "rotating": bool(ssid.pwRotate),
        "entries": [{"id": e.id, "position": e.position + 1, "password": e.password,
                     "current": e.id == ssid.listCurrentId,
                     "lastUsed": e.lastUsed.isoformat(sep=" ", timespec="minutes") if e.lastUsed else None}
                    for e in entries],
    }
    response = jsonify(body)
    response.headers["Cache-Control"] = "no-store"
    return response


def _renumber(ssid: SSID):
    for pos, entry in enumerate(ssid.entries):
        entry.position = pos


def _error(message, code=400):
    return {"message": message}, code


@bp.route("", methods=["GET"])
@admin_required
def listPasswords(id):
    ssid = SSID.query.get_or_404(id)
    log.info(f"{current_user.username} viewed the password list of {ssid.ssidName}")
    return _state(ssid)


@bp.route("/add", methods=["POST"])
@admin_required
def addPasswords(id):
    """Add passwords, one per line. All lines are checked first; nothing is added if any is rejected."""
    ssid = SSID.query.get_or_404(id)
    lines = [line.rstrip("\r") for line in request.form.get("passwords", "").split("\n")]
    lines = [line for line in lines if line.strip()]
    if not lines:
        return _error("Enter at least one password.")
    if len(ssid.entries) + len(lines) > MAX_ENTRIES:
        return _error(f"A list can hold at most {MAX_ENTRIES} passwords.")
    policy = getPolicy()
    problems = [f"Line {n}: {' '.join(checkPassword(line, policy))}"
                for n, line in enumerate(lines, 1) if checkPassword(line, policy)]
    if problems:
        return _error(" ".join(problems[:5]) + (f" (+{len(problems) - 5} more)" if len(problems) > 5 else ""))
    start = len(ssid.entries)
    for offset, line in enumerate(lines):
        db.session.add(PasswordListEntry(ssid_id=ssid.id, password=line, position=start + offset))
    db.session.commit()
    db.session.refresh(ssid)
    log.info(f"{current_user.username} added {len(lines)} password(s) to the list of {ssid.ssidName}")
    return _state(ssid)


@bp.route("/<int:entryId>/delete", methods=["POST"])
@admin_required
def deletePassword(id, entryId):
    ssid = SSID.query.get_or_404(id)
    entry = db.session.get(PasswordListEntry, entryId)
    if entry is None or entry.ssid_id != ssid.id:
        return _error("No such entry.", 404)
    if entry.position < (ssid.listIndex or 0):
        ssid.listIndex -= 1
    if ssid.listCurrentId == entry.id:
        ssid.listCurrentId = None
    ssid.entries.remove(entry)
    db.session.flush()
    _renumber(ssid)
    db.session.commit()
    log.info(f"{current_user.username} removed an entry from the list of {ssid.ssidName}")
    return _state(ssid)


@bp.route("/<int:entryId>/move", methods=["POST"])
@admin_required
def movePassword(id, entryId):
    ssid = SSID.query.get_or_404(id)
    entries = list(ssid.entries)
    entry = next((e for e in entries if e.id == entryId), None)
    if entry is None:
        return _error("No such entry.", 404)
    step = {"up": -1, "down": 1}.get(request.form.get("direction"))
    if step is None:
        return _error("direction must be up or down.")
    target = entries.index(entry) + step
    if 0 <= target < len(entries):
        entries[target].position, entry.position = entry.position, entries[target].position
        db.session.commit()
        db.session.refresh(ssid)
    return _state(ssid)


@bp.route("/settings", methods=["POST"])
@admin_required
def passwordListSettings(id):
    ssid = SSID.query.get_or_404(id)
    newMode = request.form.get("mode", mode(ssid))
    newEnd = request.form.get("onEnd", onEnd(ssid))
    if newMode not in MODES or newEnd not in END_ACTIONS:
        return _error("Unknown mode or end-of-list action.")
    enabled = request.form.get("enabled") in ("1", "on", "true")
    if enabled and not ssid.entries:
        return _error("Add at least one password before turning the list on.")
    ssid.listMode, ssid.listOnEnd, ssid.listEnabled = newMode, newEnd, enabled
    db.session.commit()
    log.info(f"{current_user.username} set the list of {ssid.ssidName}: enabled={enabled} "
             f"mode={newMode} onEnd={newEnd}")
    return _state(ssid)


@bp.route("/reset", methods=["POST"])
@admin_required
def resetPasswordList(id):
    """Go back to the first entry. Does not touch the schedule; set it again from the Rotate menu."""
    ssid = SSID.query.get_or_404(id)
    ssid.listIndex = 0
    ssid.listCurrentId = None
    db.session.commit()
    log.info(f"{current_user.username} reset the list of {ssid.ssidName}")
    return _state(ssid)
