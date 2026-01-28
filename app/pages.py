from flask import Blueprint, render_template, request, url_for, redirect,flash
from .models import user
from flask_bcrypt import bcrypt
from app.config.config import getConfig, updateConfig
from flask_login import  login_user, login_required, logout_user, current_user
import json
from app.config.crontab import cronChange,getCrontab,manualCron
from crontab import CronTab


bp = Blueprint("pages", __name__)

@bp.route("/")
def guest():
    return render_template("pages/index.html")

@bp.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    cron = getCrontab()
    try:
        schedule=cron[0].slices.render()
    except Exception as e:
        schedule = '@daily'
    myConfig = getConfig()
    tab=request.args.get('tab','home')
    
    return render_template("pages/admin.html",config = myConfig,current_user=current_user,cron = cron,schedule=schedule,tab=tab)

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
                return redirect(url_for("pages.admin"))
            else:
                flash('Incorrect Username or Password', 'danger')
        else:
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
    #cronChange(newConfig['rotation_mode'])
    
    return redirect(url_for('pages.admin', tab=newConfig["tab"]))

@bp.route("/manualCron",methods=["POST"])
@login_required
def manual():
    time =request.form["schedule"]
    print(manualCron(time))
    return redirect(request.referrer)


