import requests
from app.config.config import getConfig
import logging 
import json
import pprint
from app.models import SSID as s
from app import db

log = logging.getLogger("api.omada")
session = requests.Session()
myconfig = getConfig()
baseUrl=f"https://{myconfig["controllerIp"]}:8043/"
class OMADA:
    def login():
        username = myconfig["apiUser"]["userName"]
        password = myconfig["apiUser"]["passWord"]
        payload = {
            "username": username,
            "password": password
        }
        headers = {
            'Content-Type': 'application/json'
        }
        requests.packages.urllib3.disable_warnings()
        response = session.post(f"{baseUrl}api/v2/login", json=payload, headers=headers,verify=False)
        if response.status_code == 200:
            log.info("Logged in to Omada Controller successfully")
            return response.json()
        else:
            log.error(f"Failed to log in to Omada Controller: {response.text}")
            return "failed"
        
    def getSites(token):
        try:
            omadacid = token["result"]["omadacId"]
            payload={
                'Content-Type': 'application/json',
                'CSRF-Token': token['result']['token']
            }
            response=session.get(f"{baseUrl}{omadacid}/api/v2/sites?currentPage=1&currentPageSize=1000",headers=payload,verify=False)
            print(response.text)
            siteList=[]
            for site in response.json().get("result", {}).get("data", []):
                siteList.append(site["id"])
            return siteList
        except Exception as e:
            log.info(f"OMADA get Sites Error: {e}, {token}")
            return f"An Error has occured: {e}"

    def getWlanGroups(token,siteID):
        try:
            omadacid = token["result"]["omadacId"]
            wlanList=[]
            for i in siteID:
                payload={
                    'Content-Type': 'application/json',
                    'CSRF-Token': token['result']['token']
                }
                response=session.get(f"{baseUrl}{omadacid}/api/v2/sites/{i}/setting/wlans",headers=payload,verify=False)
                for x in response.json().get("result", {}).get("data", []):
                    wlanList.append(x.get("id"))

            return wlanList
        except Exception as e:
            log.info(f"OMADA get Sites Error: {e}")
            return f"An Error has occured: {e}"

    def getSSIDs(token,siteIDs,wlans):
        try:
            requests.packages.urllib3.disable_warnings()
            omadacid = token["result"]["omadacId"]
            ssidList=[]
            for i in siteIDs:
                for j in wlans:
                    url = f"{baseUrl}{omadacid}/api/v2/sites/{i}/setting/wlans/{j}/ssids?currentPage=1&currentPageSize=10"
                    headers = {
                        'Content-Type': 'application/json',
                        'CSRF-Token': token['result']['token']
                    }
                    response = session.get(url, headers=headers,verify=False)
                    if response.status_code == 200:
                        for x in response.json().get("result", {}).get("data", []):
                            ssidObj=s(x.get('name'), x.get('pskSetting',{}).get('securityKey'),x.get('site'), x.get('wlanId'),x.get('id'))
                            ssidList.append(ssidObj)
                        print("Fetched SSIDs successfully")
                        return ssidList
                    else:
                        return response.text
        except Exception as e:
            log.info(f"OMADA get SSIDs Error: {e}")
            return f"An Error has occured: {e}"
    
    def changePW(ssid:s,newPW):
        try:
            requests.packages.urllib3.disable_warnings()
            token=OMADA.login()
            print(token)
            omadacid = token["result"]["omadacId"]
            url = f"{baseUrl}{omadacid}/api/v2/sites/{ssid.siteID}/setting/wlans/{ssid.wlanGroupID}/ssids?currentPage=1&currentPageSize=100"
            headers = {
                'Content-Type': 'application/json',
                'CSRF-Token': token['result']['token']
            }
            response = session.get(url, headers=headers,verify=False).json().get("result",{})       
            for i in response.get("data", []):
                if i.get("id") == ssid.ssidID:
                    payload=i
                    break
            if payload is None:
                log.info(f"SSID with ID {ssid.ssidID} not found.")
                return f"SSID with ID {ssid.ssidID} not found."
            payload['pskSetting']['securityKey']=newPW
            
            url = f"{baseUrl}{omadacid}/api/v2/sites/{ssid.siteID}/setting/wlans/{ssid.wlanGroupID}/ssids/{ssid.ssidID}"
            headers = {
                'Content-Type': 'application/json',
                'CSRF-Token': token['result']['token']
            }
            info = session.patch(url, headers=headers,json = payload,verify=False)
            if info.status_code == 200:
                log.info(f"Wi-Fi {ssid.ssidName} password changed to {newPW}")
                log.debug(f"Wi-Fi PW Changed: {payload} ")
            else:
                log.info(f"Error: {info.status_code} - {info.text} ")
                log.debug(f"Error: {info.status_code} - {info.text}, info sent: {payload}")
                return f"Error: {info.status_code} - {info.text}"
            return True
        except Exception as e:
            log.info(f"OMADA change PW Error: {e}")
            return f"An Error has occured: {e}"


    def initDBinfo() -> bool:
        try:
            token=OMADA.login()
            siteID=OMADA.getSites(token)
            wlanList=OMADA.getWlanGroups(token,siteID)
            ssids=OMADA.getSSIDs(token,siteID,wlanList)
            for i in ssids:
                db.session.add(i)
            db.session.commit()
            log.info(f"{ssids} added to DataBase")
            return True
        except Exception as e:
            log.info(f"omada initDb Error: {e}")
            return False

