from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.core.database import get_db_session
from backend.src.core.rate_limit import enforce_login_rate_limit
from backend.src.core.security import create_access_token
from backend.src.domain.users.schemas import LoginRequest, TokenResponse, UserResponse
from backend.src.domain.users.service import UserService

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])


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
