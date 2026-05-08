from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.domain.entities.enums import UserRole
from app.infrastructure.database.models import UserModel
from app.infrastructure.database.session import get_db
from app.infrastructure.security.tokens import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserModel:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
    except JWTError as exc:
        raise credentials_error from exc

    if not user_id:
        raise credentials_error

    user = db.get(UserModel, user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_admin(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user

