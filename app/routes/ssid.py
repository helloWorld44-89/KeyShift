from flask import Blueprint, request, url_for, redirect, abort, render_template, send_file
from croniter import croniter
from flask_login import login_required
from app.routes.auth import admin_required
from pathlib import Path
from app.models import SSID
from app.config.config import getConfig
from app.config.crontab import createCron, cronChange, deleteCron, manualCron
from app.utilities.genPW import genPW
from app.utilities.genQR import genQRCode, qrPath
from app.api.omada import OMADA
from app.api.unifi import UNIFI
from app import db
import logging

bp = Blueprint("ssid", __name__)
log = logging.getLogger(__name__)





@bp.route("/changepw/<int:id>", methods=["POST"])
@login_required
def changePW(id:int):
    try:
        myconfig = getConfig()
        ssid=SSID.query.get(id)
        pw = request.values.get("pw", 'auto')
        if pw != 'auto':
            if myconfig["apiType"] == "omada":
                info=OMADA.changePW(ssid,pw)
            elif myconfig["apiType"] == "unifi":    
                info=UNIFI.changePW(ssid,pw)
            else:
                log.error(f"Invalid API Type: {myconfig['apiType']}")
                return abort(404, f"Error changing password: Invalid API Type {myconfig['apiType']}") 
        else:
            pw=genPW()
            if myconfig["apiType"] == "omada":
                info=OMADA.changePW(ssid,pw)
            elif myconfig["apiType"] == "unifi":    
                info=UNIFI.changePW(ssid,pw)
            else:
                log.error(f"Invalid API Type: {myconfig['apiType']}")
                return abort(404, f"Error changing password: Invalid API Type {myconfig['apiType']}")
        if info is True:
            ssid.ssidPW=pw
            db.session.add(ssid)
            db.session.commit()
            log.info(f"Password changed for {ssid.ssidName}")
            log.debug(f"Password changed for {ssid.ssidName}")
            genQRCode(ssid, pw)
            return redirect(url_for('admin.admin'))
        else:
            log.error(f"Error changing password for {ssid.ssidName}: {info}")
            return {"message":f"Error changing password: {info}"}
    except Exception as e:
        log.error(f"Error changing password: {e}")
        return abort(500,f"An Error has occured: {e}")
 

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
