import re
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth_context import AuthContext, require_auth
from app.database import get_db
from app.http import success
from app.models import Profile, ProfileTimeSlot, utc_now
from app.services.matching import CATEGORIES, STAGES, STYLES, MatchingProfile, TimeSlot

router = APIRouter(prefix="/profiles", tags=["learning profiles"])
TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def time_minutes(value: str, *, allow_midnight: bool = False) -> int:
    if allow_midnight and value == "24:00":
        return 1440
    if not TIME_PATTERN.fullmatch(value):
        raise ValueError("时间格式必须为 HH:mm")
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute


def format_time(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


class TimeSlotPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    day: int = Field(ge=1, le=7, strict=True)
    start: str
    end: str

    @model_validator(mode="after")
    def valid_interval(self):
        if time_minutes(self.end, allow_midnight=True) <= time_minutes(self.start):
            raise ValueError("结束时间必须晚于开始时间；跨午夜请拆成两天")
        return self


class ProfilePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=50)
    school: str = Field(default="", max_length=100)
    major: str = Field(default="", max_length=100)
    bio: str = Field(default="", max_length=300)
    categories: list[str] = Field(default_factory=list, max_length=8)
    tags: list[str] = Field(default_factory=list, max_length=20)
    styles: list[str] = Field(default_factory=list, max_length=8)
    stage: str | None = None
    time_slots: list[TimeSlotPayload] = Field(default_factory=list, alias="timeSlots", max_length=42)
    daily_target_minutes: int = Field(default=180, alias="dailyTargetMinutes", ge=30, le=720, strict=True)
    matching_enabled: bool = Field(default=False, alias="publicProfile", strict=True)
    allow_invites: bool = Field(default=False, alias="allowInvites", strict=True)
    timezone: Literal["Asia/Shanghai", "Asia/Hong_Kong"] = "Asia/Shanghai"

    @field_validator("categories", "tags", "styles")
    @classmethod
    def valid_list(cls, values: list[str], info) -> list[str]:
        cleaned = []
        seen = set()
        options = CATEGORIES if info.field_name == "categories" else STYLES
        for value in values:
            value = value.strip()
            if not 1 <= len(value) <= 32:
                raise ValueError("标签长度须为 1–32 字符")
            if info.field_name != "tags" and value not in options:
                raise ValueError("请选择预设的学习方向或方式")
            if value.lower() not in seen:
                cleaned.append(value)
                seen.add(value.lower())
        return cleaned

    @field_validator("stage")
    @classmethod
    def valid_stage(cls, value: str | None) -> str | None:
        if value is not None and value not in STAGES:
            raise ValueError("请选择预设学习阶段")
        return value

    @model_validator(mode="after")
    def unique_slots(self):
        keys = {(s.day, s.start, s.end) for s in self.time_slots}
        if len(keys) != len(self.time_slots):
            raise ValueError("请移除重复的学习时段")
        return self


async def load_profile(db: AsyncSession, user_id, *, lock: bool = False) -> Profile:
    statement = select(Profile).where(Profile.user_id == user_id).options(selectinload(Profile.time_slots))
    if lock:
        statement = statement.with_for_update()
    return (await db.scalars(statement.execution_options(populate_existing=True))).one()


def matching_input(profile: Profile) -> MatchingProfile:
    return MatchingProfile(
        categories=profile.categories,
        tags=profile.tags,
        styles=profile.styles,
        stage=profile.stage,
        time_slots=[TimeSlot(s.day, s.start_minute, s.end_minute) for s in profile.time_slots],
    )


def public_profile(profile: Profile) -> dict:
    # Deliberate whitelist. Never serialize the User ORM or the owner-only fields.
    return {
        "id": str(profile.user_id),
        "name": profile.display_name,
        "avatar": profile.display_name[:1],
        "categories": profile.categories,
        "tags": profile.tags,
        "styles": profile.styles,
        "stage": profile.stage,
        "timezone": profile.timezone_name,
        "allowInvites": profile.matching_enabled and profile.allow_invites,
        "timeSlots": [
            {"day": s.day, "start": format_time(s.start_minute), "end": format_time(s.end_minute)}
            for s in profile.time_slots
        ],
    }


def own_profile(profile: Profile) -> dict:
    return {
        **public_profile(profile),
        "school": profile.school,
        "major": profile.major,
        "bio": profile.bio,
        "publicProfile": profile.matching_enabled,
        "allowInvites": profile.allow_invites,
        "dailyTargetMinutes": profile.daily_target_minutes,
        "updatedAt": profile.updated_at.isoformat(),
        "timeSlots": [
            {"id": str(s.id), "day": s.day, "start": format_time(s.start_minute), "end": format_time(s.end_minute)}
            for s in profile.time_slots
        ],
    }


@router.get("/me")
async def get_profile(
    request: Request,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    return success(request, own_profile(await load_profile(db, auth.user.id)))


@router.put("/me")
async def update_profile(
    payload: ProfilePayload,
    request: Request,
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    profile = await load_profile(db, auth.user.id, lock=True)
    profile.display_name = payload.name
    for key in ("school", "major", "bio", "categories", "tags", "styles", "stage", "daily_target_minutes", "matching_enabled", "allow_invites"):
        setattr(profile, key, getattr(payload, key))
    profile.timezone_name = payload.timezone
    profile.updated_at = utc_now()
    profile.onboarding_completed = bool(payload.categories and payload.tags and payload.time_slots and payload.styles and payload.stage)
    # Replace only the authenticated owner's availability, in the same transaction.
    await db.execute(delete(ProfileTimeSlot).where(ProfileTimeSlot.user_id == auth.user.id))
    db.add_all([
        ProfileTimeSlot(
            user_id=auth.user.id, day=slot.day,
            start_minute=time_minutes(slot.start),
            end_minute=time_minutes(slot.end, allow_midnight=True),
        )
        for slot in payload.time_slots
    ])
    await db.commit()
    return success(request, own_profile(await load_profile(db, auth.user.id)))
