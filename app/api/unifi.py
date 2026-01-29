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