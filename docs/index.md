# KeyShift

**KeyShift** is a self-hosted Flask web application for managing Wi-Fi SSIDs and automatically rotating passwords on **UniFi** and **TP-Link Omada** network controllers. It generates scannable QR codes for each SSID so guests can connect without ever typing a password.

---

## Key Features

| Feature | Description |
|---|---|
| 🔑 **Password Rotation** | Automatically rotate Wi-Fi passwords on a configurable cron schedule |
| 📱 **QR Code Generation** | Generate and display Wi-Fi QR codes for easy guest access |
| 🌐 **Dual Controller Support** | Works with both UniFi and TP-Link Omada controllers |
| 👤 **User Management** | Admin and standard user roles with bcrypt-hashed passwords |
| 🐳 **Docker Ready** | Ships with a `Dockerfile` and `docker-compose.yml` |
| 🔒 **Rate Limiting & CSRF** | Built-in login rate limiting and CSRF protection |

---

## Quick Links

- [Getting Started](getting-started.md)
- [Docker Deployment](docker.md)
- [Configuration](installation.md)

