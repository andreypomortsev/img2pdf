"""Dependencies for API endpoints."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError

from app import crud
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)


def get_current_user(
    db_gen=Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    """
    Get the current user from the token.

    Args:
        db_gen: Database session or generator
        token: JWT token

    Returns:
        User: The current user

    Raises:
        HTTPException: If the token is invalid or the user doesn't exist
    """
    # Handle both direct session and generator cases
    is_generator = not hasattr(db_gen, "execute")
    db = next(db_gen) if is_generator else db_gen

    try:
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            token_data = {"sub": payload.get("sub")}
        except (jwt.JWTError, ValidationError):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials",
            )

        # Look up user by email (which is the token's subject)
        user = crud.user.get_by_email(db, email=token_data["sub"])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    finally:
        # Only close the session if we're using a generator
        if is_generator and hasattr(db, "close"):
            db.close()


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current active user.

    Args:
        current_user: The current user

    Returns:
        User: The current active user

    Raises:
        HTTPException: If the user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current active superuser.

    Args:
        current_user: The current user

    Returns:
        User: The current active superuser

    Raises:
        HTTPException: If the user is not a superuser
    """
    if not crud.user.is_superuser(current_user):
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return current_user
