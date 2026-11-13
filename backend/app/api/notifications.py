import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_context import AuthContext, require_auth
from app.database import get_db
from app.http import ApiProblem, success
from app.models import Notification, Profile, StudyGroup, utc_now
from app.services.buddy_connections import commit_changes, iso

router = APIRouter(prefix="/notifications", tags=["notifications"])
TITLES = {"buddy_request_received": "收到搭子邀请", "buddy_request_accepted": "搭子邀请已被接受",
          "buddy_request_rejected": "搭子邀请已被拒绝", "buddy_relation_removed": "搭子关系已解除",
          "group_join_requested": "收到小组加入申请", "group_join_approved": "小组申请已通过",
          "group_join_rejected": "小组申请已被拒绝", "group_member_removed": "你已被移出学习小组"}


async def notification_payloads(db: AsyncSession, items: list[Notification]):
    profiles = {p.user_id: p for p in await db.scalars(select(Profile).where(Profile.user_id.in_([n.actor_id for n in items if n.actor_id])))} if items else {}
    groups = {g.id: g for g in await db.scalars(select(StudyGroup).where(StudyGroup.id.in_([n.group_id for n in items if n.group_id])))} if items else {}
    def target(item):
        if item.kind.startswith("group_"):
            group = groups.get(item.group_id)
            if not group or group.archived_at or item.kind == "group_member_removed":
                return "/groups"
            return f"/groups/{group.id}" + ("?tab=requests" if item.kind == "group_join_requested" else "")
        tab = "incoming" if item.kind == "buddy_request_received" else "mine" if item.kind == "buddy_relation_removed" else "outgoing"
        return f"/buddies?tab={tab}"
    return [{
        "id": str(item.id), "kind": item.kind, "title": TITLES[item.kind],
        "actor": {"id": str(item.actor_id), "name": profiles[item.actor_id].display_name} if item.actor_id in profiles else None,
        "requestId": str(item.request_id) if item.request_id else None,
        "relationId": str(item.relation_id) if item.relation_id else None,
        "groupId": str(item.group_id) if item.group_id else None,
        "groupRequestId": str(item.group_request_id) if item.group_request_id else None,
        "groupEventId": str(item.group_event_id) if item.group_event_id else None,
        "groupName": groups[item.group_id].name if item.group_id in groups else None,
        "href": target(item),
        "createdAt": iso(item.created_at), "readAt": iso(item.read_at),
    } for item in items]


@router.get("")
async def list_notifications(request: Request, unread_only: bool = Query(False, alias="unreadOnly"),
                             page: int = Query(1, ge=1, le=10000), page_size: int = Query(12, alias="pageSize", ge=1, le=50),
                             auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    conditions = [Notification.user_id == auth.user.id]
    if unread_only:
        conditions.append(Notification.read_at.is_(None))
    unread = await db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == auth.user.id, Notification.read_at.is_(None)))
    total = await db.scalar(select(func.count()).select_from(Notification).where(*conditions))
    items = list(await db.scalars(select(Notification).where(*conditions)
                                 .order_by(Notification.created_at.desc(), Notification.id)
                                 .offset((page - 1) * page_size).limit(page_size)))
    return success(request, {"items": await notification_payloads(db, items), "total": total,
                             "unreadCount": unread, "page": page, "pageSize": page_size})


@router.get("/unread-count")
async def unread_count(request: Request, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    count = await db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == auth.user.id, Notification.read_at.is_(None)))
    return success(request, {"unreadCount": count})


@router.patch("/read-all")
async def read_all(request: Request, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    # One database statement marks only this user's rows visible to the statement.
    result = await db.execute(update(Notification).where(Notification.user_id == auth.user.id, Notification.read_at.is_(None)).values(read_at=utc_now()))
    await commit_changes(db)
    count = await db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == auth.user.id, Notification.read_at.is_(None)))
    return success(request, {"updatedCount": result.rowcount, "unreadCount": count})


@router.patch("/{notification_id}/read")
async def read_notification(notification_id: uuid.UUID, request: Request,
                             auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    item = await db.scalar(select(Notification).where(Notification.id == notification_id, Notification.user_id == auth.user.id).with_for_update())
    if not item:
        raise ApiProblem(404, "NOTIFICATION_NOT_FOUND", "通知不存在")
    if not item.read_at:
        item.read_at = utc_now()
        await commit_changes(db)
    return success(request, (await notification_payloads(db, [item]))[0])
