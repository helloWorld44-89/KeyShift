from flask import Blueprint, render_template, request, session, url_for, redirect
from flask_login import current_user
from app.models import user, SSID
from app.config.config import getConfig, updateConfig
from app.api.omada import OMADA
from app.api.unifi import UNIFI
from app.utilities.genQR import genQRCode
from app import db
import logging

bp = Blueprint("setup", __name__)
log = logging.getLogger(__name__)


@bp.route("/initApp", methods=["GET","POST"])
def initApp():
    users = user.query.all()
    if len(users)== 0:
        session['init_mode'] = True
        return render_template("pages/initApp.html")
    else:
        log.error(f"Init App Requested: User Count: {len(users)}")
        return {"error": "Not Found"}, 404

@bp.route("/init")
def initdb():
    try:
        if current_user.is_authenticated or session.get('init_mode'):
            config=getConfig()
            if config['apiType']=='unifi':
                info=UNIFI.initDBinfo()
            elif config['apiType']=='omada':
                info = OMADA.initDBinfo()
            else:
                log.error(f"APi Type Error: {config['apiType']}")
                return {"message":"Incorrect ApiType in config"}
            if info:
                ssids=db.session.query(SSID)
                x=0
                for i in ssids:
                    genQRCode(i)
                    x+=1
                return {"message": "Success", "details": f'{x} SSIDs Initialized'}
            else:
                log.error(f"initDb returned {info}")
                return {"message":"Failed", "details":"Initializing the Database failed. Please Try Again"}
        else:
            log.error("Unauthorized DB Initialization Attempt")
            return {"message": "Unauthorized"}, 401
    except Exception as e:
        log.error(e)
        return {"message": f"An Error has occured: {e}"}, 500

@bp.route("/newConfig", methods=['POST'])
def newConfig():
    try:
        if request.referrer.endswith("/initApp") and session.get('init_mode'):
            myConfig = getConfig()
            newConfig = request.form.to_dict()
            print(newConfig)
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