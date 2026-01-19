import requests
import json
from config import config

def changePW(pw):
    myConfig= config.getConfig()
    gwIP = myConfig['controllerIp']
    wifiId = myConfig['wifiInfo']['ID']
    newPW =pw

    # Disable SSL warnings for self-signed certificates
    requests.packages.urllib3.disable_warnings()

    session = requests.Session()

  
   
    update_url = f"https://{gwIP}/proxy/network/integration/v1/sites/88f7af54-98f8-306a-a1c7-c9349722b1f6/wifi/broadcasts/{wifiId}"
    headers= {
        'Accept': 'application/json',
        'X-API-KEY': 'JbcZXUU-WrNj2XTUBF3mAqNJR2vaF6gl'}
    response = session.get(update_url, headers=headers, verify=False)
    dict = response.json()
    del dict['id']
    del dict['metadata']
    dict['securityConfiguration']['passphrase'] = newPW
    headers= {
        'Content-Type': 'application/json',
        'X-API-KEY': 'JbcZXUU-WrNj2XTUBF3mAqNJR2vaF6gl'}

    newResponse = session.put(update_url, headers=headers, json=dict, verify=False)


    if newResponse.status_code == 200:
        print("Success: Wi-Fi password updated.")
        return "Success: Wi-Fi password updated."
    else:
        print(f"Error: {newResponse.status_code} - {newResponse.text} ")
        return f"Error: {newResponse.status_code} - {newResponse.text}"
