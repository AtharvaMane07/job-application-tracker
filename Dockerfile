FROM python:3.12-slim

WORKDIR /app

# psycopg2-binary has no build-time system deps, so no gcc/libpq-dev needed here
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway (and most PaaS providers) injects PORT at runtime; default 8000
# covers plain `docker run` locally. Migrations run on every container
# start — alembic upgrade head is idempotent, so restarts never re-apply
# already-applied migrations.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
