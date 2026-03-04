# Manual Installation

## Requirements

- Python 3.11+
- pip
- A system cron daemon (for password rotation)

---

## Steps

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set environment variables

```bash
cp env.example .env
# Edit .env — at minimum set SECRET_KEY
```

### 3. Initialise the database

```bash
flask db upgrade
```

### 4. Run the development server

```bash
python wsgi.py
```

### 5. Run with Gunicorn (production)

```bash
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:flask_app
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | **Required.** Flask secret key for sessions and CSRF |
| `FLASK_ENV` | `production` or `development` |
| `FLASK_DEBUG` | `true` / `false` |
| `TZ` | Timezone (e.g. `America/Chicago`) |

---

## Config File

After first-run setup, controller settings are stored in `app/config/file/config.json`:

```json
{
  "apiType": "unifi",
  "controllerIp": "192.168.1.1",
  "apiUser": {
    "apiKey": "your-unifi-api-key"
  },
  "wifiInfo": {
    "password": "current-wifi-password"
  }
}
```
