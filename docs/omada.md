# Omada API Integration

Module: `app/api/omada.py`

KeyShift supports **TP-Link Omada** controllers via the Omada REST API v2. Authentication uses username/password login to obtain a session token and `omadacId`.

!!! note "SSL"
    SSL verification is disabled (`verify=False`) for self-signed certificates.

---

## Class: `OMADA`

### `OMADA.login() → dict`

Authenticates with the Omada controller and returns the session token response (contains `omadacId` and `CSRF-Token`).

**Endpoint:** `POST /api/v2/login`

---

### `OMADA.getSites(token) → list[str]`

Returns a list of site IDs.

**Endpoint:** `GET /{omadacId}/api/v2/sites`

---

### `OMADA.getWlanGroups(token, siteID) → list[str]`

Returns WLAN group IDs for each site.

**Endpoint:** `GET /{omadacId}/api/v2/sites/{siteID}/setting/wlans`

---

### `OMADA.getSSIDs(token, siteIDs, wlans) → list[SSID]`

Fetches SSID details (name, PSK password, site, WLAN group, SSID ID) for all sites and WLAN groups.

**Endpoint:** `GET /{omadacId}/api/v2/sites/{siteID}/setting/wlans/{wlanID}/ssids`

---

### `OMADA.changePW(ssid, newPW) → bool | str`

Changes the password for a single SSID:

1. Logs in to obtain a fresh token
2. Fetches the current SSID payload
3. Updates `pskSetting.securityKey`
4. Sends the updated payload via `PATCH`

**Endpoint:** `PATCH /{omadacId}/api/v2/sites/{siteID}/setting/wlans/{wlanGroupID}/ssids/{ssidID}`

---

### `OMADA.initDBinfo() → bool`

Full SSID import: login → get sites → get WLAN groups → get SSIDs → persist to DB.
