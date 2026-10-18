from collections.abc import Callable
from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.core.config import settings
from backend.src.core.database import get_db_session
from backend.src.core.errors import ForbiddenException, UnauthorizedException
from backend.src.core.security import decode_access_token
from backend.src.domain.users.models import User
from backend.src.domain.users.service import UserService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False,
)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Dependency to extract and validate the JWT token and return the current user."""
    if not token:
        raise UnauthorizedException("Authentication token is missing.")

    payload = decode_access_token(token)
    user_id_str: str | None = payload.get("sub")
    tenant_id_str: str | None = payload.get("tenant_id")

    if not user_id_str or not tenant_id_str:
        raise UnauthorizedException("Token payload missing required identity claims.")

    try:
        user_id = UUID(user_id_str)
        tenant_id = UUID(tenant_id_str)
    except ValueError:
        raise UnauthorizedException("Malformed token claims.") from None

    try:
        user = await UserService.get_user_by_id(db, user_id=user_id, tenant_id=tenant_id)
    except Exception:
        raise UnauthorizedException("User associated with token no longer exists.") from None

    if not user.is_active:
        raise UnauthorizedException("User account is inactive.")

    return user


def require_roles(allowed_roles: list[str]) -> Callable[..., User]:
    """Factory dependency to enforce Role-Based Access Control (RBAC)."""

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            roles_str = ", ".join(allowed_roles)
            raise ForbiddenException(
                f"Role '{current_user.role}' is not authorized. Required: {roles_str}."
            )
        return current_user

    return role_checker


async def get_current_tenant_id(
    current_user: User = Depends(get_current_user),
) -> UUID:
    """Dependency returning the current user's authenticated tenant_id."""
    return current_user.tenant_id
