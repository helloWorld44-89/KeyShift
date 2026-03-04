# KeyShift

> Self-hosted Wi-Fi password rotation and QR code management for UniFi and TP-Link Omada controllers.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-black?logo=flask&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Overview

KeyShift is a self-hosted web application that gives you full control over your Wi-Fi network passwords. Connect it to your UniFi or TP-Link Omada controller and KeyShift will automatically rotate passwords on a schedule, keep your local database in sync, and generate scannable QR codes so guests can connect instantly — no typing required.

---

## Features

- 🔑 **Automatic Password Rotation** — Schedule password changes via cron for any SSID
- 📱 **QR Code Generation** — Instant Wi-Fi QR codes for guest networks
- 🌐 **Dual Controller Support** — Works with both UniFi and TP-Link Omada
- 👤 **User Management** — Admin and standard roles with bcrypt-hashed passwords
- 🔒 **Security First** — CSRF protection, rate-limited login, session management
- 🐳 **Docker Ready** — Single-command deployment with Docker Compose

---

## Quick Start

### 1. Download and Extract

```bash
wget https://github.com/helloWorld44-89/KeyShift/raw/refs/heads/main/keyshift.tar.xz
mkdir keyshift && tar -xf keyshift.tar.xz -C keyshift
cd keyshift
```

### 2. Configure Environment

```bash
cp env.example .env
```

Edit `.env` and set your values:

```bash
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your-secure-secret-key-here

FLASK_ENV=production
FLASK_DEBUG=false
TZ=America/Chicago
```

### 3. Start with Docker Compose

```bash
docker compose up -d
```

KeyShift will be available at **http://localhost:5000**.

On first launch you will be redirected to the setup wizard to configure your controller and create your admin account.

---

## Docker Compose

```yaml
services:
  web:
    container_name: keyshift
    image: keyshift:latest
    ports:
      - "5000:5000"
    volumes:
      - ./data/db:/app/instance
      - ./data/cron:/etc/cron.d
      - ./data/config:/app/app/config/file
    env_file:
      - .env
```

All persistent data is stored in `./data/` and survives container restarts and upgrades.

---

## Documentation

Full documentation is available at the link below, including setup guides, route references, API integration details, and deployment instructions.

📖 **[View the KeyShift Docs](https://your-docs-url-here)**

| Section | Description |
|---|---|
| [Getting Started](docs/getting-started.md) | Download, configure, and run KeyShift |
| [Architecture](docs/architecture.md) | Project structure and request lifecycle |
| [API Integrations](docs/api/unifi.md) | UniFi and Omada controller integration |
| [Deployment](docs/deployment/docker.md) | Full Docker deployment reference |
| [Recommendations](docs/recommendations.md) | Suggested improvements and best practices |

---

## A Note on This Project

KeyShift was designed, architected, and built by me as a **self-taught, beginning developer**. Every feature — the Flask application structure, database models, controller API integrations, cron scheduling, user authentication, and Docker deployment — was written by hand as a real-world learning project.

**AI was used in a limited and specific capacity:**
- 📝 Generating inline code comments and documentation
- 🎨 Styling and layout assistance for the frontend UI

The core application logic, architecture decisions, and all backend code are my own work. This project represents the kind of thing I believe developers at any experience level can build by tackling real problems and learning along the way.

---

## Project Structure

```
app/
├── api/          # UniFi and Omada controller clients
├── config/       # JSON config management and cron scheduling
├── routes/       # Flask blueprints (auth, admin, ssid, setup)
├── utilities/    # Password generator and QR code generator
├── models.py     # SQLAlchemy database models
└── __init__.py   # Application factory
```

---

## License

This project is licensed under the MIT License. See `LICENSE` for details.
