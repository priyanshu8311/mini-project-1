from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.api.dependencies import get_current_user
from backend.src.core.database import get_db_session
from backend.src.core.rate_limit import enforce_login_rate_limit
from backend.src.core.security import create_access_token
from backend.src.domain.users.models import User
from backend.src.domain.users.schemas import (
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from backend.src.domain.users.service import UserService

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


@auth_router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_login_rate_limit)],
    summary="Register a new organization and initialize its Admin account",
)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Register a new tenant organization and issue a signed JWT for the initial Admin."""
    _tenant, user = await UserService.register_organization(
        db=db,
        organization_name=payload.organization_name,
        email=payload.email,
        password=payload.password,
    )

    token_data = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role": user.role,
        "email": user.email,
    }
    access_token = create_access_token(data=token_data)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@auth_router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(enforce_login_rate_limit)],
    summary="Authenticate user and issue JWT access token",
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    """Authenticate user credentials and issue a signed JSON Web Token."""
    user = await UserService.authenticate_user(
        db=db,
        email=payload.email,
        password=payload.password,
    )

    token_data = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role": user.role,
        "email": user.email,
    }
    access_token = create_access_token(data=token_data)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@auth_router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Terminate authenticated session",
)
async def logout(
    _current_user: User = Depends(get_current_user),
) -> LogoutResponse:
    """Acknowledge authenticated session termination and prompt client-side token disposal."""
    return LogoutResponse(message="Logged out successfully.")
