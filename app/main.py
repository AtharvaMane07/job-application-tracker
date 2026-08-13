from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
import app.models  # noqa: F401  (registers models on Base.metadata)

app = FastAPI(title="Job Application Tracker API", version="0.1.0")


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """
    Liveness + DB connectivity check.
    Returns 200 with db: "connected" only if a real query round-trips
    to Postgres — not just that the process is running.
    """
    db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}
