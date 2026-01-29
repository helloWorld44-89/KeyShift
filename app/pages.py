from flask import Blueprint, render_template, request, url_for, redirect,flash
from .models import user
from flask_bcrypt import bcrypt
from app.config.config import getConfig, updateConfig
from flask_login import  login_user, login_required, logout_user, current_user
import json
from app import db
from app.config.crontab import cronChange,getCrontab,manualCron
from crontab import CronTab
import logging 


log = logging.getLogger(__name__)
bp = Blueprint("pages", __name__)

@bp.route("/")
def guest():
    return render_template("pages/index.html")

@bp.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    users = user.query.all()
    cron = getCrontab()
    try:
        schedule=cron[0].slices.render()
    except Exception as e:
        schedule = '@daily'
    myConfig = getConfig()
    tab=request.args.get('tab','home')
    
    return render_template("pages/admin.html",users=users,config = myConfig,current_user=current_user,cron = cron,schedule=schedule,tab=tab)

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
    myConfig["siteId"] = newConfig["siteId"]
    myConfig["apiType"] = newConfig["api_type"]
    myConfig["wifiInfo"]["SSID"]=newConfig["SSID"]
    myConfig["wifiInfo"]["ID"]=newConfig["wifiId"]
    cronChange(newConfig['rotation_mode'])
    log.info(f"Config updated")
    log.debug(f"Config updated {newConfig}")
    
    return redirect(url_for('pages.admin', tab=newConfig["tab"]))

@bp.route("/manualCron",methods=["POST"])
@login_required
def manual():
    time =request.form["schedule"]
    manualCron(time)
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
