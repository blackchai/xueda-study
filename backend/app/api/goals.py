import re
import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth_context import AuthContext, require_auth
from app.database import get_db
from app.http import ApiProblem, success
from app.models import Goal, GoalTask, utc_now

router = APIRouter(prefix="/goals", tags=["goals"])
COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


class TaskPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    due_date: date = Field(alias="dueDate")
    estimated_minutes: int = Field(alias="estimatedMinutes", ge=1, le=1440)
    completed: bool = False

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("任务标题不能为空")
        return value


class GoalPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=2000)
    category: str = Field(min_length=1, max_length=40)
    tags: list[str] = Field(default_factory=list, max_length=20)
    start_date: date = Field(alias="startDate")
    target_date: date = Field(alias="targetDate")
    status: Literal["进行中", "已完成", "已暂停"] = "进行中"
    color: str = "#5b5ce2"

    @field_validator("title", "category")
    @classmethod
    def strip_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("字段不能为空")
        return value

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value.strip()[:40] for value in values if value.strip()))

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str) -> str:
        if not COLOR_PATTERN.fullmatch(value):
            raise ValueError("颜色必须为 #RRGGBB")
        return value.lower()

    @model_validator(mode="after")
    def validate_dates(self):
        if self.target_date < self.start_date:
            raise ValueError("目标日期不能早于开始日期")
        return self


def serialize_task(task: GoalTask) -> dict[str, object]:
    return {
        "id": str(task.id),
        "title": task.title,
        "dueDate": task.due_date.isoformat(),
        "estimatedMinutes": task.estimated_minutes,
        "completed": task.completed,
    }


def serialize_goal(goal: Goal) -> dict[str, object]:
    return {
        "id": str(goal.id),
        "title": goal.title,
        "description": goal.description,
        "category": goal.category,
        "tags": goal.tags,
        "startDate": goal.start_date.isoformat(),
        "targetDate": goal.target_date.isoformat(),
        "status": goal.status,
        "color": goal.color,
        "tasks": [serialize_task(task) for task in goal.tasks],
        "createdAt": goal.created_at.isoformat(),
    }


async def owned_goal(
    db: AsyncSession,
    goal_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    with_tasks: bool = False,
) -> Goal:
    statement = select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id)
    if with_tasks:
        statement = statement.options(selectinload(Goal.tasks))
    goal = await db.scalar(statement)
    if not goal:
        raise ApiProblem(404, "GOAL_NOT_FOUND", "学习目标不存在")
    return goal


@router.get("")
async def list_goals(
    request: Request,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    goals = (
        await db.scalars(
            select(Goal)
            .where(Goal.user_id == auth.user.id)
            .options(selectinload(Goal.tasks))
            .order_by(Goal.created_at.desc())
        )
    ).all()
    return success(request, [serialize_goal(goal) for goal in goals])


@router.post("", status_code=201)
async def create_goal(
    payload: GoalPayload,
    request: Request,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    goal = Goal(
        user_id=auth.user.id,
        title=payload.title,
        description=payload.description.strip(),
        category=payload.category,
        tags=payload.tags,
        start_date=payload.start_date,
        target_date=payload.target_date,
        status=payload.status,
        color=payload.color,
    )
    db.add(goal)
    await db.commit()
    goal = await db.scalar(
        select(Goal).where(Goal.id == goal.id).options(selectinload(Goal.tasks))
    )
    if not goal:
        raise ApiProblem(500, "GOAL_CREATE_FAILED", "目标创建失败")
    return success(request, serialize_goal(goal), "目标已创建")


@router.get("/{goal_id}")
async def get_goal(
    goal_id: uuid.UUID,
    request: Request,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    goal = await owned_goal(db, goal_id, auth.user.id, with_tasks=True)
    return success(request, serialize_goal(goal))


@router.put("/{goal_id}")
async def update_goal(
    goal_id: uuid.UUID,
    payload: GoalPayload,
    request: Request,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    goal = await owned_goal(db, goal_id, auth.user.id, with_tasks=True)
    goal.title = payload.title
    goal.description = payload.description.strip()
    goal.category = payload.category
    goal.tags = payload.tags
    goal.start_date = payload.start_date
    goal.target_date = payload.target_date
    goal.status = payload.status
    goal.color = payload.color
    await db.commit()
    return success(request, serialize_goal(goal), "目标已更新")


@router.delete("/{goal_id}", status_code=204)
async def delete_goal(
    goal_id: uuid.UUID,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    goal = await owned_goal(db, goal_id, auth.user.id)
    await db.delete(goal)
    await db.commit()


@router.post("/{goal_id}/tasks", status_code=201)
async def create_task(
    goal_id: uuid.UUID,
    payload: TaskPayload,
    request: Request,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    goal = await owned_goal(db, goal_id, auth.user.id)
    task = GoalTask(
        goal_id=goal.id,
        title=payload.title,
        due_date=payload.due_date,
        estimated_minutes=payload.estimated_minutes,
        completed=payload.completed,
        completed_at=utc_now() if payload.completed else None,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return success(request, serialize_task(task), "任务已创建")


async def owned_task(
    db: AsyncSession,
    goal_id: uuid.UUID,
    task_id: uuid.UUID,
    user_id: uuid.UUID,
) -> GoalTask:
    task = await db.scalar(
        select(GoalTask)
        .join(Goal, Goal.id == GoalTask.goal_id)
        .where(GoalTask.id == task_id, GoalTask.goal_id == goal_id, Goal.user_id == user_id)
    )
    if not task:
        raise ApiProblem(404, "TASK_NOT_FOUND", "学习任务不存在")
    return task


@router.put("/{goal_id}/tasks/{task_id}")
async def update_task(
    goal_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: TaskPayload,
    request: Request,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    task = await owned_task(db, goal_id, task_id, auth.user.id)
    task.title = payload.title
    task.due_date = payload.due_date
    task.estimated_minutes = payload.estimated_minutes
    if task.completed != payload.completed:
        task.completed_at = utc_now() if payload.completed else None
    task.completed = payload.completed
    await db.commit()
    return success(request, serialize_task(task), "任务已更新")


@router.delete("/{goal_id}/tasks/{task_id}", status_code=204)
async def delete_task(
    goal_id: uuid.UUID,
    task_id: uuid.UUID,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    task = await owned_task(db, goal_id, task_id, auth.user.id)
    await db.delete(task)
    await db.commit()
