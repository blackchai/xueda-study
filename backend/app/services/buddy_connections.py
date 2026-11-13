"""Shared locking and projections for real buddy connections; no private goals or checkins."""
import uuid

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.profiles import public_profile
from app.http import ApiProblem
from app.models import BuddyRelation, BuddyRequest, Notification, Profile, User, as_utc, utc_now


def iso(value):
    return as_utc(value).isoformat() if value else None


def pair_ids(a: uuid.UUID, b: uuid.UUID) -> tuple[uuid.UUID, uuid.UUID]:
    return tuple(sorted((a, b)))


async def lock_participants(db: AsyncSession, a: uuid.UUID, b: uuid.UUID) -> dict[uuid.UUID, User]:
    # All mutations acquire the same user rows in global UUID order, then the
    # request/relation row. This serializes reverse invites and per-sender quotas
    # across workers and avoids cycles between different pairs sharing a user.
    users = (await db.scalars(
        select(User).where(User.id.in_(pair_ids(a, b))).order_by(User.id)
        .with_for_update().execution_options(populate_existing=True)
    )).all()
    return {user.id: user for user in users}


def is_active(user: User | None) -> bool:
    return bool(user and user.is_active and user.status == "active")


async def active_relation(db: AsyncSession, a: uuid.UUID, b: uuid.UUID):
    low, high = pair_ids(a, b)
    return await db.scalar(select(BuddyRelation).where(
        BuddyRelation.user_low_id == low, BuddyRelation.user_high_id == high,
        BuddyRelation.ended_at.is_(None),
    ))


async def connection_states(db: AsyncSession, viewer: uuid.UUID, peers: list[uuid.UUID]) -> dict:
    states = {}
    if not peers:
        return states
    relations = await db.scalars(select(BuddyRelation).where(
        BuddyRelation.ended_at.is_(None),
        or_((BuddyRelation.user_low_id == viewer) & BuddyRelation.user_high_id.in_(peers),
            (BuddyRelation.user_high_id == viewer) & BuddyRelation.user_low_id.in_(peers)),
    ))
    requests = await db.scalars(select(BuddyRequest).where(
        BuddyRequest.status == "pending",
        or_((BuddyRequest.sender_id == viewer) & BuddyRequest.recipient_id.in_(peers),
            (BuddyRequest.recipient_id == viewer) & BuddyRequest.sender_id.in_(peers)),
    ))
    for item in requests:
        outgoing = item.sender_id == viewer
        peer = item.recipient_id if outgoing else item.sender_id
        states[peer] = {"status": "outgoing_pending" if outgoing else "incoming_pending", "requestId": str(item.id)}
    for relation in relations:
        peer = relation.user_high_id if relation.user_low_id == viewer else relation.user_low_id
        states[peer] = {"status": "connected", "relationId": str(relation.id)}
    return states


async def load_profiles(db: AsyncSession, ids: list[uuid.UUID]) -> dict[uuid.UUID, Profile]:
    if not ids:
        return {}
    return {p.user_id: p for p in await db.scalars(
        select(Profile).where(Profile.user_id.in_(ids)).options(selectinload(Profile.time_slots))
    )}


def peer_payload(profile: Profile | None, user_id: uuid.UUID, *, shared: bool) -> dict:
    if profile and shared:
        return {**public_profile(profile), "profileVisible": True}
    return {
        "id": str(user_id), "name": profile.display_name if profile else "已不可用的用户",
        "avatar": profile.display_name[:1] if profile else "学", "categories": [], "tags": [],
        "styles": [], "stage": None, "timezone": "Asia/Shanghai", "timeSlots": [],
        "profileVisible": False, "allowInvites": False,
    }


async def request_payloads(db: AsyncSession, items: list[BuddyRequest], viewer: uuid.UUID) -> list[dict]:
    peers = [r.recipient_id if r.sender_id == viewer else r.sender_id for r in items]
    profiles = await load_profiles(db, peers)
    connections = await connection_states(db, viewer, peers)
    result = []
    for item, peer in zip(items, peers):
        profile = profiles.get(peer)
        shared = bool(profile and (profile.matching_enabled or item.status == "pending"
                                  or connections.get(peer, {}).get("status") == "connected"))
        result.append({
            "id": str(item.id), "senderId": str(item.sender_id), "recipientId": str(item.recipient_id),
            "direction": "outgoing" if item.sender_id == viewer else "incoming",
            "message": item.message, "status": item.status,
            "createdAt": iso(item.created_at), "updatedAt": iso(item.updated_at),
            "resolvedAt": iso(item.resolved_at),
            "peer": peer_payload(profile, peer, shared=shared),
            "connection": connections.get(peer, {"status": "none"}),
        })
    return result


async def relation_payloads(db: AsyncSession, items: list[BuddyRelation], viewer: uuid.UUID) -> list[dict]:
    peers = [r.user_high_id if r.user_low_id == viewer else r.user_low_id for r in items]
    profiles = await load_profiles(db, peers)
    return [{
        "id": str(item.id), "createdAt": iso(item.created_at),
        "peer": peer_payload(profiles.get(peer), peer, shared=True),
    } for item, peer in zip(items, peers)]


def add_notification(db: AsyncSession, *, recipient: uuid.UUID, actor: uuid.UUID,
                     kind: str, request_id: uuid.UUID | None = None, relation_id: uuid.UUID | None = None):
    entity = relation_id if kind == "buddy_relation_removed" else request_id
    db.add(Notification(
        user_id=recipient, actor_id=actor, kind=kind, request_id=request_id, relation_id=relation_id,
        event_key=f"{kind}:{entity}:{recipient}",
    ))


async def mark_request_handled(db: AsyncSession, request_id: uuid.UUID):
    await db.execute(update(Notification).where(
        Notification.request_id == request_id, Notification.kind == "buddy_request_received",
        Notification.read_at.is_(None),
    ).values(read_at=utc_now()))


async def commit_changes(db: AsyncSession):
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ApiProblem(409, "BUDDY_STATE_CONFLICT", "状态已变化，请刷新后重试") from None


async def flush_changes(db: AsyncSession):
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise ApiProblem(409, "BUDDY_STATE_CONFLICT", "状态已变化，请刷新后重试") from None
