from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import DB, CurrentUser
from app.core.errors import AppError
from app.core.security import create_access_token, verify_password
from app.models import User
from app.schemas.misc import LoginIn, LoginOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

# Verified against a throwaway hash so unknown emails take similar time as wrong passwords.
_DUMMY_HASH = "$2b$12$C6UzMDM.H6dfI/f/IKcEeO5zkPQ0jQ6u2lE3mQ9cZ0gQK3wJ3dJ2e"


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn, db: DB) -> LoginOut:
    user = db.scalar(select(User).where(func.lower(User.email) == body.email.strip().lower()))
    ok = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if user is None or not ok:
        raise AppError("Incorrect email or password", 401, "invalid_credentials")
    token = create_access_token(str(user.id))
    return LoginOut(user=UserOut.model_validate(user), access_token=token)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user
