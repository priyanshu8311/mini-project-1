from collections.abc import AsyncGenerator

import pytest
from backend.src.core.database import Base, get_db_session
from backend.src.core.rate_limit import login_rate_limiter
from backend.src.core.security import create_access_token
from backend.src.domain.users.models import Tenant, User, UserRole
from backend.src.domain.users.service import UserService
from backend.src.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# In-memory SQLite async test database
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    future=True,
)

TestAsyncSession = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest.fixture(autouse=True)
async def setup_test_database() -> AsyncGenerator[None, None]:
    """Create all tables in in-memory test database and tear down after each test."""
    # Reset rate limit counters before each test
    login_rate_limiter.reset()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session for direct test assertions."""
    async with TestAsyncSession() as session:
        yield session


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an asynchronous HTTP client with overridden database session."""

    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with TestAsyncSession() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """Create and return a sample tenant."""
    tenant = await UserService.create_tenant(db_session, name="Acme Logistics")
    await db_session.commit()
    return tenant


@pytest.fixture
async def test_admin_user(db_session: AsyncSession, test_tenant: Tenant) -> User:
    """Create and return a test Admin user."""
    user = await UserService.create_user(
        db_session,
        tenant_id=test_tenant.id,
        email="admin@acme.com",
        password="Password123!",
        role=UserRole.ADMIN,
    )
    await db_session.commit()
    return user


@pytest.fixture
async def test_viewer_user(db_session: AsyncSession, test_tenant: Tenant) -> User:
    """Create and return a test Viewer user."""
    user = await UserService.create_user(
        db_session,
        tenant_id=test_tenant.id,
        email="viewer@acme.com",
        password="Password123!",
        role=UserRole.VIEWER,
    )
    await db_session.commit()
    return user


@pytest.fixture
def admin_token(test_admin_user: User) -> str:
    """Generate a valid JWT token for the admin user."""
    return create_access_token(
        {
            "sub": str(test_admin_user.id),
            "tenant_id": str(test_admin_user.tenant_id),
            "role": test_admin_user.role,
            "email": test_admin_user.email,
        }
    )


@pytest.fixture
def viewer_token(test_viewer_user: User) -> str:
    """Generate a valid JWT token for the viewer user."""
    return create_access_token(
        {
            "sub": str(test_viewer_user.id),
            "tenant_id": str(test_viewer_user.tenant_id),
            "role": test_viewer_user.role,
            "email": test_viewer_user.email,
        }
    )
