# Admin Routes

Blueprint: `admin` — registered at `/`

All routes require `@login_required` unless noted.

---

## `GET/POST /admin`

Main admin dashboard. Accepts a `?tab=` query parameter to open a specific tab (default: `home`).

Renders `pages/admin.html` with all users, all SSIDs, current app config, and the active cron schedule for the guest SSID.

---

## `POST /log`

Accepts a JSON body `{ "message": "..." }` and writes it to the application log under the current user's name. Used by the frontend for client-side audit logging.

---

## `POST /updateConfig`

Updates the controller configuration (API type, credentials, controller IP) and writes back to `config.json`.

**Form fields:** `api_type`, `apiKey` (UniFi) or `username`/`password` (Omada), `controller_host`, `tab`

---

## `POST /manualCron/<id>`

Sets a custom cron schedule for the SSID with the given `id`.

**Form fields:** `schedule` (cron expression, e.g. `0 3 * * 1`)

---

## `POST /users/add`

Creates a new application user. Accessible during `init_mode` (first run) or when already authenticated.

**Form fields:** `newUsername`, `newPassword`, `newPasswordConfirm`, `newRole` (`admin` | `user`)

---

## `GET /makeguest/<id>`

Designates the SSID with the given `id` as the active guest network (only one allowed at a time).

---

## `GET /rescanSSIDs`

Deletes all locally stored SSIDs and re-imports them from the controller. Useful after adding or removing SSIDs on the controller.
