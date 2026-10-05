from collections.abc import Callable
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core import clock
from app.core.db import get_db
from app.core.errors import AppError
from app.core.security import decode_access_token
from app.models import User, UserRole
from app.services.ai.service import AIService, build_ai_service

DB = Annotated[Session, Depends(get_db)]


def get_today() -> date:
    return clock.today()


Today = Annotated[date, Depends(get_today)]


def get_ai_service() -> AIService:
    return build_ai_service()


AI = Annotated[AIService, Depends(get_ai_service)]


def get_current_user(
    db: DB,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    token = authorization[7:] if authorization and authorization.lower().startswith("bearer ") else None
    sub = decode_access_token(token) if token else None
    user = None
    if sub:
        try:
            user = db.get(User, UUID(sub))
        except ValueError:
            user = None
    if user is None:
        raise AppError("Please sign in to continue", 401, "unauthorized")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise AppError("You do not have permission to do this", 403, "forbidden")
        return user
    return checker


Approver = Annotated[User, Depends(require_roles(UserRole.owner, UserRole.manager))]
