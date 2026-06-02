"""
Admin task API endpoints.
Full CRUD on tasks for any user; requires admin authentication.
"""

import math
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_admin_user
from app.core.exceptions import NotFoundError
from app.models.task import TaskPriority, TaskStatus
from app.models.user import User
from app.schemas.task import (
    AdminTaskCreate,
    AdminTaskListResponse,
    AdminTaskResponse,
    TaskOwnerSummary,
    TaskUpdate,
)
from app.services.task_service import task_service

router = APIRouter()


def _to_admin_task_response(task) -> AdminTaskResponse:
    response = AdminTaskResponse.model_validate(task)
    response.is_overdue = task.is_overdue
    response.owner = TaskOwnerSummary.model_validate(task.owner)
    return response


@router.get("/", response_model=AdminTaskListResponse)
async def admin_list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    user_id: Optional[uuid.UUID] = Query(None, description="Filter by task owner"),
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    priority_filter: Optional[TaskPriority] = Query(None, alias="priority"),
    category_id: Optional[uuid.UUID] = Query(None),
    search: Optional[str] = Query(None, max_length=200),
    due_date_from: Optional[datetime] = Query(None),
    due_date_to: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all tasks with optional filters and owner details."""
    try:
        tasks, total = await task_service.admin_list_tasks(
            db,
            user_id=user_id,
            status=status_filter,
            priority=priority_filter,
            category_id=category_id,
            search=search,
            due_date_from=due_date_from,
            due_date_to=due_date_to,
            skip=skip,
            limit=limit,
        )
        page = (skip // limit) + 1
        total_pages = math.ceil(total / limit) if total > 0 else 0
        return AdminTaskListResponse(
            items=[_to_admin_task_response(t) for t in tasks],
            total=total,
            page=page,
            page_size=limit,
            total_pages=total_pages,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{task_id}", response_model=AdminTaskResponse)
async def admin_get_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        task = await task_service.admin_get_task(db, task_id)
        return _to_admin_task_response(task)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/", response_model=AdminTaskResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_task(
    task_in: AdminTaskCreate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        task = await task_service.admin_create_task(db, task_in)
        return _to_admin_task_response(task)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/{task_id}", response_model=AdminTaskResponse)
async def admin_update_task(
    task_id: uuid.UUID,
    task_update: TaskUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        task = await task_service.admin_update_task(db, task_id, task_update)
        return _to_admin_task_response(task)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        await task_service.admin_delete_task(db, task_id)
        return None
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{task_id}/status", response_model=AdminTaskResponse)
async def admin_update_task_status(
    task_id: uuid.UUID,
    new_status: TaskStatus,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        task = await task_service.admin_update_task(
            db, task_id, TaskUpdate(status=new_status)
        )
        return _to_admin_task_response(task)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/{task_id}/priority", response_model=AdminTaskResponse)
async def admin_update_task_priority(
    task_id: uuid.UUID,
    new_priority: TaskPriority,
    current_user: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        task = await task_service.admin_update_task(
            db, task_id, TaskUpdate(priority=new_priority)
        )
        return _to_admin_task_response(task)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
