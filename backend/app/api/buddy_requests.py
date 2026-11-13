import uuid
from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_context import AuthContext, require_auth
from app.database import get_db
from app.http import ApiProblem, success
from app.models import BuddyRelation, BuddyRequest, Profile, as_utc, utc_now
from app.services.buddy_connections import (
    active_relation, add_notification, commit_changes, flush_changes, is_active, lock_participants,
    mark_request_handled, pair_ids, request_payloads,
)

router = APIRouter(prefix="/buddy-requests", tags=["buddy requests"])
Status = Literal["pending", "accepted", "rejected", "cancelled"]


class InvitationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    recipient_id: uuid.UUID = Field(alias="recipientId")
    message: str = Field(default="", max_length=200)


@router.post("")
async def send_invitation(payload: InvitationPayload, request: Request,
                          auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    sender, recipient = auth.user.id, payload.recipient_id
    if sender == recipient:
        raise ApiProblem(422, "CANNOT_INVITE_SELF", "不能邀请自己成为搭子")
    users = await lock_participants(db, sender, recipient)
    if not is_active(users.get(sender)) or not is_active(users.get(recipient)):
        raise ApiProblem(404, "BUDDY_UNAVAILABLE", "该用户当前不可邀请")
    low, high = pair_ids(sender, recipient)
    if await active_relation(db, sender, recipient):
        raise ApiProblem(409, "ALREADY_BUDDIES", "你们已经是学习搭子")
    pending = await db.scalar(select(BuddyRequest).where(
        BuddyRequest.user_low_id == low, BuddyRequest.user_high_id == high, BuddyRequest.status == "pending",
    ))
    if pending:
        if pending.sender_id != sender:
            raise ApiProblem(409, "INCOMING_REQUEST_EXISTS", "对方已发来邀请，请在收到的邀请中处理")
        # A retried POST returns the original resource, without changing its
        # message, resetting its date, consuming another quota or notifying twice.
        return success(request, (await request_payloads(db, [pending], sender))[0])
    profile = await db.scalar(select(Profile).where(Profile.user_id == recipient).with_for_update())
    if not profile or not profile.matching_enabled or not profile.allow_invites:
        raise ApiProblem(404, "BUDDY_UNAVAILABLE", "该用户当前不可邀请")

    settings, now = request.app.state.settings, utc_now()
    created = select(func.count()).select_from(BuddyRequest).where(BuddyRequest.sender_id == sender)
    hourly = await db.scalar(created.where(BuddyRequest.created_at >= now - timedelta(hours=1)))
    daily = await db.scalar(created.where(BuddyRequest.created_at >= now - timedelta(days=1)))
    pending_count = await db.scalar(created.where(BuddyRequest.status == "pending"))
    if hourly >= settings.buddy_invites_per_hour or daily >= settings.buddy_invites_per_day or pending_count >= settings.buddy_pending_limit:
        raise ApiProblem(429, "BUDDY_INVITE_RATE_LIMITED", "邀请过于频繁或待处理邀请过多，请稍后再试")
    latest = await db.scalar(select(BuddyRequest.created_at).where(
        BuddyRequest.user_low_id == low, BuddyRequest.user_high_id == high,
    ).order_by(BuddyRequest.created_at.desc()).limit(1))
    if latest and (now - as_utc(latest)).total_seconds() < settings.buddy_pair_cooldown_seconds:
        raise ApiProblem(429, "BUDDY_PAIR_COOLDOWN", "请给对方一些时间，稍后再发起邀请")

    invitation = BuddyRequest(id=uuid.uuid4(), sender_id=sender, recipient_id=recipient,
                              user_low_id=low, user_high_id=high, message=payload.message)
    db.add(invitation)
    await flush_changes(db)
    add_notification(db, recipient=recipient, actor=sender, kind="buddy_request_received", request_id=invitation.id)
    await commit_changes(db)
    return JSONResponse(status_code=201, content=success(request, (await request_payloads(db, [invitation], sender))[0]))


@router.get("")
async def list_invitations(request: Request, direction: Literal["incoming", "outgoing"] = "incoming",
                           status: Status | None = None, page: int = Query(1, ge=1, le=10000),
                           page_size: int = Query(12, alias="pageSize", ge=1, le=50),
                           auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    owner = BuddyRequest.recipient_id if direction == "incoming" else BuddyRequest.sender_id
    conditions = [owner == auth.user.id]
    if status:
        conditions.append(BuddyRequest.status == status)
    total = await db.scalar(select(func.count()).select_from(BuddyRequest).where(*conditions))
    pending_count = await db.scalar(select(func.count()).select_from(BuddyRequest).where(owner == auth.user.id, BuddyRequest.status == "pending"))
    items = list(await db.scalars(select(BuddyRequest).where(*conditions)
                                .order_by(BuddyRequest.created_at.desc(), BuddyRequest.id)
                                .offset((page - 1) * page_size).limit(page_size)))
    return success(request, {"items": await request_payloads(db, items, auth.user.id),
                             "page": page, "pageSize": page_size, "total": total, "pendingCount": pending_count})


async def owned_request(db: AsyncSession, request_id: uuid.UUID, viewer: uuid.UUID, *, lock=False):
    item = await db.get(BuddyRequest, request_id)
    if not item or viewer not in (item.sender_id, item.recipient_id):
        raise ApiProblem(404, "BUDDY_REQUEST_NOT_FOUND", "邀请不存在")
    if lock:
        await lock_participants(db, item.sender_id, item.recipient_id)
        item = await db.scalar(select(BuddyRequest).where(BuddyRequest.id == request_id)
                               .with_for_update().execution_options(populate_existing=True))
        if not item:
            raise ApiProblem(404, "BUDDY_REQUEST_NOT_FOUND", "邀请不存在")
    return item


@router.get("/{request_id}")
async def get_invitation(request_id: uuid.UUID, request: Request,
                          auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    item = await owned_request(db, request_id, auth.user.id)
    return success(request, (await request_payloads(db, [item], auth.user.id))[0])


@router.post("/{request_id}/{action}")
async def resolve_invitation(request_id: uuid.UUID, action: Literal["accept", "reject", "cancel"], request: Request,
                             auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    viewer = auth.user.id
    item = await owned_request(db, request_id, viewer, lock=True)
    required_owner = item.sender_id if action == "cancel" else item.recipient_id
    if viewer != required_owner:
        raise ApiProblem(404, "BUDDY_REQUEST_NOT_FOUND", "邀请不存在")
    desired = {"accept": "accepted", "reject": "rejected", "cancel": "cancelled"}[action]
    if item.status != "pending":
        if item.status == desired:
            if action == "accept":
                original_relation = await db.scalar(select(BuddyRelation).where(
                    BuddyRelation.source_request_id == item.id, BuddyRelation.ended_at.is_(None),
                ))
                if not original_relation:
                    raise ApiProblem(409, "BUDDY_REQUEST_CLOSED", "该邀请已结束，请重新发起邀请")
            return success(request, (await request_payloads(db, [item], viewer))[0])
        raise ApiProblem(409, "BUDDY_REQUEST_CLOSED", "邀请已处理，无法重复改变状态")
    now = utc_now()
    if action == "accept":
        # Recipient explicitly accepts an existing request even if they have
        # disabled future invitations. A disabled sender cannot form a relation.
        users = await lock_participants(db, item.sender_id, item.recipient_id)
        if not all(is_active(users.get(user_id)) for user_id in (item.sender_id, item.recipient_id)):
            raise ApiProblem(409, "BUDDY_UNAVAILABLE", "对方账号当前不可用")
        relation = await active_relation(db, item.sender_id, item.recipient_id)
        if relation:
            raise ApiProblem(409, "ALREADY_BUDDIES", "你们已经是学习搭子")
        relation = BuddyRelation(id=uuid.uuid4(), user_low_id=item.user_low_id,
                                 user_high_id=item.user_high_id, source_request_id=item.id)
        db.add(relation)
        await flush_changes(db)
        add_notification(db, recipient=item.sender_id, actor=viewer, kind="buddy_request_accepted",
                         request_id=item.id, relation_id=relation.id)
    elif action == "reject":
        add_notification(db, recipient=item.sender_id, actor=viewer, kind="buddy_request_rejected", request_id=item.id)
    item.status, item.resolved_at, item.updated_at = desired, now, now
    await mark_request_handled(db, item.id)
    await commit_changes(db)
    return success(request, (await request_payloads(db, [item], viewer))[0])
