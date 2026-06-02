
"""
Pytest configuration and fixtures.
Provides test database, test client, and test users.
"""

import os

os.environ.setdefault("ENVIRONMENT", "test")

import pytest
from typing import AsyncGenerator, Generator

from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.pool import NullPool

from app.main import app
from app.database import Base
from app.api.deps import get_db
from app.config import settings
from app.models.user import User
from app.core.security import get_password_hash, create_access_token
from app.repositories.user_repository import user_repository


# Test database URL (separate from development database)
TEST_DATABASE_URL = settings.DATABASE_URL.replace(
    "task_management_dev",
    "task_management_test",
)

@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database for each test.
    Creates all tables before test, drops them after.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
def client(db_session: AsyncSession) -> Generator:
    """
    Create test client with overridden database dependency.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client sharing the test DB session (same event loop)."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    """
    Create a test user.
    """
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "hashed_password": get_password_hash("testpass123"),
        "full_name": "Test User",
        "is_active": True,
        "is_verified": True,
        "is_admin": False,
    }

    user = await user_repository.create(db_session, obj_in=user_data)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
async def test_user_unverified(db_session: AsyncSession) -> User:
    """
    Create an unverified test user.
    """
    user_data = {
        "email": "unverified@example.com",
        "username": "unverified",
        "hashed_password": get_password_hash("testpass123"),
        "full_name": "Unverified User",
        "is_active": True,
        "is_verified": False,
        "is_admin": False,
    }

    user = await user_repository.create(db_session, obj_in=user_data)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin test user."""
    user_data = {
        "email": "admin@example.com",
        "username": "adminuser",
        "hashed_password": get_password_hash("testpass123"),
        "full_name": "Admin User",
        "is_active": True,
        "is_verified": True,
        "is_admin": True,
    }
    user = await user_repository.create(db_session, obj_in=user_data)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    """Create a second non-admin user."""
    user_data = {
        "email": "other@example.com",
        "username": "otheruser",
        "hashed_password": get_password_hash("testpass123"),
        "full_name": "Other User",
        "is_active": True,
        "is_verified": True,
        "is_admin": False,
    }
    user = await user_repository.create(db_session, obj_in=user_data)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def admin_headers(admin_user: User) -> dict:
    """Authorization headers for admin user."""
    token = create_access_token(data={"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_user_token(test_user: User) -> str:
    """
    Create access token for test user.
    """
    return create_access_token(data={"sub": str(test_user.id)})


@pytest.fixture
def auth_headers(test_user_token: str) -> dict:
    """
    Create authorization headers with test user token.
    """
    return {"Authorization": f"Bearer {test_user_token}"}
