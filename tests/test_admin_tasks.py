"""
Tests for admin task endpoints.
"""

import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.task_repository import task_repository
from app.services.admin_bootstrap import promote_admin_users_from_env, seed_default_admin


class TestAdminAccess:
    """Admin authorization tests."""

    @pytest.mark.asyncio
    async def test_admin_list_requires_auth(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/admin/tasks/")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_list_forbidden_for_regular_user(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        response = await async_client.get(
            "/api/v1/admin/tasks/", headers=auth_headers
        )
        assert response.status_code == 403
        assert "Admin" in response.json()["detail"]


class TestAdminTaskCRUD:
    """Admin CRUD on tasks across users."""

    @pytest.fixture
    async def other_user_task(
        self, db_session: AsyncSession, other_user: User
    ):
        task = await task_repository.create(
            db_session,
            obj_in={
                "title": "Other user task",
                "user_id": other_user.id,
                "status": "TODO",
                "priority": "MEDIUM",
            },
        )
        await db_session.commit()
        await db_session.refresh(task)
        return task

    @pytest.mark.asyncio
    async def test_admin_lists_all_users_tasks(
        self,
        async_client: AsyncClient,
        admin_headers: dict,
        auth_headers: dict,
        other_user_task,
    ):
        await async_client.post(
            "/api/v1/tasks/",
            headers=auth_headers,
            json={"title": "My task"},
        )
        response = await async_client.get(
            "/api/v1/admin/tasks/", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 2
        titles = {item["title"] for item in data["items"]}
        assert "Other user task" in titles
        assert "My task" in titles
        for item in data["items"]:
            assert "owner" in item
            assert "email" in item["owner"]

    @pytest.mark.asyncio
    async def test_admin_list_filter_by_user_id(
        self,
        async_client: AsyncClient,
        admin_headers: dict,
        other_user: User,
        other_user_task,
        auth_headers: dict,
    ):
        await async_client.post(
            "/api/v1/tasks/",
            headers=auth_headers,
            json={"title": "My task"},
        )
        response = await async_client.get(
            f"/api/v1/admin/tasks/?user_id={other_user.id}",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Other user task"
        assert data["items"][0]["owner"]["id"] == str(other_user.id)

    @pytest.mark.asyncio
    async def test_admin_get_other_users_task(
        self,
        async_client: AsyncClient,
        admin_headers: dict,
        other_user_task,
        other_user: User,
    ):
        response = await async_client.get(
            f"/api/v1/admin/tasks/{other_user_task.id}",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Other user task"
        assert data["owner"]["username"] == other_user.username

    @pytest.mark.asyncio
    async def test_admin_create_task_for_user(
        self,
        async_client: AsyncClient,
        admin_headers: dict,
        other_user: User,
    ):
        response = await async_client.post(
            "/api/v1/admin/tasks/",
            headers=admin_headers,
            json={
                "title": "Admin created",
                "user_id": str(other_user.id),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Admin created"
        assert data["user_id"] == str(other_user.id)
        assert data["owner"]["email"] == other_user.email

    @pytest.mark.asyncio
    async def test_admin_update_other_users_task(
        self,
        async_client: AsyncClient,
        admin_headers: dict,
        other_user_task,
    ):
        response = await async_client.put(
            f"/api/v1/admin/tasks/{other_user_task.id}",
            headers=admin_headers,
            json={"title": "Updated by admin"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "Updated by admin"

    @pytest.mark.asyncio
    async def test_admin_delete_other_users_task(
        self,
        async_client: AsyncClient,
        admin_headers: dict,
        other_user_task,
    ):
        response = await async_client.delete(
            f"/api/v1/admin/tasks/{other_user_task.id}",
            headers=admin_headers,
        )
        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_regular_user_cannot_see_other_tasks(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        other_user_task,
    ):
        response = await async_client.get(
            f"/api/v1/tasks/{other_user_task.id}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestAdminBootstrap:
    """Admin seed and promotion from env."""

    @pytest.mark.asyncio
    async def test_seed_default_admin_creates_user(self, db_session: AsyncSession):
        with patch("app.services.admin_bootstrap.settings") as mock_settings:
            mock_settings.SEED_DEFAULT_ADMIN = True
            mock_settings.DEFAULT_ADMIN_EMAIL = "seed@example.com"
            mock_settings.DEFAULT_ADMIN_USERNAME = "seedadmin"
            mock_settings.DEFAULT_ADMIN_PASSWORD = "SeedPass123!"
            mock_settings.DEFAULT_ADMIN_FULL_NAME = "Seed Admin"
            mock_settings.ENVIRONMENT = "development"
            mock_settings.SEED_DEFAULT_ADMIN_SYNC_PASSWORD = False
            created = await seed_default_admin(db_session)
            await db_session.commit()

        assert created is True
        from app.repositories.user_repository import user_repository

        user = await user_repository.get_by_email(db_session, "seed@example.com")
        assert user is not None
        assert user.is_admin is True
        assert user.is_verified is True

    @pytest.mark.asyncio
    async def test_seed_sync_password_for_existing_admin(
        self, db_session: AsyncSession, admin_user: User
    ):
        from app.core.security import verify_password

        with patch("app.services.admin_bootstrap.settings") as mock_settings:
            mock_settings.SEED_DEFAULT_ADMIN = True
            mock_settings.SEED_DEFAULT_ADMIN_SYNC_PASSWORD = True
            mock_settings.DEFAULT_ADMIN_EMAIL = admin_user.email
            mock_settings.DEFAULT_ADMIN_USERNAME = admin_user.username
            mock_settings.DEFAULT_ADMIN_PASSWORD = "NewSeedPass99!"
            mock_settings.DEFAULT_ADMIN_FULL_NAME = "Admin"
            mock_settings.ENVIRONMENT = "development"
            await seed_default_admin(db_session)
            await db_session.commit()

        await db_session.refresh(admin_user)
        assert verify_password("NewSeedPass99!", admin_user.hashed_password)

    @pytest.mark.asyncio
    async def test_seed_default_admin_idempotent(self, db_session: AsyncSession, admin_user: User):
        with patch("app.services.admin_bootstrap.settings") as mock_settings:
            mock_settings.SEED_DEFAULT_ADMIN = True
            mock_settings.DEFAULT_ADMIN_EMAIL = admin_user.email
            mock_settings.DEFAULT_ADMIN_USERNAME = "ignored"
            mock_settings.DEFAULT_ADMIN_PASSWORD = "IgnoredPass1!"
            mock_settings.DEFAULT_ADMIN_FULL_NAME = "Ignored"
            mock_settings.ENVIRONMENT = "development"
            mock_settings.SEED_DEFAULT_ADMIN_SYNC_PASSWORD = False
            created = await seed_default_admin(db_session)

        assert created is False

    @pytest.mark.asyncio
    async def test_promote_admin_users_from_env(
        self, db_session: AsyncSession, test_user: User
    ):
        with patch("app.services.admin_bootstrap.settings") as mock_settings:
            mock_settings.admin_emails_list = [test_user.email.upper()]
            promoted = await promote_admin_users_from_env(db_session)
            await db_session.commit()
        await db_session.refresh(test_user)
        assert promoted == 1
        assert test_user.is_admin is True


class TestUserMeAdminFlag:
    """is_admin visible only on /me endpoints."""

    @pytest.mark.asyncio
    async def test_auth_me_includes_is_admin_for_admin(
        self, async_client: AsyncClient, admin_headers: dict
    ):
        response = await async_client.get(
            "/api/v1/auth/me", headers=admin_headers
        )
        assert response.status_code == 200
        assert response.json()["is_admin"] is True

    @pytest.mark.asyncio
    async def test_public_profile_excludes_admin_flag(
        self, async_client: AsyncClient, auth_headers: dict, admin_user: User
    ):
        response = await async_client.get(
            f"/api/v1/users/{admin_user.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "is_admin" not in response.json()
