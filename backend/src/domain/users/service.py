from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.core.errors import (
    ConflictException,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)
from backend.src.core.security import hash_password, verify_password
from backend.src.domain.users.models import Tenant, User, UserRole


class UserService:
    """Service handling tenant and user identity management."""

    @staticmethod
    async def create_tenant(db: AsyncSession, name: str) -> Tenant:
        """Create a new tenant organization."""
        tenant = Tenant(name=name)
        db.add(tenant)
        await db.flush()
        await db.refresh(tenant)
        return tenant

    @staticmethod
    async def get_tenant_by_id(db: AsyncSession, tenant_id: UUID) -> Tenant:
        """Fetch tenant by primary key."""
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise NotFoundException("Tenant", tenant_id)
        return tenant

    @staticmethod
    async def register_organization(
        db: AsyncSession,
        organization_name: str,
        email: str,
        password: str,
    ) -> tuple[Tenant, User]:
        """Atomically register a new tenant organization and its initial administrator."""
        # Ensure email is not already registered across tenants to prevent credential collision
        existing = await UserService.get_user_by_email(db, email=email)
        if existing:
            raise ConflictException(
                f"An account with email '{email}' already exists. "
                "Please sign in or use another email."
            )

        tenant = Tenant(name=organization_name.strip())
        db.add(tenant)
        await db.flush()

        user = User(
            tenant_id=tenant.id,
            email=email.lower().strip(),
            password_hash=hash_password(password),
            role=UserRole.ADMIN.value,
            is_active=True,
        )
        db.add(user)
        await db.flush()
        await db.refresh(tenant)
        await db.refresh(user)
        return tenant, user

    @staticmethod
    async def create_user(
        db: AsyncSession,
        tenant_id: UUID,
        email: str,
        password: str,
        role: UserRole = UserRole.VIEWER,
    ) -> User:
        """Create a new user with hashed credentials under a tenant."""
        # Check tenant exists
        await UserService.get_tenant_by_id(db, tenant_id)

        # Check unique constraint (tenant_id, email)
        existing = await UserService.get_user_by_email(db, tenant_id=tenant_id, email=email)
        if existing:
            raise ConflictException(
                f"User with email '{email}' already exists in this tenant organization."
            )

        user = User(
            tenant_id=tenant_id,
            email=email.lower().strip(),
            password_hash=hash_password(password),
            role=role.value if isinstance(role, UserRole) else str(role),
            is_active=True,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def list_users_by_tenant(
        db: AsyncSession,
        tenant_id: UUID,
    ) -> list[User]:
        """List all users within a tenant organization."""
        result = await db.execute(
            select(User)
            .where(User.tenant_id == tenant_id)
            .order_by(User.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_user_by_email(
        db: AsyncSession,
        email: str,
        tenant_id: UUID | None = None,
    ) -> User | None:
        """Find a user by email, optionally scoping to a tenant."""
        query = select(User).where(User.email == email.lower().strip())
        if tenant_id:
            query = query.where(User.tenant_id == tenant_id)
        result = await db.execute(query)
        return result.scalars().first()

    @staticmethod
    async def get_user_by_id(
        db: AsyncSession,
        user_id: UUID,
        tenant_id: UUID | None = None,
    ) -> User:
        """Find a user by ID, optionally scoping to a tenant."""
        query = select(User).where(User.id == user_id)
        if tenant_id:
            query = query.where(User.tenant_id == tenant_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundException("User", user_id)
        return user

    @staticmethod
    async def update_user_status(
        db: AsyncSession,
        user_id: UUID,
        tenant_id: UUID,
        is_active: bool,
        actor_user_id: UUID,
    ) -> User:
        """Activate or deactivate a user account within the tenant."""
        if user_id == actor_user_id and not is_active:
            raise ValidationException("Administrators cannot deactivate their own account.")

        user = await UserService.get_user_by_id(db, user_id=user_id, tenant_id=tenant_id)
        user.is_active = is_active
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        email: str,
        password: str,
        tenant_id: UUID | None = None,
    ) -> User:
        """Authenticate user credentials and ensure active account status."""
        user = await UserService.get_user_by_email(db, email=email, tenant_id=tenant_id)
        if not user or not verify_password(password, user.password_hash):
            raise UnauthorizedException("Invalid email or password.")

        if not user.is_active:
            raise UnauthorizedException(
                "User account is inactive. Please contact your administrator."
            )

        return user

