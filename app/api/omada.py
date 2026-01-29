import requests
from app.config.config import getConfig
import logging 

log = logging.getLogger("api.omada")


def omadaPW(newPW):
    try:
        config=getConfig()
        controller = f"https://{config["controllerIp"]}:8043"
        userName = f"{config["apiUser"]["userName"]}"
        passWord = f"{config["apiUser"]["passWord"]}"
        siteId = f"{config["siteId"]}"          # siteKey
        wlanId = f"{config["wifiInfo"]["wlanId"]}"    # wlanId
        wifiId = f"{config["wifiInfo"]["ID"]}"    # ssidId
        newPW = newPW

        session = requests.Session()
        session.verify = False  # disable SSL verify if using self-signed certs

        # --- Step 1: Login ---
        login_payload = {
            "username": userName,
            "password": passWord
        }

        login = session.post(f"{controller}/api/v2/login", json=login_payload)
        login.raise_for_status()

        token = login.json()["result"]["token"]
        session.headers.update({"Csrf-Token": token})

        # --- Step 2: Build PATCH payload ---
        payload = {
            "security": {
                "key": newPW
            }
        }

        # --- Step 3: Send PATCH request to update SSID password ---
        url = f"{controller}/api/v2/sites/{siteId}/setting/wlans/{wlanId}/ssids/{wifiId}"

        resp = session.patch(url, json=payload)
        resp.raise_for_status()
        log.info(f"{wifiId} pw has been changed") 
        log.debug(f"Payload received: {payload}")
        return "SSID password updated successfully!"
    except Exception as e:
        log.info(f"Error: {e}")
        log.debug(f"Error: {e}, JSON{payload}, user: {userName}, pw: {passWord}")
        return f"An Error has occured: {e}"

