import requests
import json
from app.config import config
import logging
from app.models import SSID as s
from app import db

log = logging.getLogger("api.unifi")
myConfig= config.getConfig()
session=requests.Session()
class UNIFI:
    def changePW(ssid:s, newPw):
        try:
            gwIP = myConfig['controllerIp']
            apiKey=myConfig["apiUser"]["apiKey"]
            # Disable SSL warnings for self-signed certificates
            requests.packages.urllib3.disable_warnings()
            update_url = f"https://{gwIP}/proxy/network/integration/v1/sites/{ssid.siteID}/wifi/broadcasts/{ssid.ssidID}"
            headers= {
                'Accept': 'application/json',
                'X-API-KEY': f'{apiKey}'}
            response = session.get(update_url, headers=headers, verify=False)
            dict = response.json()
            del dict['id']
            del dict['metadata']
            dict['securityConfiguration']['passphrase'] = newPw
            headers= {
                'Content-Type': 'application/json',
                'X-API-KEY': f'{apiKey}'}
            newResponse = session.put(update_url, headers=headers, json=dict, verify=False)
            if newResponse.status_code == 200:
                log.info("Wi-Fi password changed successfully")
                log.debug(f"Wi-Fi PW Changed: {dict} ")
                return True
            else:
                log.info(f"Error: {newResponse.status_code} - {newResponse.text} ")
                log.debug(f"Error: {newResponse.status_code} - {newResponse.text}, info sent: {dict}")
                return f"Error: {newResponse.status_code} - {newResponse.text}"
        except Exception as e:
            log.info(f"Error: {e}")
            log.debug(f"Error: {e}, JSON{dict}, apiKey: {apiKey}")
            return f"An Error has occured: {e}"
        
    def getSiteIDs():
            try:
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
            except Exception as e:
                log.info(f"UNIFI get Sites Error: {e}")
                return f"An Error has occured: {e}"


    def getWifiID(siteList):
        try:
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
        except Exception as e:
            log.info(f"UNIFI get Wifi IDs Error: {e}")
            return f"An Error has occured: {e}"     

    def getSSIDInfo(siteIDs,wlans):
        try:
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
                        wifi=s(ssidName=response.json()['name'], ssidPW=response.json()['securityConfiguration']['passphrase'],
                            siteID=i,
                            wlanGroupID=None,
                            ssidID=j,
                            status=response.json()['enabled'])
                        ssidList.append(wifi)
            return ssidList
        except Exception as e:
            log.info(f"UNIFI get SSIDs Error: {e}")
            return f"An Error has occured: {e}"

    def initDBinfo():
        try:
            siteIDs=UNIFI.getSiteIDs()
            wlans=UNIFI.getWifiID(siteIDs)
            ssidList=UNIFI.getSSIDInfo(siteIDs,wlans)
            for ssid in ssidList:
                existingSSID=s.query.filter_by(ssidID=ssid.ssidID).first()
                if not existingSSID:
                    db.session.add(ssid)
                    log.info(f"Added SSID {ssid.ssidName} to DataBase")
                else:
                    log.info(f"SSID {ssid.ssidName} already exists in DataBase")
            db.session.commit()
            return ssidList
        except Exception as e:
            log.info(f"UNIFI initDBinfo Error: {e}")
            return f"An Error has occured: {e}"