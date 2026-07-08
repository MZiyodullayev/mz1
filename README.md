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

## Using it from your phone (same Wi-Fi)

The dev server only listens on `localhost` by default, which a phone can't
reach. To open it up on your local network:

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
