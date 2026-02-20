from flask import Blueprint, render_template, request, url_for, redirect, session
from flask_login import login_required, current_user
from app.models import user, SSID
from app.config.config import getConfig, updateConfig
from app.config.crontab import getCrontab, manualCron
from app import db
import logging

bp = Blueprint("admin", __name__)
log = logging.getLogger(__name__)


@bp.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    users = user.query.all()
    if len(users) == 0:
        return redirect(url_for("setup.initApp"))
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
    
    return redirect(url_for('admin.admin', tab=newConfig["tab"]))

@bp.route("/manualCron/<int:id>",methods=["POST"])
@login_required
def manual(id):
    time =request.form["schedule"]
    name = SSID.query.get(id).ssidName
    manualCron(time, name)
    log.info(f"Custom Cron schedule updated: {time}")
    return redirect(request.referrer)


@bp.route("/users/add",methods=['POST'])
def addNewUser():
    try:
        if current_user.is_authenticated or session.get('init_mode'):
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
                    return redirect(url_for("admin.admin",tab="security"))
                else:
                    log.error("Password Validation Failed for New User Creation")
                    return redirect(url_for("admin.admin",tab="security",))
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

@bp.route("/makeguest/<int:id>")
@login_required
def guestSwap(id):
    ssid=SSID.query.get(id)
    ssid.makeGuest()
    return redirect(request.referrer)
