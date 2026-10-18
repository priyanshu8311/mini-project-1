from fastapi import APIRouter, Depends, status

from backend.src.api.dependencies import get_current_user, require_roles
from backend.src.domain.users.models import User, UserRole
from backend.src.domain.users.schemas import UserResponse

users_router = APIRouter(prefix="/users", tags=["Users"])


@users_router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Retrieve identity and role permissions for the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@users_router.get(
    "/admin-test",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="RBAC verification endpoint requiring Admin role",
)
async def admin_rbac_test(
    _admin_user: User = Depends(require_roles([UserRole.ADMIN.value])),
) -> dict:
    """Test endpoint accessible strictly by Admin role."""
    return {"message": "Admin authorization granted successfully."}
