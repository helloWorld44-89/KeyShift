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
    users = user.query.all()
    if len(users) == 0:
        return redirect(url_for("pages.initApp"))
    ssids=db.session.query(SSID)
    guestSSID = ssids.filter_by(isGuest=True).first()
    return render_template("pages/index.html",guest=guestSSID)

@bp.route("/initApp", methods=["GET","POST"])
def initApp():
    return render_template("pages/initApp.html")

@bp.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    users = user.query.all()
    if len(users) == 0:
        return redirect(url_for("pages.initApp"))
    ssids=db.session.query(SSID)
    guestSSID = ssids.filter_by(isGuest=True).first()
    if guestSSID:
        cron = getCrontab(guestSSID.ssidName) 
    else:
        cron = '@daily root /usr/local/bin/python3 /app/app/cron.py'
    try:
        schedule=cron[0].slices.render()
    except Exception as e:
        schedule = '@daily'
    myConfig = getConfig()
    tab=request.args.get('tab','home')
    
    return render_template("pages/admin.html",users=users,config = myConfig,current_user=current_user,cron = cron,schedule=schedule,tab=tab,ssids=ssids,guest=guestSSID)

@bp.route("/login", methods=["GET", "POST"])
def login():
    print(len(user.query.all()))
    if len(user.query.all()) < 1:
        log.info("No users found, redirecting to initApp")
        return redirect(url_for("pages.initApp"))
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

@bp.route("/logout")
@login_required
def logout():
    log.info(f"{current_user.username} logged out")
    logout_user()
    return redirect(url_for("pages.login"))

@bp.route("/updateConfig", methods=['POST'])
@login_required
def changeConfig():
    myConfig = getConfig()
    newConfig = request.form.to_dict()
    myConfig["apiType"] = newConfig["api_type"]
    if myConfig["apiType"] == 'unifi':
        myConfig["apiUser"]["apiKey"] = newConfig["apiKey"] or None
    elif myConfig["apiType"] == 'omada':
        myConfig["apiUser"]["userName"] = newConfig["username"] or None
        myConfig["apiUser"]["passWord"] = newConfig["password"] or None
    else:
        log.error(f'API Type Unknown: {newConfig["api_type"]}')
    myConfig["controllerIp"]=newConfig["controller_host"]
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
def addNewUser():
    try:
        if current_user.is_authenticated or request.referrer.endswith("/initApp"):
            userName=request.form.get("newUsername")
            passWord=request.form.get("newPassword")
            passWordConfirm = request.form.get("newPasswordConfirm")
            role = request.form.get("newRole")
            if "/initApp" not in request.referrer: 
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
            else:
                userName=request.form.get("newUsername")
                passWord=request.form.get("newPassword")
                role = 1
                user.newUser(userName,passWord,role)
                log.info(f"Initial User Created: {userName}")
                return {"message": "Success"}
        else:
            log.error("Unauthorized User Creation Attempt")
            return {"message": "Unauthorized"}, 401
    except Exception as e:
        log.error(f"Error creating user: {e}")
        return {"message": f"An Error has occured: {e}"}, 500

@bp.route("/init")
def initdb():
    try:
        if current_user.is_authenticated or request.referrer.endswith("/initApp"):
            config=getConfig()
            if config['apiType']=='unifi':
                info=UNIFI.initDBinfo()
            elif config['apiType']=='omada':
                info = OMADA.initDBinfo()
            else:
                log.error(f"APi Type Error: {config['apiType']}")
                return {"message":"Incorrect ApiType in config"}
            ssids=db.session.query(SSID)
            x=0
            for i in ssids:
                genQRCode(i)
                x+=1
            return {"message": "Success", "details": f'{x} SSIDs Initialized'}
        else:
            log.error("Unauthorized DB Initialization Attempt")
            return {"message": "Unauthorized"}, 401
    except Exception as e:
        log.error(e)
        return {"message": f"An Error has occured: {e}"}, 500

@bp.route("/qr/<name>")
@login_required
def getImage(name):
    filePath = Path(f"static/img/{name}.png")
    if filePath.exists():
        log.info(f"Qr Code accessed for {name}")
        return send_file(f"static/img/{name}.png")
    else:
        log.error(f"QRCode getImage: 404 no image found for {filePath}")
        abort(404,description="Resource Not Found")

@bp.route("/changepw/<int:id>")
@login_required
def changePW(id:int):
    try:
        myconfig = getConfig()
        print(id)
        ssid=SSID.query.get(id)
        print(ssid)
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
            return redirect(url_for('pages.admin'))
        else:
            log.error(f"Error changing password for {ssid.ssidName}: {info}")
            return {"message":f"Error changing password: {info}"}
    except Exception as e:
        log.error(f"Error changing password: {e}")
        return abort(500,f"An Error has occured: {e}")
    
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
            
            print(ssid.rotateFrequency)
            
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
    
@bp.route("makeguest/<int:id>")
@login_required
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

@bp.route("/newConfig", methods=['POST'])
def newConfig():
    try:
        if request.referrer.endswith("/initApp"):
            myConfig = getConfig()
            newConfig = request.form.to_dict()
            myConfig["apiType"] = newConfig["api_type"]
            if myConfig["apiType"] == 'unifi':
                myConfig["apiUser"]["apiKey"] = newConfig["controllerApiKey"] or None
            elif myConfig["apiType"] == 'omada':
                myConfig["apiUser"]["userName"] = newConfig["controllerUsername"] or None
                myConfig["apiUser"]["passWord"] = newConfig["controllePassword"] or None
            else:
                log.error(f'API Type Unknown: {newConfig["api_type"]}')
            myConfig["controllerIp"]=newConfig["controllerIp"]
            updateConfig(myConfig)
            log.info(f"New Config Saved")
            log.debug(f"New Config Saved {newConfig}")  
            return {"message":"Success", "details": "Configuration Saved"}
        else:
            log.error("Unauthorized Config Creation Attempt")
            return {"message": "Unauthorized"}, 401
    except Exception as e:
        log.error(e)
        return {"message": "Error","details":f"{e}"}, 500