from utilities.genPW import genPW
from utilities.genQR import genQRCode
import datetime


now=datetime.datetime.now()
pw = genPW()
genQRCode(pw)
### Added API Call code here for changing the password
with open("/app/app/cron.log","a") as file:
    file.write(f"{now}|PW: {pw} | QRCode created ")
