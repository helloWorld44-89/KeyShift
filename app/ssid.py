import logging
import sys
from app import create_app
with create_app().app_context():
    from app import db
    from app.models import SSID
    from app.rotation import rotate

    log = logging.getLogger("CronPWChangeScript")
    args=sys.argv

    try:
        log.info(f"Starting SSID PW Change with args: {args} /n")
        ssid = db.session.get(SSID,args[1])
        if ssid.pwRotate is not True:
            raise Exception(f"SSID:{ssid.ssidName} PW is not set to rotate. Aborting...")
        rotate(ssid)
    except Exception as e:
        log.error(f" {e}")
        log.debug(f" {e} | Args: {args}")
