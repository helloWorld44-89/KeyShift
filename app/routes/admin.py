from flask import Blueprint, render_template, request, url_for, redirect, session, abort, jsonify, current_app
from flask_login import login_required, current_user
from app.models import user, SSID
from app.config.config import getConfig, updateConfig
from app.config.crontab import getCrontab, manualCron
from app.utilities.genQR import genQRCode
from app.api import unifi,omada
from app.routes.auth import admin_required, setup_token_valid, clear_setup_token
from app import db
from app.logging_config import logFilePath
from app.settings import getPolicy, savePolicy
from app.utilities.passwordPolicy import (PasswordPolicy, validatePolicy, generate, entropyBits)
from app.utilities.logTail import readLog, LEVELS
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
    
    return render_template("pages/admin.html",users=users,config = myConfig,current_user=current_user,cron = cron,schedule=schedule,tab=tab,ssids=ssids,guest=guestSSID,policy=getPolicy())

@bp.route("/admin/logs")
@admin_required
def viewLogs():
    """Tail of the application log for the Advanced tab: ?lines=1-1000&level=ALL|DEBUG|INFO|WARNING|ERROR."""
    level = request.args.get("level", "ALL").upper()
    if level != "ALL" and level not in LEVELS:
        return {"message": "Unknown log level"}, 400
    try:
        count = max(1, min(int(request.args.get("lines", 200)), 1000))
    except ValueError:
        return {"message": "lines must be a number"}, 400
    response = jsonify({"entries": readLog(logFilePath(current_app), count, level)})
    response.headers["Cache-Control"] = "no-store"
    return response

def _policyFromForm(form) -> PasswordPolicy:
    """Read a PasswordPolicy from submitted form fields (checkboxes are present only when ticked)."""
    def number(name, default):
        try:
            return int(form.get(name, default))
        except (TypeError, ValueError):
            return default
    return PasswordPolicy(
        length=number("length", 40),
        upper="upper" in form, lower="lower" in form,
        digits="digits" in form, symbols="symbols" in form,
        minPerClass=number("minPerClass", 1),
        symbolSet=form.get("symbolSet", ""),
        excludeLookalikes="excludeLookalikes" in form,
        enforceManual="enforceManual" in form)


@bp.route("/admin/passwordPolicy", methods=["POST"])
@admin_required
def savePasswordPolicy():
    policy = _policyFromForm(request.form)
    problems = validatePolicy(policy)
    if problems:
        return {"message": " ".join(problems)}, 400
    savePolicy(policy)
    log.info(f"{current_user.username} updated the password policy")
    return redirect(url_for("admin.admin", tab="settings"))


@bp.route("/admin/passwordPolicy/preview", methods=["POST"])
@admin_required
def previewPasswordPolicy():
    """Sample password and strength for the (unsaved) form values. The sample is never stored."""
    policy = _policyFromForm(request.form)
    problems = validatePolicy(policy)
    if problems:
        return {"errors": problems}, 400
    response = jsonify({"sample": generate(policy), "bits": entropyBits(policy)})
    response.headers["Cache-Control"] = "no-store"
    return response

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
@admin_required
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
    
    return redirect(url_for('admin.admin', tab=newConfig["tab"]))

@bp.route("/manualCron/<int:id>",methods=["POST"])
@admin_required
def manual(id):
    time =request.form["schedule"]
    name = SSID.query.get(id).ssidName
    manualCron(time, name)
    log.info(f"Custom Cron schedule updated: {time}")
    return redirect(request.referrer)


@bp.route("/users/add",methods=['POST'])
def addNewUser():
    try:
        userName=request.form.get("newUsername")
        passWord=request.form.get("newPassword")

        # First-run: with no users yet, the visitor creates the initial admin.
        # Once any user exists this branch is closed for good.
        if user.query.count() == 0:
            if session.get('init_mode') is not True:
                log.error("Initial user creation attempted without visiting /initApp")
                return {"message": "Unauthorized"}, 401
            if not setup_token_valid(request.form.get("setupToken")):
                log.error("Initial user creation attempted with a wrong setup token")
                return {"message": "Invalid setup token"}, 403
            if not userName or not passWord:
                return {"message": "Username and password are required"}, 400
            user.newUser(userName, passWord, 1)
            first = user.query.filter_by(username=userName).first()
            if first is None:
                return {"message": "Could not create the initial user"}, 500
            clear_setup_token()
            session['init_user'] = first.id  # binds setup privileges to this session
            log.info(f"Initial User Created: {userName}")
            return {"message": "Success"}

        # Afterwards only a logged-in admin may add users.
        if not current_user.is_authenticated:
            log.error("Unauthorized User Creation Attempt")
            return {"message": "Unauthorized"}, 401
        if not current_user.admin:
            log.warning(f"{current_user.username} (non-admin) tried to create a user")
            abort(403)
        if request.form.get("newPasswordConfirm") != passWord:
            log.error("Password Validation Failed for New User Creation")
            return redirect(url_for("admin.admin",tab="security"))
        role = 1 if request.form.get("newRole") == 'admin' else 0
        user.newUser(userName,passWord,role)
        log.info(f"New User Created: {userName} by {current_user.username}")
        return redirect(url_for("admin.admin",tab="security"))
    except Exception as e:
        if hasattr(e, "code"):  # let abort() HTTP errors through
            raise
        log.error(f"Error creating user: {e}")
        return {"message": "An error has occured creating the user"}, 500

@bp.route("/makeguest/<int:id>", methods=["POST"])
@admin_required
def guestSwap(id):
    ssid=SSID.query.get(id)
    ssid.makeGuest()
    return redirect(request.referrer)

@bp.route("/rescanSSIDs", methods=["POST"])
@admin_required
def rescanSSIDs():
    try:
        log.info(f"User: {current_user.id} has requested to rescan for SSIDs")
        config= getConfig()
        if config["apiType"] == 'unifi':
            synced = unifi.UNIFI.initDBinfo()
        elif config['apiType'] =='omada':
            synced = omada.OMADA.initDBinfo()
        else:
            raise Exception(f'Wrong API Type: {config["apiType"]}')
        if not synced:
            return {"message": "Could not read SSIDs from the controller. See logs for details"}, 502
        for i in SSID.query.all():
            genQRCode(i)
        return redirect(request.referrer or url_for("admin.admin"))
    except Exception as e:
        log.error(f"Error rescanning SSIDs: {e}")
        return {"message": "An error has occured rescanning SSIDs"}, 500
