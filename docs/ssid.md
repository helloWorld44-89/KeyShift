# SSID Routes

Blueprint: `ssid` — registered at `/`

All routes require `@login_required`.

---

## `GET /changepw/<id>`

Changes the Wi-Fi password for the SSID with the given `id`.

| Query Param | Value | Behaviour |
|---|---|---|
| `pw` | `auto` (default) | Generates a new secure 40-character password |
| `pw` | any string | Uses the provided string as the new password |

On success, updates the password in both the controller and the local database, then redirects to `/admin`.

---

## `GET /qr/<id>`

Returns the QR code image (PNG) for the given SSID. The image must already exist at `app/static/img/<ssidName>.png`.

Returns `404` if the image file is not found.

---

## `GET /createCron/<id>`

Creates, updates, or deletes the password-rotation cron job for the given SSID.

| Query Param | Value | Behaviour |
|---|---|---|
| `rotateFrequency` | `None` | Deletes the existing cron job and disables rotation |
| `rotateFrequency` | cron expression | Creates or updates the cron job |

---

## `GET /network/qr/<id>`

Renders a guest-facing page (`pages/index.html`) showing the QR code for the given SSID. Intended to be displayed on a screen in a lobby or common area.
