# Job Application Tracker API

A backend service for tracking job applications, interview rounds, and status
changes, with a full audit trail of how each application's status evolved
over time.

## Tech stack

- **Language/framework:** Python, FastAPI
- **Database:** PostgreSQL
- **ORM/migrations:** SQLAlchemy + Alembic
- **Auth:** JWT (access + refresh tokens)
- **Caching:** Redis
- **Testing:** pytest
- **Containerization:** Docker + docker-compose

## Data model

- **User** — id, email, hashed_password, created_at
- **Application** — id, user_id (FK), company, role, status, applied_date, notes
- **InterviewRound** — id, application_id (FK), round_type, scheduled_date, outcome
- **StatusHistory** — id, application_id (FK), old_status, new_status, changed_at

`status` on `Application` is a Postgres enum
(`applied` / `screening` / `interview` / `offer` / `rejected`), not a free
string — invalid values are rejected at the database layer, not just by
application code.

`StatusHistory` exists as its own table rather than just overwriting
`Application.status` in place: every status transition writes a row here,
so the full history of an application is queryable and auditable instead of
being lost on each update.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
docker compose up -d

alembic upgrade head

uvicorn app.main:app --reload
```

API docs (Swagger): `http://localhost:8000/docs`

Health check: `http://localhost:8000/health` → `{"status": "ok", "db": "connected"}`

## Architecture notes

- `user_id` on `Application` is a plain integer column rather than a foreign
  key. The FK constraint is added once the `User` table and auth are in
  place, via its own migration.
- Alembic's `env.py` reads the database URL from application settings
  (`app/config.py`, sourced from `.env`) rather than from a hardcoded value
  in `alembic.ini`, so no credentials are committed to the repo.
- Redis caches one read-heavy endpoint (application-count-by-status
  dashboard summary) rather than being used broadly, to keep cache
  invalidation reasoning simple and explainable.
