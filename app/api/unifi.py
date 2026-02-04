import requests
import json
from app.config import config
import logging
from app.models import SSID as s

log = logging.getLogger("api.unifi")
myConfig= config.getConfig()
session=requests.Session()
def changePW(pw):
    try:
        
        gwIP = myConfig['controllerIp']
        wifiId = myConfig['wifiInfo']['ID']
        siteID=myConfig["siteId"]
        apiKey=myConfig["apiUser"]["apiKey"]
        newPW =pw
        # Disable SSL warnings for self-signed certificates
        requests.packages.urllib3.disable_warnings()
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
    
def getSiteID():
    
        requests.packages.urllib3.disable_warnings()
        gwIP = myConfig['controllerIp']
        headers= {
            'Accept': 'application/json',
            'X-API-KEY': f'{myConfig["apiUser"]["apiKey"]}'}
        response=session.get(f"https://{gwIP}/proxy/network/integration/v1/sites",headers=headers, verify=False)
        siteList=[]
        for site in response.json().get("data", []):
            siteList.append(site["id"])

        return siteList

def getWifiID(siteList):
    requests.packages.urllib3.disable_warnings()
    gwIP = myConfig['controllerIp']
    headers= {
        'Accept': 'application/json',
        'X-API-KEY': f'{myConfig["apiUser"]["apiKey"]}'}
    wifiList=[]
    for i in siteList:
        response=session.get(f"https://{gwIP}/proxy/network/integration/v1/sites/{i}/wifi/broadcasts",headers=headers, verify=False)
        for x in response.json().get("data", []):
            wifiList.append(x.get("id"))    
    return wifiList

def getSSIDInfo(siteIDs,wlans):
    requests.packages.urllib3.disable_warnings()
    gwIP = myConfig['controllerIp']
    headers= {
        'Accept': 'application/json',
        'X-API-KEY': f'{myConfig["apiUser"]["apiKey"]}'}
    ssidList=[]
    for i in siteIDs:
        for j in wlans:
            response=session.get(f"https://{gwIP}/proxy/network/integration/v1/sites/{i}/wifi/broadcasts/{j}",headers=headers, verify=False)
            if response.status_code == 200:
                wifi=s(sidName=response.json()['name'], ssidPW=response.json()['securityConfiguration']['passphrase'],
                       siteID=i,
                       ssidID=j,
                       status=response.json()['enabled'])
                ssidList.append(wifi)
    return ssidList

siteList=getSiteID()
wifiList=getWifiID(siteList)
print(getSSIDInfo(siteList,wifiList))
