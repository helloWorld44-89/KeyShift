# Docker Deployment

The recommended way to run KeyShift is with Docker Compose.

---

## Quick Start

### 1. Download and Extract KeyShift

Download the latest `keyshift.tar.xz` release and unzip it into a directory of your choice:

```bash
# Download the release zip
wget https://github.com/helloWorld44-89/KeyShift/raw/refs/heads/main/keyshift.tar.xz

# Unzip into a 'keyshift' directory
unzip keyshift.tar.xz -d keyshift

# Move into the project directory
cd keyshift
```

> **Note:** If you don't have `wget`, you can use `curl -L -o keyshift.tar.xz https://github.com/helloWorld44-89/KeyShift/raw/refs/heads/main/keyshift.tar.xz` instead, or download it manually from the releases page.

---

### 2. Configure Environment Variables

```bash
cp env.example .env
```

Open `.env` in a text editor and set your values:

```bash
# Minimum required — generate a secure key with:
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your-secure-secret-key-here

FLASK_ENV=production
FLASK_DEBUG=false
TZ=America/Chicago
```

---

### 3. Start the Container

```bash
docker compose up -d
```

KeyShift will be available at **http://localhost:5000**.

On first launch with no existing database, you will be redirected to `/initApp` to complete setup.

---

## docker-compose.yml Overview

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

| Volume | Purpose |
|---|---|
| `./data/db` | SQLite database (`KeyShift.db`) — persists across restarts |
| `./data/cron` | Cron job files for scheduled password rotation |
| `./data/config` | Controller config (`config.json`) — API credentials and Wi-Fi info |

All persistent data lives under `./data/` in your project directory, making backups straightforward.

---

## Persisting Data

KeyShift stores all runtime data in the mounted `./data/` directories. These are created automatically on first run. To back up your instance:

```bash
cp -r ./data ./data_backup
```

---

## Rebuilding After Updates

When a new version of KeyShift is released, download and unzip the new `keyshift.zip` over your existing directory, then rebuild:

```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

Your data in `./data/` will be preserved.

---

## Viewing Logs

```bash
docker compose logs -f
```

---

## Stopping KeyShift

```bash
docker compose down
```
