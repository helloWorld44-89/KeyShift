# Authentication Routes

Blueprint: `auth` — registered at `/`

---

## `GET/POST /login`

Renders the login page and processes login form submissions.

- Rate limited to **5 requests per minute** per IP via Flask-Limiter
- If no users exist in the database, redirects to `/initApp`
- On successful login, redirects to `/admin`
- On failure, flashes a generic "Incorrect Username or Password" message (intentionally avoids revealing whether the username exists)

**Form fields:** `username`, `password`

---

## `GET /logout`

Logs out the current user and redirects to `/login`.

Requires: `@login_required`
