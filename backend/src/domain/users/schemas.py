from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from backend.src.core.security import validate_password_strength
from backend.src.domain.users.models import UserRole


class LoginRequest(BaseModel):
    """Payload for user authentication."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Plaintext password")


class RegisterRequest(BaseModel):
    """Payload to register a new tenant organization and its initial administrator."""

    organization_name: str = Field(
        ..., min_length=2, max_length=255, description="Tenant organization name"
    )
    email: EmailStr = Field(..., description="Initial admin work email")
    password: str = Field(..., description="Strong administrative password")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        validate_password_strength(v)
        return v


class UserResponse(BaseModel):
    """User profile response schema."""

    id: UUID
    tenant_id: UUID
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """JWT authentication response payload."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TenantCreate(BaseModel):
    """Payload to create a new tenant organization."""

    name: str = Field(..., min_length=2, max_length=255)


class TenantResponse(BaseModel):
    """Tenant organization response schema."""

    id: UUID
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    """Payload for creating a new user within a tenant."""

    email: EmailStr
    password: str = Field(..., description="User password meeting complexity requirements")
    role: UserRole = UserRole.VIEWER

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        validate_password_strength(v)
        return v


class UserStatusUpdate(BaseModel):
    """Payload for activating or deactivating a user."""

    is_active: bool = Field(..., description="New active status")


class UserListResponse(BaseModel):
    """Paginated or listed collection of users within a tenant."""

    data: list[UserResponse]
    total: int


class LogoutResponse(BaseModel):
    """Acknowledgment payload for session logout."""

    message: str = "Logged out successfully"
