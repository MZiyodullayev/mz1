# mz1 — Screener

Django + DRF backend that watches a folder for screenshots, sends them to the
Groq API for analysis, stores the result, and broadcasts it to a Telegram
whitelist. Includes a JWT-protected REST API so a phone (or any other client)
can upload screenshots and read results too, not just the desktop watcher.

## Setup

```bash
python -m venv venv
source venv/Scripts/activate     # Windows Git Bash
# source venv/bin/activate       # Mac/Linux

pip install -r requirements.txt
cd src
cp .env.example .env             # fill in SECRET_KEY, GROQ_API_KEY, TELEGRAM_BOT_TOKEN, ...

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Running the folder watcher

```bash
python manage.py run_watcher --folder /path/to/watched/folder
# or set WATCH_FOLDER in .env and omit --folder
```

You also need a Django-Q worker running to process the queued analysis tasks:

```bash
python manage.py qcluster
```

## Deploying for free (Render + Neon + local worker)

Render's Free instance type only supports Web Service, Static Site, Postgres,
and Key Value — **not** Background Workers, and it doesn't run one-off jobs
(so migrations can't run as a separate release step). Render's free Postgres
also self-deletes after 30 days. To stay fully free, use this split instead:

- **Database**: [Neon](https://neon.tech) free Postgres — permanent, no
  expiry, no credit card. Create a project, copy its connection string.
- **Web (API)**: Render free Web Service — this is what your phone talks to.
- **Worker (`qcluster`)**: runs on your own computer, connected to the same
  Neon database. This is what actually processes screenshots and sends the
  Telegram message — **it only works while your computer is on and this is
  running.** If your PC is off, uploads just sit queued until you turn it
  back on and start the worker again.

### 1. Create the Neon database
Sign up at neon.tech, create a project, copy the connection string (looks
like `postgresql://user:password@ep-xxx.neon.tech/dbname?sslmode=require`).

### 2. Render Web Service
New Web Service → connect the `mz1` repo. **Leave Root Directory empty**
(repo root, not `src` — the `Procfile` already handles `cd`-ing into `src`).
- Build Command: `pip install -r requirements.txt && cd src && python manage.py migrate --noinput`
  (migrations run here, during build, since one-off jobs aren't available on Free)
- Start Command: leave blank — it uses the `web:` line in `Procfile`
- Environment variables: `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS=<your-app>.onrender.com`,
  `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `GROQ_API_KEY`, `TELEGRAM_BOT_TOKEN`,
  and `DATABASE_URL` = the Neon connection string from step 1.
- Instance type: Free.

### 3. Local worker
On your computer, in `src/.env`, set the **same** `DATABASE_URL` (the Neon
one, not sqlite), plus `GROQ_API_KEY` / `TELEGRAM_BOT_TOKEN`. Then, whenever
you want auto-answers to actually go out:
```bash
python manage.py qcluster
```
Optionally also run `python manage.py run_watcher` locally if you still want
the folder-watching flow in addition to the phone/API flow.

## Using it from your phone (same Wi-Fi) — local dev only

The section above (Render) is for when you're not on the same network. For
purely local development, the dev server only listens on `localhost` by
default, which a phone can't reach. To open it up on your local network:

1. Find your computer's LAN IP — `ipconfig` (Windows) or `ifconfig` / `ip a`
   (Mac/Linux). It looks like `192.168.x.x`.
2. Add that IP to `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, and
   `CSRF_TRUSTED_ORIGINS` in your `.env`.
3. Start the server bound to all interfaces:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
4. On your phone's browser or app, open `http://<your-computer-LAN-IP>:8000/`.

Both devices must be on the same Wi-Fi network. If you need access from
outside your home network (e.g. mobile data), put the server behind a
tunnel (ngrok, Cloudflare Tunnel) or deploy it to a real host, and use HTTPS.

## API

All endpoints below require a JWT, obtained via `/api/v1/token/`
(`username`/`password` → `access`/`refresh`), except where noted.

| Endpoint | Method | Auth | Notes |
|---|---|---|---|
| `/api/v1/token/` | POST | — | get access/refresh tokens |
| `/api/v1/token/refresh/` | POST | — | refresh an access token |
| `/api/v1/users/` | GET/POST/PATCH/DELETE | JWT | staff see everyone; others see only themselves |
| `/api/v1/screener/upload/` | POST | JWT | multipart `images[]`, queues analysis |
| `/api/v1/screener/screenshots/` | GET | JWT | list/detail with analysis result |
| `/api/v1/screener/whitelist/` | GET | JWT + staff | Telegram whitelist |

## Environment variables

See `src/.env.example` for the full list (`SECRET_KEY`, `DEBUG`,
`ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`,
`GROQ_API_KEY`, `TELEGRAM_BOT_TOKEN`, `WATCH_FOLDER`).
