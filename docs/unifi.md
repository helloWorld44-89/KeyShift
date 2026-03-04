# UniFi API Integration

Module: `app/api/unifi.py`

KeyShift uses the **UniFi Network Integration API** (v1) to read and update Wi-Fi broadcast configurations. Authentication is via an **API key** passed in the `X-API-KEY` header.

!!! note "SSL"
    SSL verification is disabled (`verify=False`) to support controllers with self-signed certificates. Consider providing a CA bundle in production.

---

## Class: `UNIFI`

### `UNIFI.getSiteIDs() → list[str]`

Fetches all site IDs from the controller.

**Endpoint:** `GET /proxy/network/integration/v1/sites`

---

### `UNIFI.getWifiID(siteList) → list[str]`

Fetches all Wi-Fi broadcast IDs across the provided sites.

**Endpoint:** `GET /proxy/network/integration/v1/sites/{siteID}/wifi/broadcasts`

---

### `UNIFI.getSSIDInfo(siteIDs, wlans) → list[SSID]`

Fetches full SSID details (name, password, enabled status) for every combination of site and broadcast ID.

**Endpoint:** `GET /proxy/network/integration/v1/sites/{siteID}/wifi/broadcasts/{wlanID}`

---

### `UNIFI.initDBinfo() → bool`

Orchestrates a full SSID import:

1. `getSiteIDs()`
2. `getWifiID(siteIDs)`
3. `getSSIDInfo(siteIDs, wlans)`
4. Persists each new SSID to the database (skips duplicates by `ssidID`)

---

### `UNIFI.changePW(ssid, newPw) → bool | str`

Changes the password of a single SSID on the controller.

1. Fetches the current broadcast config via `GET`
2. Strips `id` and `metadata` fields
3. Updates `securityConfiguration.passphrase`
4. Sends updated config via `PUT`

Returns `True` on success, an error string on failure.
