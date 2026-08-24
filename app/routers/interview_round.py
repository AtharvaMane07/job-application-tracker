from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.application import Application
from app.models.interview_round import InterviewRound
from app.schemas.interview_round import (
    InterviewRoundCreate,
    InterviewRoundUpdate,
    InterviewRoundOut,
)

router = APIRouter(prefix="/applications/{application_id}/interview-rounds", tags=["interview-rounds"])


def _get_owned_application(application_id: int, db: Session, current_user: User) -> Application:
    app_obj = (
        db.query(Application)
        .filter(Application.id == application_id, Application.user_id == current_user.id)
        .first()
    )
    if app_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return app_obj


def _get_owned_round(
    application_id: int, round_id: int, db: Session, current_user: User
) -> InterviewRound:
    _get_owned_application(application_id, db, current_user)  # ownership check
    round_obj = (
        db.query(InterviewRound)
        .filter(InterviewRound.id == round_id, InterviewRound.application_id == application_id)
        .first()
    )
    if round_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview round not found")
    return round_obj


@router.post("", response_model=InterviewRoundOut, status_code=status.HTTP_201_CREATED)
def create_round(
    application_id: int,
    payload: InterviewRoundCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_application(application_id, db, current_user)
    round_obj = InterviewRound(application_id=application_id, **payload.model_dump())
    db.add(round_obj)
    db.commit()
    db.refresh(round_obj)
    return round_obj


@router.get("", response_model=list[InterviewRoundOut])
def list_rounds(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_application(application_id, db, current_user)
    return (
        db.query(InterviewRound)
        .filter(InterviewRound.application_id == application_id)
        .order_by(InterviewRound.scheduled_date.asc())
        .all()
    )


@router.get("/{round_id}", response_model=InterviewRoundOut)
def get_round(
    application_id: int,
    round_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _get_owned_round(application_id, round_id, db, current_user)


@router.patch("/{round_id}", response_model=InterviewRoundOut)
def update_round(
    application_id: int,
    round_id: int,
    payload: InterviewRoundUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    round_obj = _get_owned_round(application_id, round_id, db, current_user)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(round_obj, field, value)
    db.commit()
    db.refresh(round_obj)
    return round_obj


@router.delete("/{round_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_round(
    application_id: int,
    round_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    round_obj = _get_owned_round(application_id, round_id, db, current_user)
    db.delete(round_obj)
    db.commit()
    return None
