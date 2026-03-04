# Setup / Initialisation Routes

Blueprint: `setup` — registered at `/`

These routes are only accessible during the first-run setup flow (no users in the database).

---

## `GET/POST /initApp`

Renders the first-run setup wizard (`pages/initApp.html`). Sets `session['init_mode'] = True` to allow unauthenticated access to the user-creation and config endpoints during setup.

Returns `404` if users already exist.

---

## `GET /init`

Triggers the initial database population from the controller:

1. Reads `config.json` to determine the API type
2. Calls `UNIFI.initDBinfo()` or `OMADA.initDBinfo()` to import all SSIDs
3. Generates a QR code for each imported SSID

**Returns:** `{ "message": "Success", "details": "N SSIDs Initialized" }`

Requires: authenticated user **or** `session['init_mode']`

---

## `POST /newConfig`

Saves the initial controller configuration during the setup wizard. Only accessible when the request originates from `/initApp` and `init_mode` is active.

**Form fields:** `api_type`, `controllerIp`, `controllerApiKey` (UniFi) or `controllerUsername`/`controllePassword` (Omada)
