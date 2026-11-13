import uuid
from datetime import date

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_context import AuthContext, require_auth
from app.database import get_db
from app.http import ApiProblem, success
from app.models import Checkin, Goal
from app.services.study_calendar import study_today

router = APIRouter(prefix="/checkins", tags=["checkins"])


class CheckinPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    study_date: date = Field(alias="date")
    duration: int = Field(ge=1, le=1440)
    content: str = Field(min_length=1, max_length=1000)
    mood: str = Field(min_length=1, max_length=30)
    goal_id: uuid.UUID | None = Field(default=None, alias="goalId")

    @field_validator("content", "mood")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("字段不能为空")
        return value

    @field_validator("study_date")
    @classmethod
    def reject_future_date(cls, value: date) -> date:
        if value > study_today():
            raise ValueError("不能提交未来日期的打卡")
        return value


def serialize_checkin(checkin: Checkin) -> dict[str, object]:
    return {
        "id": str(checkin.id),
        "date": checkin.study_date.isoformat(),
        "duration": checkin.duration_minutes,
        "content": checkin.content,
        "mood": checkin.mood,
        "goalId": str(checkin.goal_id) if checkin.goal_id else None,
        "createdAt": checkin.created_at.isoformat(),
    }


async def validate_goal_owner(
    db: AsyncSession,
    goal_id: uuid.UUID | None,
    user_id: uuid.UUID,
) -> None:
    if not goal_id:
        return
    owner = await db.scalar(select(Goal.user_id).where(Goal.id == goal_id))
    if owner != user_id:
        raise ApiProblem(404, "GOAL_NOT_FOUND", "关联目标不存在")


@router.get("")
async def list_checkins(
    request: Request,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    checkins = (
        await db.scalars(
            select(Checkin)
            .where(Checkin.user_id == auth.user.id)
            .order_by(Checkin.study_date.desc(), Checkin.created_at.desc())
        )
    ).all()
    return success(request, [serialize_checkin(item) for item in checkins])


@router.post("", status_code=201)
async def create_checkin(
    payload: CheckinPayload,
    request: Request,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    await validate_goal_owner(db, payload.goal_id, auth.user.id)
    checkin = Checkin(
        user_id=auth.user.id,
        goal_id=payload.goal_id,
        study_date=payload.study_date,
        duration_minutes=payload.duration,
        content=payload.content,
        mood=payload.mood,
    )
    db.add(checkin)
    await db.commit()
    await db.refresh(checkin)
    return success(request, serialize_checkin(checkin), "打卡已保存")


@router.get("/{checkin_id}")
async def get_checkin(
    checkin_id: uuid.UUID,
    request: Request,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    checkin = await db.scalar(
        select(Checkin).where(Checkin.id == checkin_id, Checkin.user_id == auth.user.id)
    )
    if not checkin:
        raise ApiProblem(404, "CHECKIN_NOT_FOUND", "打卡记录不存在")
    return success(request, serialize_checkin(checkin))


@router.delete("/{checkin_id}", status_code=204)
async def delete_checkin(
    checkin_id: uuid.UUID,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    checkin = await db.scalar(
        select(Checkin).where(Checkin.id == checkin_id, Checkin.user_id == auth.user.id)
    )
    if not checkin:
        raise ApiProblem(404, "CHECKIN_NOT_FOUND", "打卡记录不存在")
    await db.delete(checkin)
    await db.commit()
