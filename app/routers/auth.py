from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    UserOut,
    TokenPair,
    RefreshRequest,
    AccessTokenOut,
)
from app.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    hash_token,
    decode_token,
    JWTError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_token_pair(user_id: int, db: Session) -> TokenPair:
    access_token = create_access_token(subject=str(user_id))
    raw_refresh, expires_at = create_refresh_token(subject=str(user_id))

    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=hash_token(raw_refresh),
            expires_at=expires_at,
        )
    )
    db.commit()

    return TokenPair(access_token=access_token, refresh_token=raw_refresh)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenPair)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        # deliberately identical error for "no such user" and "wrong password" —
        # distinguishing them lets an attacker enumerate valid emails
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    return _issue_token_pair(user.id, db)


@router.post("/refresh", response_model=AccessTokenOut)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
    )

    try:
        decoded = decode_token(payload.refresh_token)
    except JWTError:
        raise invalid

    if decoded.get("type") != "refresh":
        raise invalid

    token_row = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == hash_token(payload.refresh_token))
        .first()
    )
    if token_row is None or token_row.revoked:
        raise invalid

    if token_row.expires_at < datetime.now(timezone.utc):
        raise invalid

    access_token = create_access_token(subject=str(token_row.user_id))
    return AccessTokenOut(access_token=access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    """Revokes the given refresh token so it can no longer be used to mint access tokens."""
    token_row = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == hash_token(payload.refresh_token))
        .first()
    )
    if token_row is not None:
        token_row.revoked = True
        db.commit()
    # 204 regardless of whether the token existed — don't leak that info either
    return None
