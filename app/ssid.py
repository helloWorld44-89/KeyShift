import logging
import sys
from app import create_app
with create_app().app_context():
    from app import db
    from app.api.omada import OMADA
    from app.api.unifi import UNIFI
    from app.models import SSID
    from app.config.config import getConfig
    from app.utilities.genPW import genPW
    from app.utilities.genQR import genQRCode

    log = logging.getLogger("CronPWChangeScript")
    myconfig=getConfig()
    args=sys.argv

    def changePW(ssidID:SSID,newPW):
        if myconfig['apiType']=='unifi':
            return UNIFI.changePW(ssidID, newPW)
        elif myconfig['apiType']=='omada':
            return OMADA.changePW(ssidID,newPW)
        else:
            return log.error(f"Unable to access {myconfig['apiType']}")

        


    try:
        log.info(f"Starting SSID PW Change with args: {args} /n")
        ssid = db.session.get(SSID,args[1])
        if ssid.pwRotate is not True:
            raise Exception(f"SSID:{ssid.ssidName} PW is not set to rotate. Aborting...")
        newPW = genPW()
        result = changePW(ssid,newPW)
        if result is True:
            ssid.ssidPW=newPW
            db.session.add(ssid)
            db.session.commit()
            db.session.refresh(ssid)
            if ssid.ssidPW==newPW:
                log.info("Password successfully changed in database.")
                log.debug(f"SSID PW Change Result: {result} | SSID Info: {ssid.ssidPW} | New PW: {newPW}")
            else:
                raise Exception("Password does not match database.")  
            
            genQRCode(ssid,newPW)
        else:
            raise Exception(f'changePW had an Error...')

    except Exception as e:
        log.error(f" {e}")
        log.debug(f" {e} | Args: {args}")

