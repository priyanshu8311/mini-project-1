from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from backend.src.domain.users.models import UserRole


class LoginRequest(BaseModel):
    """Payload for user authentication."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Plaintext password")


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
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.VIEWER
