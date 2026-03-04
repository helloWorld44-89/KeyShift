# Database Models

KeyShift uses **SQLite** via Flask-SQLAlchemy. The database file is stored at `instance/KeyShift.db`.

---

## `user`

Represents an application user who can log in to the admin panel.

| Column | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Auto-increment primary key |
| `username` | Text | Unique login name |
| `password` | Text | Bcrypt-hashed password |
| `admin` | Boolean | `True` = admin role (can manage users) |
| `active` | Boolean | Account enabled/disabled |
| `apiKey` | Text | Per-user API token (URL-safe, 32 bytes) |

### Methods

#### `user.newUser(userName, pw, role=0)`
Creates a new user, hashes the password with bcrypt, generates an API key, and commits to the database.

```python
user.newUser("alice", "s3cr3t", role=1)  # role=1 → admin
```

---

## `SSID`

Represents a Wi-Fi network imported from the controller.

| Column | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Auto-increment primary key |
| `ssidName` | Text | Human-readable SSID name |
| `ssidPW` | Text | Current plaintext Wi-Fi password |
| `lastChanged` | DateTime | Timestamp of last password change |
| `siteID` | Text | Controller site ID |
| `wlanGroupID` | Text | WLAN group ID (Omada only) |
| `ssidID` | Text | Unique SSID ID on the controller |
| `status` | Boolean | SSID enabled/disabled |
| `hidden` | Boolean | Hidden SSID flag |
| `pwRotate` | Boolean | Password rotation enabled |
| `rotateFrequency` | Text | Cron expression for rotation schedule |
| `qrCode` | Boolean | QR code generation enabled |
| `isGuest` | Boolean | Marks this as the displayed guest SSID |

### Methods

#### `SSID.newSSID(...)`
Creates and persists a new SSID record.

#### `ssid.makeGuest()`
Designates this SSID as the guest network. Unsets any previously set guest SSID — only one may be active at a time.

#### `ssid.addRotation(rotateFrequency)`
Enables or disables password rotation. Pass `None` to disable.

#### `SSID.removeAllSSIDS()`
Deletes all SSID records (used before a controller rescan).
