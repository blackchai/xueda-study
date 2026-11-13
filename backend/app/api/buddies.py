import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.profiles import load_profile, matching_input, public_profile, time_minutes
from app.auth_context import AuthContext, require_auth
from app.database import get_db
from app.http import ApiProblem, success
from app.models import BuddyRelation, Profile, User, utc_now
from app.services.buddy_connections import add_notification, commit_changes, connection_states, lock_participants, relation_payloads
from app.services.matching import CATEGORIES, MATCHING_TIMEZONES, calculate_match

router = APIRouter(prefix="/buddies", tags=["buddy recommendations"])


@router.get("/recommendations")
async def recommendations(
    request: Request,
    category: str | None = Query(default=None, max_length=40),
    period: Literal["morning", "daytime", "evening"] | None = None,
    day: int | None = Query(default=None, ge=1, le=7),
    start: str | None = Query(default=None, max_length=5),
    end: str | None = Query(default=None, max_length=5),
    overlap_only: bool = Query(default=False, alias="overlapOnly"),
    q: str = Query(default="", max_length=100),
    page: int = Query(default=1, ge=1, le=10000),
    page_size: int = Query(default=12, alias="pageSize", ge=1, le=50),
    auth: AuthContext = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    if category is not None and category not in CATEGORIES:
        raise ApiProblem(422, "VALIDATION_ERROR", "请选择预设学习方向")
    if bool(start) != bool(end) or (period and start is not None):
        raise ApiProblem(422, "VALIDATION_ERROR", "开始和结束时间须同时提供，且不能与时段筛选并用")
    interval = None
    if start is not None and end is not None:
        try:
            interval = (time_minutes(start), time_minutes(end, allow_midnight=True))
            if interval[0] >= interval[1]:
                raise ValueError("invalid range")
        except ValueError:
            raise ApiProblem(422, "VALIDATION_ERROR", "筛选时段不合法") from None
    elif period:
        interval = {"morning": (0, 720), "daytime": (720, 1080), "evening": (1080, 1440)}[period]

    viewer = await load_profile(db, auth.user.id)
    if viewer.timezone_name not in MATCHING_TIMEZONES:
        raise ApiProblem(422, "UNSUPPORTED_TIMEZONE", "请先将匹配档案时区设置为北京时间 UTC+8")
    candidates = await db.scalars(
        select(Profile)
        .join(User, Profile.user_id == User.id)
        .where(
            Profile.user_id != auth.user.id,
            Profile.matching_enabled.is_(True),
            Profile.timezone_name.in_(MATCHING_TIMEZONES),
            User.is_active.is_(True),
            User.status == "active",
        )
        .options(selectinload(Profile.time_slots))
    )
    viewer_input = matching_input(viewer)
    keyword = q.strip().lower()
    items = []
    for candidate in candidates:
        if category and category not in candidate.categories:
            continue
        if keyword and keyword not in " ".join([candidate.display_name, *candidate.tags, *candidate.categories]).lower():
            continue
        if (day is not None or interval) and not any(
            (day is None or slot.day == day)
            and (interval is None or (slot.start_minute < interval[1] and slot.end_minute > interval[0]))
            for slot in candidate.time_slots
        ):
            continue
        result = calculate_match(viewer_input, matching_input(candidate))
        if overlap_only and result["overlapMinutes"] == 0:
            continue
        items.append({**public_profile(candidate), **result})
    # Stable across processes, requests and database row order, including ties.
    items.sort(key=lambda item: (-item["score"], item["id"]))
    offset = (page - 1) * page_size
    visible_items = items[offset:offset + page_size]
    states = await connection_states(db, auth.user.id, [uuid.UUID(item["id"]) for item in visible_items])
    for item in visible_items:
        item["connection"] = states.get(uuid.UUID(item["id"]), {"status": "none"})
    return success(request, {
        "items": visible_items,
        "page": page, "pageSize": page_size, "total": len(items),
        "timezone": "Asia/Shanghai", "algorithmVersion": "weighted-v1",
    })


@router.get("")
async def list_buddies(request: Request, page: int = Query(1, ge=1, le=10000),
                       page_size: int = Query(12, alias="pageSize", ge=1, le=50),
                       auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    conditions = [BuddyRelation.ended_at.is_(None),
                  or_(BuddyRelation.user_low_id == auth.user.id, BuddyRelation.user_high_id == auth.user.id)]
    total = await db.scalar(select(func.count()).select_from(BuddyRelation).where(*conditions))
    items = list(await db.scalars(select(BuddyRelation).where(*conditions)
                                 .order_by(BuddyRelation.created_at.desc(), BuddyRelation.id)
                                 .offset((page - 1) * page_size).limit(page_size)))
    return success(request, {"items": await relation_payloads(db, items, auth.user.id),
                             "page": page, "pageSize": page_size, "total": total})


@router.delete("/{relation_id}", status_code=204)
async def remove_buddy(relation_id: uuid.UUID, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    viewer = auth.user.id
    relation = await db.get(BuddyRelation, relation_id)
    if not relation or viewer not in (relation.user_low_id, relation.user_high_id):
        raise ApiProblem(404, "BUDDY_RELATION_NOT_FOUND", "搭子关系不存在")
    await lock_participants(db, relation.user_low_id, relation.user_high_id)
    relation = await db.scalar(select(BuddyRelation).where(BuddyRelation.id == relation_id)
                               .with_for_update().execution_options(populate_existing=True))
    if relation and not relation.ended_at:
        relation.ended_at, relation.ended_by = utc_now(), viewer
        peer = relation.user_high_id if relation.user_low_id == viewer else relation.user_low_id
        add_notification(db, recipient=peer, actor=viewer, kind="buddy_relation_removed", relation_id=relation.id)
        await commit_changes(db)
    return Response(status_code=204)
