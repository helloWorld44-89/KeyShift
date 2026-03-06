from flask import Blueprint, request, url_for, redirect, abort, render_template, send_file
from flask_login import login_required
from pathlib import Path
from app.models import SSID
from app.config.config import getConfig
from app.config.crontab import createCron, cronChange, deleteCron, manualCron
from app.utilities.genPW import genPW
from app.utilities.genQR import genQRCode
from app.api.omada import OMADA
from app.api.unifi import UNIFI
from app import db
import logging

bp = Blueprint("ssid", __name__)
log = logging.getLogger(__name__)





@bp.route("/changepw/<int:id>")
@login_required
def changePW(id:int):
    try:
        myconfig = getConfig()
        ssid=SSID.query.get(id)
        pw = request.args.get("pw",'auto')
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
 

@bp.route("/qr/<int:id>")
@login_required
def getImage(id):
    ssid = SSID.query.get_or_404(id)
    filePath = Path(f"static/img/{ssid.ssidName}.png")
    if filePath.exists():
        log.info(f"Qr Code accessed for {ssid.ssidName}")
        return send_file(f"static/img/{ssid.ssidName}.png")
    else:
        log.error(f"QRCode getImage: 404 no image found for {filePath}")
        abort(404,description="Resource Not Found")

@bp.route("/createCron/<int:id>")
@login_required
def AddCronJob(id):
    try:
        rotate=request.args.get("rotateFrequency")
        ssid=SSID.query.get(id)
        if rotate == "None":
            deleteCron(ssid)
            ssid.addRotation(None)
            log.info(f"Cron job deleted for SSID: {ssid.ssidName}")
            return redirect(request.referrer)
        else:           
            if ssid.rotateFrequency is not None:
                ssid.addRotation(rotate)
                cronChange(ssid)
                log.info(f'Cron Time for SSID: {ssid.ssidName} updated to {rotate}.')
            else:
                ssid.addRotation(rotate)
                createCron(ssid)
                log.info(f"Cron job created for SSID: {ssid.ssidName} with schedule {rotate}")
        return redirect(request.referrer)
    except Exception as e:
        log.error(f"Create Cron Error: {e}")
        return f"An Error has occured: {e}"

@bp.route("/network/qr/<int:id>")
@login_required
def networkQR(id):
    guest = SSID.query.get(id)
    return render_template("pages/index.html",guest=guest)