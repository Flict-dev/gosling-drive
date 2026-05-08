from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserRead
from app.application.services.audit import write_audit
from app.infrastructure.database.models import UserModel
from app.infrastructure.database.session import get_db
from app.infrastructure.security.passwords import hash_password, verify_password
from app.infrastructure.security.tokens import create_access_token
from app.presentation.api.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserModel:
    user = UserModel(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.flush()
        write_audit(
            db,
            user_id=user.id,
            action="register",
            resource_type="user",
            resource_id=user.id,
            metadata={"email": user.email},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        ) from exc
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(UserModel).where(UserModel.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled")

    write_audit(db, user_id=user.id, action="login", resource_type="user", resource_id=user.id)
    db.commit()
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserRead)
def me(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    return current_user
