import requests
import json
from config import config
import logging

log = logging.getLogger("api.unifi")

def changePW(pw):
    try:
        myConfig= config.getConfig()
        gwIP = myConfig['controllerIp']
        wifiId = myConfig['wifiInfo']['ID']
        siteID=myConfig["siteId"]
        apiKey=myConfig["apiUser"]["apiKey"]
        newPW =pw
        # Disable SSL warnings for self-signed certificates
        requests.packages.urllib3.disable_warnings()
        session = requests.Session()
        update_url = f"https://{gwIP}/proxy/network/integration/v1/sites/{siteID}/wifi/broadcasts/{wifiId}"
        headers= {
            'Accept': 'application/json',
            'X-API-KEY': f'{apiKey}'}
        response = session.get(update_url, headers=headers, verify=False)
        dict = response.json()
        del dict['id']
        del dict['metadata']
        dict['securityConfiguration']['passphrase'] = newPW
        headers= {
            'Content-Type': 'application/json',
            'X-API-KEY': f'{apiKey}'}
        newResponse = session.put(update_url, headers=headers, json=dict, verify=False)
        if newResponse.status_code == 200:
            log.info(f"Wi-Fi password changed to {pw}")
            log.debug(f"Wi-Fi PW Changed: {dict} ")
            return "Success: Wi-Fi password updated."
        else:
            log.info(f"Error: {newResponse.status_code} - {newResponse.text} ")
            log.debug(f"Error: {newResponse.status_code} - {newResponse.text}")
            return f"Error: {newResponse.status_code} - {newResponse.text}"
    except Exception as e:
        log.info(f"Error: {e}")
        log.debug(f"Error: {e}, JSON{dict}, apiKey: {apiKey}")
        return f"An Error has occured: {e}"
    
    
def getUNIFIssids():

    myConfig= config.getConfig()
    gwIP = myConfig['controllerIp']
    wifiId = myConfig['wifiInfo']['ID']
    site=myConfig["siteId"]
    apiKey=myConfig["apiUser"]["apiKey"]

    base_url=f"https://{gwIP}"
    username=myConfig["apiUser"]["userName"]
    password=myConfig["apiUser"]["passWord"]
    verify_ssl: bool = False,
    timeout: int = 30


    s = requests.Session()
    s.verify = verify_ssl
    s.headers.update({"Accept": "application/json", "Content-Type": "application/json"})

    # ----- 1. Login to UniFi OS (/api/auth/login) -----
    r = s.post(
        f"{base_url}/api/auth/login",
        json={"username": username, "password": password},
        timeout=timeout
    )
    r.raise_for_status()

    # All network API calls go under `/proxy/network/...` for UniFi OS
    def api(path: str) -> str:
        return f"{base_url}/proxy/network{path}"

    # ----- 2. Get SSIDs from /rest/wlanconf -----
    r = s.get(api(f"/api/s/{site}/rest/wlanconf"), timeout=timeout)
    r.raise_for_status()
    wlanconfs = r.json().get("data", [])  

    ssids = [{"name": w.get("name"), "enabled": bool(w.get("enabled", True))}
             for w in wlanconfs]

    # ----- 3. Get Clients from /stat/sta -----
    r = s.get(api(f"/api/s/{site}/stat/sta"), timeout=timeout)
    r.raise_for_status()
    clients = r.json().get("data", [])
    counts = {}
    for c in clients:
        ssid = c.get("essid")
        if ssid:
            counts[ssid] = counts.get(ssid, 0) + 1

    # ----- 4. Build return objects -----
    summaries = []
    for ssid in ssids:
        summaries.append(
                ssid["name"],
                "Enabled" if ssid["enabled"] else "Disabled",
                counts.get(ssid["name"], 0),
        )
    return summaries
