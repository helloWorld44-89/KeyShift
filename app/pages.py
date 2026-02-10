from flask import Blueprint, render_template, request, url_for, redirect,flash, send_file,abort
from .models import user, SSID
from flask_bcrypt import bcrypt
from app.config.config import getConfig, updateConfig
from flask_login import  login_user, login_required, logout_user, current_user
import json
from pathlib import Path
from app import db
from app.utilities.genPW import genPW
from app.utilities.genQR import genQRCode
from app.config.crontab import cronChange,getCrontab,manualCron,createCron,deleteCron
from crontab import CronTab
import logging 
from .api.omada import OMADA
from .api.unifi import UNIFI

log = logging.getLogger(__name__)
bp = Blueprint("pages", __name__)

@bp.route("/")
def guest():
    ssids=db.session.query(SSID)
    guestSSID = ssids.filter_by(isGuest=True).first()
    return render_template("pages/index.html",guest=guestSSID)

@bp.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    users = user.query.all()
    ssids=db.session.query(SSID)
    guestSSID = ssids.filter_by(isGuest=True).first()
    cron = getCrontab(guestSSID.ssidName) 
    try:
        schedule=cron[0].slices.render()
    except Exception as e:
        schedule = '@daily'
    myConfig = getConfig()
    tab=request.args.get('tab','home')
    
    return render_template("pages/admin.html",users=users,config = myConfig,current_user=current_user,cron = cron,schedule=schedule,tab=tab,ssids=ssids,guest=guestSSID)

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        _username = request.form["username"]
        password = request.form["password"]
        _user = user.query.filter_by(username=_username).first()
        if _user:
            if(bcrypt.checkpw(password.encode('utf-8'),_user.password)):
                flash('Login success!','success')
                login_user(_user)
                log.info(f"{_username} logged in")
                return redirect(url_for("pages.admin"))
            else:
                log.warning(f"{_username} failed log in")
                flash('Incorrect Username or Password', 'danger')
        else:
            log.warning(f"{_username} failed log in")
            flash('Incorrect Username or Password', 'danger')
    return render_template("pages/login.html")

@bp.route("/updateConfig", methods=['POST'])
@login_required
def changeConfig():
    myConfig = getConfig()
    newConfig = request.form.to_dict()
    myConfig["apiUser"]["userName"] = newConfig["username"]
    myConfig["apiUser"]["passWord"] = newConfig["password"]
    myConfig["apiUser"]["apiKey"] = newConfig["apiKey"]
    myConfig["controllerIp"]=newConfig["controller_host"]
    myConfig["apiType"] = newConfig["api_type"]
    updateConfig(myConfig)
    log.info(f"Config updated")
    log.debug(f"Config updated {newConfig}")
    
    return redirect(url_for('pages.admin', tab=newConfig["tab"]))

@bp.route("/manualCron/<int:id>",methods=["POST"])
@login_required
def manual(id):
    time =request.form["schedule"]
    name = SSID.query.get(id).ssidName
    manualCron(time, name)
    log.info(f"Custom Cron schedule updated: {time}")
    return redirect(request.referrer)

@bp.route("users/add",methods=['POST'])
@login_required
def addNewUser():
    userName=request.form.get("newUsername")
    passWord=request.form.get("newPassword")
    passWordConfirm = request.form.get("newPasswordConfirm")
    role = request.form.get("newRole")
    if role == 'admin':
        role =1
    else:
        role = 0
    if passWord == passWordConfirm:
        user.newUser(userName,passWord,role)
        log.info(f"New User Created: {userName}")
        return redirect(url_for("pages.admin",tab="security"))
    else:
        log.error("Password Validation Failed for New User Creation")
        return redirect(url_for("pages.admin",tab="security",))
    
@bp.route("/init")
def initdb():
    #info=OMADA.initDBinfo()
    ssids=db.session.query(SSID)
    for i in ssids:
        genQRCode(i)
    return render_template("pages/login.html")

@bp.route("/qr/<name>")
def getImage(name):
    filePath = Path(f"static/img/{name}.png")
    if filePath.exists():
        log.info(f"Qr Code accessed for {name}")
        return send_file(f"static/img/{name}.png")
    else:
        log.error(f"QRCode getImage: 404 no image found for {filePath}")
        abort(404,description="Resource Not Found")

@bp.route("/changepw/<int:id>")
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
            log.debug(f"Password changed for {ssid.ssidName} to {pw}")
            return {"message":'Success'}
        else:
            log.error(f"Error changing password for {ssid.ssidName}: {info}")
            return {"message":f"Error changing password: {info}"}
    except Exception as e:
        log.error(f"Error changing password: {e}")
        return abort(500,f"An Error has occured: {e}")
    
@bp.route("/createCron/<int:id>")
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
            ssid.addRotation(rotate)
            cron =getCrontab(ssid.ssidName)
            createCron(ssid)
            log.info(f"Cron job created for SSID: {ssid.ssidName} with schedule {rotate}")
        return redirect(request.referrer)
    except Exception as e:
        log.error(f"Create Cron Error: {e}")
        return f"An Error has occured: {e}"
    
@bp.route("makeguest/<int:id>")
def guestSwap(id):
    ssid=SSID.query.get(id)
    ssid.makeGuest()
    return redirect(request.referrer)

@bp.route("/log",methods=["POST"])
@login_required
def logAction():
    try:
        data = request.get_json()
        log.info(f"{current_user.username}: {data['message']}")
        return {"message": "Action logged successfully"}
    except Exception as e:
        log.error(f"Error logging action: {e}")
        return {"message": f"An Error has occured: {e}"}, 500

@bp.route("/network/qr/<int:id>")
@login_required
def networkQR(id):
    guest = SSID.query.get(id)
    return render_template("pages/index.html",guest=guest)