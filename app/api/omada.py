import requests
# from app.config.config import getConfig
import logging 
import json
import pprint
from app.models import SSID as s

log = logging.getLogger("api.omada")
session = requests.Session()

url="https://192.168.5.233:8043/"
class OMADA:
    def login():
        username = "Root"
        password = "Baseball44!"
        payload = {
            "username": username,
            "password": password
        }
        headers = {
            'Content-Type': 'application/json'
        }
        requests.packages.urllib3.disable_warnings()
        response = session.post(f"{url}api/v2/login", json=payload, headers=headers,verify=False)
        if response.status_code == 200:
            log.info("Logged in to Omada Controller successfully")
            return response.json()
        else:
            log.error(f"Failed to log in to Omada Controller: {response.text}")
            return "failed"
        
    def getSites(token):
        omadacid = token["result"]["omadacId"]
        payload={
            'Content-Type': 'application/json',
            'CSRF-Token': token['result']['token']
        }
        response=session.get(f"{url}{omadacid}/api/v2/sites?currentPage=1&currentPageSize=1000",headers=payload,verify=False)
        siteList=[]
        for site in response.json().get("result", {}).get("data", []):
            siteList.append(site["id"])
        return siteList

    def getWlanGroups(token,siteID):
        omadacid = token["result"]["omadacId"]
        wlanList=[]
        for i in siteID:
            payload={
                'Content-Type': 'application/json',
                'CSRF-Token': token['result']['token']
            }
            print(f"{url}{omadacid}/api/v2/sites/{i}/setting/wlans")
            response=session.get(f"{url}{omadacid}/api/v2/sites/{i}/setting/wlans",headers=payload,verify=False)
            for x in response.json().get("result", {}).get("data", []):
                wlanList.append(x.get("id"))

        return wlanList

    def getSSIDs(token,siteIDs,wlans):
        requests.packages.urllib3.disable_warnings()
        omadacid = token["result"]["omadacId"]
        ssidList=[]
        for i in siteIDs:
            for j in wlans:
                
        # siteID="677b2c7c0750b87d47276c9c"
        # wlanGroup='677b2c7d0750b87d47276cb3'
                url = f"https://192.168.5.233:8043/{omadacid}/api/v2/sites/{i}/setting/wlans/{j}/ssids?currentPage=1&currentPageSize=10"
                headers = {
                    'Content-Type': 'application/json',
                    'CSRF-Token': token['result']['token']
                }
                
                response = session.get(url, headers=headers,verify=False)
                if response.status_code == 200:
                    for x in response.json().get("result", {}).get("data", []):
                        ssid_obj=s(x.get('name'), x.get('pskSetting',{}).get('securityKey'),x.get('site'), x.get('wlanId'),x.get('id'))
                        ssidList.append(ssid_obj)
                    print("Fetched SSIDs successfully")
                    return ssidList
                else:
                    return response.text
    
    def changePW(token,ssids):
        newPW="NewPassword44!"
        ssid = 'test'
        omadacid = token["result"]["omadacId"]
        siteID="677b2c7c0750b87d47276c9c"
        wlanId='677b2c7d0750b87d47276cb3'
        index =0
        newSSIDs=ssids['result']['data']
        #ssidID='697ff13ed94b2754b91fbc30'
        for i in newSSIDs:
            index+=1
            if i.get('name')==ssid:
                print("Found SSID")
                payload=i
                ssidID=i.get('id')
                break
        payload['pskSetting']['securityKey']=newPW
        print(ssidID)
        requests.packages.urllib3.disable_warnings()
        url = f"{url}/{omadacid}/api/v2/sites/{siteID}/setting/wlans/{wlanId}/ssids/{ssidID}"
        headers = {
            'Content-Type': 'application/json',
            'CSRF-Token': token['result']['token']
        }
        info = session.patch(url, headers=headers,json = payload,verify=False)
        ssidInfo=info.json()#.get("result",{})
        return ssidInfo

# token=login()
# #print(getWlanGroups(token))
# siteID=getSites(token)
# # print(siteID)
# wlanList=getWlanGroups(token,siteID)
# ssids=getSSIDs(token,siteID,wlanList)
# pprint.pprint(ssids)
# #print(changePW(token,ssids))