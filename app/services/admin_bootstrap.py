"""
Admin startup: seed default admin and promote users from ADMIN_EMAILS.
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.core.security import get_password_hash
from app.repositories.user_repository import user_repository

logger = logging.getLogger(__name__)


def _should_sync_seed_password() -> bool:
    """Whether to apply DEFAULT_ADMIN_PASSWORD to an existing default admin."""
    if not settings.SEED_DEFAULT_ADMIN_SYNC_PASSWORD:
        return False
    return settings.ENVIRONMENT in ("development", "test")


async def seed_default_admin(db: AsyncSession) -> bool:
    """
    Create the default admin account if it does not exist.
    If the user exists, ensure is_admin and optionally sync password from env.

    Returns:
        True if a new user was created, False otherwise.
    """
    if not settings.SEED_DEFAULT_ADMIN:
        return False

    email = settings.DEFAULT_ADMIN_EMAIL.strip().lower()
    username = settings.DEFAULT_ADMIN_USERNAME.strip()
    password = settings.DEFAULT_ADMIN_PASSWORD

    if not email or not username or not password:
        logger.warning(
            "SEED_DEFAULT_ADMIN is enabled but DEFAULT_ADMIN_* settings are incomplete; skipping seed"
        )
        return False

    if len(password) < 8:
        logger.error(
            "DEFAULT_ADMIN_PASSWORD must be at least 8 characters; skipping default admin seed"
        )
        return False

    user = await user_repository.get_by_email(db, email)
    if user:
        updated = False
        if not user.is_admin:
            user.is_admin = True
            updated = True
        if not user.is_verified:
            user.is_verified = True
            updated = True
        if not user.is_active:
            user.is_active = True
            updated = True
        if _should_sync_seed_password():
            user.hashed_password = get_password_hash(password)
            updated = True
            logger.info(
                "Default admin %s: password synced from DEFAULT_ADMIN_PASSWORD",
                email,
            )
        if updated:
            logger.info("Default admin account %s updated", email)
        return False

    await user_repository.create(
        db,
        obj_in={
            "email": email,
            "username": username,
            "hashed_password": get_password_hash(password),
            "full_name": settings.DEFAULT_ADMIN_FULL_NAME,
            "is_active": True,
            "is_verified": True,
            "is_admin": True,
        },
    )

    if settings.ENVIRONMENT == "production":
        logger.warning(
            "Created default admin %s in production — change DEFAULT_ADMIN_PASSWORD immediately",
            email,
        )
    else:
        logger.info(
            "Created default admin %s (username=%s). Login password is DEFAULT_ADMIN_PASSWORD from .env",
            email,
            username,
        )
    return True


async def promote_admin_users_from_env(db: AsyncSession) -> int:
    """
    Set is_admin=True for users whose email is listed in ADMIN_EMAILS.

    Returns:
        Number of users promoted in this run.
    """
    emails = settings.admin_emails_list
    if not emails:
        return 0

    promoted = 0
    for email in emails:
        user = await user_repository.get_by_email(db, email.lower())
        if user is None:
            logger.warning(
                "ADMIN_EMAILS: user with email %s not found; skipping promote",
                email,
            )
            continue
        if not user.is_admin:
            user.is_admin = True
            promoted += 1
            logger.info("Promoted user %s to admin", email)

    return promoted


async def run_admin_startup(db: AsyncSession) -> None:
    """Seed default admin and promote ADMIN_EMAILS on application startup."""
    created = await seed_default_admin(db)
    promoted = await promote_admin_users_from_env(db)
    if created:
        logger.info("Admin startup: default admin account created")
    if promoted:
        logger.info("Admin startup: promoted %d user(s) from ADMIN_EMAILS", promoted)
    if settings.SEED_DEFAULT_ADMIN and (created or promoted):
        logger.info(
            "Default admin login: username=%s (password from DEFAULT_ADMIN_PASSWORD in .env)",
            settings.DEFAULT_ADMIN_USERNAME,
        )
