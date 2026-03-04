# Project Architecture

## Directory Structure

```
app/
├── __init__.py          # App factory (create_app), extension init, DB bootstrap
├── models.py            # SQLAlchemy models: user, SSID
├── pages.py             # Static page blueprint
├── cron.py              # Standalone cron script for scheduled password rotation
├── ssid.py              # Per-SSID cron entry point
├── logging_config.py    # Centralised logging configuration
├── wsgi.py              # WSGI entry point
│
├── api/
│   ├── unifi.py         # UniFi controller API client
│   └── omada.py         # TP-Link Omada controller API client
│
├── config/
│   ├── config.py        # JSON config read/write helpers
│   ├── crontab.py       # Cron job CRUD via python-crontab
│   └── file/
│       └── config.json  # Runtime config (controller IP, API credentials, Wi-Fi info)
│
├── routes/
│   ├── admin.py         # Admin dashboard, user management, SSID rescan
│   ├── auth.py          # Login / logout
│   ├── setup.py         # First-run initialisation wizard
│   └── ssid.py          # Password change, QR code, cron scheduling
│
├── utilities/
│   ├── genPW.py         # Cryptographically secure password generator
│   └── genQR.py         # Wi-Fi QR code image generator
│
├── static/              # CSS, JS, images (Bootstrap + custom)
└── templates/           # Jinja2 HTML templates
```

## Request Lifecycle

```
Browser → Gunicorn → Flask app (create_app)
                          ↓
                    Blueprint routing
                    ├── /login         → auth.bp
                    ├── /admin         → admin.bp
                    ├── /changepw/:id  → ssid.bp
                    ├── /initApp       → setup.bp
                    └── /             → pages.bp
                          ↓
                    SQLite (KeyShift.db via SQLAlchemy)
                    JSON config (app/config/file/config.json)
                    Controller API (UniFi / Omada)
```

## Extension Stack

| Extension | Purpose |
|---|---|
| Flask-SQLAlchemy | ORM & SQLite database |
| Flask-Migrate | Database schema migrations (Alembic) |
| Flask-Login | Session-based authentication |
| Flask-Limiter | Rate limiting (200/day, 20/hour default) |
| Flask-WTF | CSRF protection |
| Flask-Bcrypt | Password hashing |
