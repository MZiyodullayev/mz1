web: gunicorn config.wsgi --log-file - --chdir src

# NOTE: no "worker" or "release" line here on purpose.
# - Render Free instances don't support Background Workers or one-off
#   jobs (only Static Site / Web Service / Postgres / Key Value get
#   Free instances) — see https://render.com/docs/free
# - The worker (qcluster) runs locally instead, see README "Free setup".
# - Migrations run as part of the Build Command in the Render dashboard
#   instead of a release phase (also unsupported on Free).
