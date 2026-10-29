from flask import Blueprint, request, url_for, redirect, abort, render_template, send_file, jsonify
from flask_login import current_user
from croniter import croniter
from flask_login import login_required
from app.routes.auth import admin_required
from pathlib import Path
from app import limiter
from app.models import SSID
from app.config.crontab import createCron, cronChange, deleteCron, manualCron
from app.rotation import rotate
from app.passwordList import rotateFromList, ListUnavailable
from app.settings import getPolicy
from app.utilities.passwordPolicy import checkPassword
from app.utilities.genQR import qrPath
import logging

bp = Blueprint("ssid", __name__)
log = logging.getLogger(__name__)





@bp.route("/changepw/<int:id>", methods=["POST"])
@login_required
def changePW(id:int):
    """Change an SSID's password: the given `pw`, or a generated one (pw=auto, the default)."""
    ssid = SSID.query.get_or_404(id)
    pw = request.values.get("pw", 'auto')
    if pw != 'auto':
        problems = checkPassword(pw, getPolicy())
        if problems:
            return {"message": " ".join(problems)}, 400
    try:
        if pw == 'auto' and ssid.listEnabled:
            result = rotateFromList(ssid, attempts=1)
        else:
            result = rotate(ssid, None if pw == 'auto' else pw, attempts=1)
    except ListUnavailable as e:
        return {"message": str(e)}, 409
    except Exception as e:
        log.error(f"Error changing password: {e}")
        return {"message": "An error has occured changing the password"}, 500
    if result.ok:
        return redirect(url_for('admin.admin'))
    return {"message": "The controller did not accept the password change. "
                       "It is saved and will be retried; see the SSID's rotation status."}, 502

@bp.route("/ssid/<int:id>/password", methods=["POST"])
@admin_required
@limiter.limit("30 per minute")
def revealPassword(id):
    """Return an SSID's current password to an admin who asked for it (Show / Copy on the home tab)."""
    ssid = SSID.query.get_or_404(id)
    log.info(f"{current_user.username} revealed the password of {ssid.ssidName}")
    response = jsonify({"password": ssid.ssidPW or ""})
    response.headers["Cache-Control"] = "no-store"
    return response

def _sendQR(ssid):
    """Return the stored QR image for an SSID, or 404 if it hasn't been generated."""
    filePath = Path(qrPath(ssid))
    if filePath.exists():
        log.info(f"Qr Code accessed for {ssid.ssidName}")
        return send_file(filePath, mimetype="image/png", max_age=0)
    log.error(f"QRCode: 404 no image found for {ssid.ssidName}")
    abort(404, description="Resource Not Found")


@bp.route("/qr/<int:id>")
@login_required
def getImage(id):
    return _sendQR(SSID.query.get_or_404(id))

@bp.route("/createCron/<int:id>", methods=["POST"])
@admin_required
def AddCronJob(id):
    """Set, change or remove (rotateFrequency=None) the rotation schedule of an SSID."""
    ssid = SSID.query.get_or_404(id)
    rotate = request.values.get("rotateFrequency")
    back = request.referrer or url_for("admin.admin")
    try:
        if rotate == "None":
            ssid.addRotation(None)
            deleteCron(ssid)
            log.info(f"Cron job deleted for SSID: {ssid.ssidName}")
            return redirect(back)
        if not rotate or not croniter.is_valid(rotate):
            log.warning(f"Invalid rotateFrequency {rotate!r} for SSID: {ssid.ssidName}")
            return {"message": "rotateFrequency must be a valid cron expression"}, 400
        ssid.addRotation(rotate)
        if cronChange(ssid):
            log.info(f"Cron time for SSID: {ssid.ssidName} updated to {rotate}.")
        elif createCron(ssid):
            log.info(f"Cron job created for SSID: {ssid.ssidName} with schedule {rotate}")
        else:
            return {"message": "Could not save the rotation schedule"}, 500
        return redirect(back)
    except Exception as e:
        log.error(f"Create Cron Error: {e}")
        return {"message": "An error has occured setting the rotation schedule"}, 500

@bp.route("/network/qr/<int:id>")
@login_required
def networkQR(id):
    guest = SSID.query.get_or_404(id)
    return render_template("pages/index.html", guest=guest, qr_url=url_for("ssid.getImage", id=guest.id))

@bp.route("/api/guest")
def getGuestQR():
    """Public: serves the QR for the guest SSID only. Every other QR requires login."""
    ssid = SSID.query.filter_by(isGuest=True).first()
    if ssid is None:
        abort(404, description="No guest SSID configured")
    return _sendQR(ssid)
