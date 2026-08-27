from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.application import Application, ApplicationStatus
from app.models.status_history import StatusHistory
from app.schemas.application import ApplicationCreate, ApplicationUpdate, ApplicationOut
from app.schemas.status_history import StatusHistoryOut
from app.schemas.dashboard import DashboardSummary
from app.cache import (
    dashboard_cache_key,
    get_cached_json,
    set_cached_json,
    invalidate_dashboard_cache,
    DASHBOARD_CACHE_TTL_SECONDS,
)

router = APIRouter(prefix="/applications", tags=["applications"])


def _get_owned_application(
    application_id: int, db: Session, current_user: User
) -> Application:
    """
    Fetches an application by id, scoped to the current user.
    Returns 404 (not 403) when it belongs to someone else — this avoids
    confirming to a caller that an application id exists at all if it's
    not theirs.
    """
    app_obj = (
        db.query(Application)
        .filter(Application.id == application_id, Application.user_id == current_user.id)
        .first()
    )
    if app_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return app_obj


@router.get("/dashboard/summary", response_model=DashboardSummary)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Read-heavy endpoint: count of the caller's applications grouped by status.
    Cached in Redis per-user, invalidated immediately on any Application
    create/update/delete for that user, with a short TTL as a self-healing
    backstop in case an invalidation call is ever missed.
    """
    cache_key = dashboard_cache_key(current_user.id)
    cached = get_cached_json(cache_key)
    if cached is not None:
        return cached

    rows = (
        db.query(Application.status, func.count(Application.id))
        .filter(Application.user_id == current_user.id)
        .group_by(Application.status)
        .all()
    )
    counts_by_status = {status_value.value: count for status_value, count in rows}
    total = sum(counts_by_status.values())

    result = {"counts_by_status": counts_by_status, "total": total}
    set_cached_json(cache_key, result, DASHBOARD_CACHE_TTL_SECONDS)
    return result


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app_obj = Application(user_id=current_user.id, **payload.model_dump())
    db.add(app_obj)
    db.commit()
    db.refresh(app_obj)
    invalidate_dashboard_cache(current_user.id)
    return app_obj


@router.get("", response_model=list[ApplicationOut])
def list_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Application)
        .filter(Application.user_id == current_user.id)
        .order_by(Application.applied_date.desc())
        .all()
    )


@router.get("/{application_id}", response_model=ApplicationOut)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_owned_application(application_id, db, current_user)


@router.patch("/{application_id}", response_model=ApplicationOut)
def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app_obj = _get_owned_application(application_id, db, current_user)

    updates = payload.model_dump(exclude_unset=True)

    if "status" in updates and updates["status"] != app_obj.status:
        db.add(
            StatusHistory(
                application_id=app_obj.id,
                old_status=app_obj.status,
                new_status=updates["status"],
            )
        )

    for field, value in updates.items():
        setattr(app_obj, field, value)

    db.commit()
    db.refresh(app_obj)
    invalidate_dashboard_cache(current_user.id)
    return app_obj


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app_obj = _get_owned_application(application_id, db, current_user)
    db.delete(app_obj)
    db.commit()
    invalidate_dashboard_cache(current_user.id)
    return None


@router.get("/{application_id}/status-history", response_model=list[StatusHistoryOut])
def get_status_history(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Confirms the application belongs to the caller, then returns its full audit trail, oldest first."""
    _get_owned_application(application_id, db, current_user)  # ownership check, 404s if not theirs
    return (
        db.query(StatusHistory)
        .filter(StatusHistory.application_id == application_id)
        .order_by(StatusHistory.changed_at.asc())
        .all()
    )
