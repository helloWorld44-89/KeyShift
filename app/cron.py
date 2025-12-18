from utilities.genPW import genPW
from utilities.genQR import genQRCode
import datetime


now=datetime.datetime.now()
pw = genPW()
genQRCode(pw)

with open("/app/app/cron.log","a") as file:
    file.write(f"{now}|PW: {pw} | QRCode created ")
