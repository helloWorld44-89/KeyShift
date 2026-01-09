import requests
import json
from app.config.config import getConfig

def changePW(pw):
    config= getConfig()
    gwIP = config.controllerIp
    userName = config.apiUser.userName
    passWord = config.apiUser.passWord
    wifiId = config.wifiInfo.ID 
    newPW = pw

    # Disable SSL warnings for self-signed certificates
    requests.packages.urllib3.disable_warnings()

    session = requests.Session()

    # 1. Login to UniFi OS
    # Note: UDM Pro uses /api/auth/login for the main OS login
    login_url = f"https://{gwIP}/api/auth/login"
    login_payload = {"username": userName, "password": passWord}
    session.post(login_url, json=login_payload, verify=False)

    # 2. Update the Wi-Fi Password
    # The network API on UDM Pro is proxied via /proxy/network/
    update_url = f"https://{gwIP}/proxy/network/api/s/default/rest/wlanconf/{wifiId}"
    update_payload = {"x_password": newPW}

    response = session.put(update_url, json=update_payload, verify=False)

    if response.status_code == 200:
        return "Success: Wi-Fi password updated."
    else:
        return f"Error: {response.status_code} - {response.text}"
