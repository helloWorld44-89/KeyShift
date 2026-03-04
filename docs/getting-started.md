# Getting Started

## Prerequisites

- Python 3.11+
- A UniFi or TP-Link Omada controller reachable over the network
- Docker & Docker Compose (recommended) **or** a Python virtual environment

---

## 1. Install the App

- [Docker reference](docker.md)
- [Manual installation](installation.md)



The app will be available at `http://localhost:5000`. (unless you change the port in the docker compose or wsgi.py file)

## 2. First-Time Setup

On first launch with no users in the database, KeyShift redirects to `/initApp`:

1. Enter your controller's IP address and API credentials
2. Create the initial admin user
3. KeyShift will scan the controller and import all SSIDs automatically

---

## Next Steps


- [Admin panel & SSID management](admin.md)
