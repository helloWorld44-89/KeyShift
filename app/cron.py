from utilities.genPW import genPW
from utilities.genQR import genQRCode
import datetime
from config import config
from api import unifi,omada
import logging

log=logging.getLogger("cron")

myconfig= config.getConfig()
now=datetime.datetime.now()
try:
     ## Generate a complex PW   
    pw = genPW() 
    ### API Call to change PW
    if myconfig["apiType"] == 'unifi':
        unifi.changePW(pw)
    elif myconfig["apitype"] == 'omada':
        omada.omadaPW(pw)
    else:
        raise Exception(f"An unknown Api Type was specififed: {myconfig["apiType"]}")
    ### Add new password to config file
    config.updatePW(pw)
    genQRCode(pw)
    log.info(f"PW: {pw}")
except Exception as e:
    log.info(f"Error: {e}")
