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


def get_omada_ssid_summaries():
    
    config=getConfig()

    controllerIp = f"https://{config["controllerIp"]}:8043"
    username = f"{config["apiUser"]["userName"]}"
    password = f"{config["apiUser"]["passWord"]}"
    site = f"{config["siteId"]}"          # siteKey
    wlanId = f"{config["wifiInfo"]["wlanId"]}"    # wlanId
    wifiId = f"{config["wifiInfo"]["ID"]}"    # ssidId


    verify_ssl: bool = False,
    timeout: int = 30
    s = requests.Session()
    s.verify = verify_ssl
    s.headers.update({"Accept": "application/json", "Content-Type": "application/json"})

    # ----- 1. GET Controller ID  (/api/info) -----
    r = s.get(f"{controllerIp}/api/info", timeout=timeout)
    r.raise_for_status()
    controller_id = r.json()["result"]["omadacId"]  

    # ----- 2. Login to Web API (/api/v2/login) -----
    r = s.post(
        f"{controllerIp}/{controller_id}/api/v2/login",
        json={"username": username, "password": password},
        timeout=timeout
    )
    r.raise_for_status()
    token = r.json()["result"]["token"]             
    s.headers.update({"Csrf-Token": token})

    # ----- 3. Get WLAN + SSID Definitions -----
    wlan_url = f"{controllerIp}/{controller_id}/api/v2/sites/{site}/setting/wlans"
    r = s.get(wlan_url, timeout=timeout)
    r.raise_for_status()
    root = r.json().get("result", {})
    wlan_groups = root.get("data", root.get("wlans", [])) 

    ssids = []
    for wlan in wlan_groups:
        for ssid in wlan.get("ssids", []):
            name = ssid.get("name") or ssid.get("ssidName")
            enabled = bool(ssid.get("enable", ssid.get("enabled", True)))
            ssids.append({"name": name, "enabled": enabled})

    # ----- 4. Get Active Clients -----
    all_clients = []
    page = 1
    page_size = 1000
    while True:
        r = s.get(
            f"{controllerIp}/{controller_id}/api/v2/sites/{site}/clients",
            params={
                "filters.active": "true",
                "currentPage": page,
                "currentPageSize": page_size
            },
            timeout=timeout
        )
        r.raise_for_status()
        payload = r.json().get("result", {})
        batch = payload.get("data", [])
        all_clients.extend(batch)
        total = payload.get("totalRows") or len(batch)
        if len(batch) < page_size or len(all_clients) >= total:
            break
        page += 1

    counts = {}
    for c in all_clients:
        ssid = c.get("ssidName") or c.get("ssid") or c.get("essid")
        if ssid:
            counts[ssid] = counts.get(ssid, 0) + 1

    # ----- 5. Build Return Tuples-
    summaries = []
    for ssid in ssids:
        summaries.append(
            
                ssid["name"],
                "Enabled" if ssid["enabled"] else "Disabled",
                counts.get(ssid["name"], 0)
            
        )
    return summaries
