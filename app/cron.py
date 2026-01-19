from utilities.genPW import genPW
from utilities.genQR import genQRCode
import datetime
from config import config
from api import unifi

myconfig= config.getConfig()
now=datetime.datetime.now()

pw = genPW()
genQRCode(pw)
### Added API Call code here for changing the password
print(unifi.changePW(pw)  )

with open("/app/app/cron.log","a") as file:
    file.write(f"{now}|PW: {pw} | QRCode created ")
