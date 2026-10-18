from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.api.dependencies import get_current_user, require_roles
from backend.src.core.database import get_db_session
from backend.src.domain.users.models import User, UserRole
from backend.src.domain.users.schemas import (
    UserCreate,
    UserListResponse,
    UserResponse,
    UserStatusUpdate,
)
from backend.src.domain.users.service import UserService

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


@users_router.get(
    "",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all users within the authenticated tenant (Admin only)",
)
async def list_users(
    current_admin: User = Depends(require_roles([UserRole.ADMIN.value])),
    db: AsyncSession = Depends(get_db_session),
) -> UserListResponse:
    """Retrieve all users registered under the administrator's tenant."""
    users = await UserService.list_users_by_tenant(
        db=db,
        tenant_id=current_admin.tenant_id,
    )
    return UserListResponse(
        data=[UserResponse.model_validate(u) for u in users],
        total=len(users),
    )


@users_router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user within the authenticated tenant (Admin only)",
)
async def create_user(
    payload: UserCreate,
    current_admin: User = Depends(require_roles([UserRole.ADMIN.value])),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Provision a new user account with assigned role in the administrator's tenant."""
    new_user = await UserService.create_user(
        db=db,
        tenant_id=current_admin.tenant_id,
        email=payload.email,
        password=payload.password,
        role=payload.role,
    )
    return UserResponse.model_validate(new_user)


@users_router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user details by ID within tenant (Admin only)",
)
async def get_user_by_id(
    user_id: UUID,
    current_admin: User = Depends(require_roles([UserRole.ADMIN.value])),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Fetch specific user details ensuring tenant isolation."""
    user = await UserService.get_user_by_id(
        db=db,
        user_id=user_id,
        tenant_id=current_admin.tenant_id,
    )
    return UserResponse.model_validate(user)


@users_router.patch(
    "/{user_id}/status",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user active status within tenant (Admin only)",
)
async def update_user_status(
    user_id: UUID,
    payload: UserStatusUpdate,
    current_admin: User = Depends(require_roles([UserRole.ADMIN.value])),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Activate or deactivate a user account within the administrator's tenant."""
    updated_user = await UserService.update_user_status(
        db=db,
        user_id=user_id,
        tenant_id=current_admin.tenant_id,
        is_active=payload.is_active,
        actor_user_id=current_admin.id,
    )
    return UserResponse.model_validate(updated_user)

