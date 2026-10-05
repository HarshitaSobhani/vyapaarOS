from fastapi import APIRouter, Request
from sqlalchemy import func, select

from app.api.deps import DB, CurrentUser
from app.core.errors import AppError
from app.core.rate_limit import login_throttle
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas.misc import LoginIn, LoginOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

# Verified against a throwaway hash so unknown emails take similar time as wrong passwords.
_DUMMY_HASH = hash_password("not-a-real-password")


_INVALID = "Incorrect email or password"


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn, request: Request, db: DB) -> LoginOut:
    ip = request.client.host if request.client else "unknown"
    # Throttled attempts get the same generic error, even with the right password.
    if login_throttle.is_blocked(ip, body.email):
        raise AppError(_INVALID, 401, "invalid_credentials")
    user = db.scalar(select(User).where(func.lower(User.email) == body.email.strip().lower()))
    ok = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if user is None or not ok:
        login_throttle.record_failure(ip, body.email)
        raise AppError(_INVALID, 401, "invalid_credentials")
    login_throttle.record_success(ip, body.email)
    token = create_access_token(str(user.id))
    return LoginOut(user=UserOut.model_validate(user), access_token=token)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user
