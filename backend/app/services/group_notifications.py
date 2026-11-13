"""Only business transactions create notices; no client notification-write endpoint."""
from sqlalchemy import select, update
from app.models import GroupJoinRequest, Notification, utc_now


def add_group_notification(db, *, recipient, actor, kind, group_id, request_id=None, event_id=None):
    source = event_id if kind == "group_member_removed" else request_id
    if source is None:
        raise ValueError("Group notifications must have a persistent business source")
    db.add(Notification(user_id=recipient, actor_id=actor, kind=kind, group_id=group_id,
                        group_request_id=request_id, group_event_id=event_id,
                        event_key=f"{kind}:{source}:{recipient}"))


async def mark_group_request_handled(db, request_id):
    await db.execute(update(Notification).where(Notification.group_request_id == request_id,
        Notification.kind == "group_join_requested", Notification.read_at.is_(None)).values(read_at=utc_now()))


async def handoff_group_requests(db, group_id, new_owner_id):
    requests = list(await db.scalars(select(GroupJoinRequest).where(
        GroupJoinRequest.group_id == group_id, GroupJoinRequest.status == "pending")))
    for item in requests:
        await mark_group_request_handled(db, item.id)
        key = f"group_join_requested:{item.id}:{new_owner_id}"
        # Ownership can move back to a prior owner without producing duplicates.
        existing = await db.scalar(select(Notification).where(Notification.event_key == key))
        if existing:
            existing.read_at = None
        else:
            add_group_notification(db, recipient=new_owner_id, actor=item.user_id, kind="group_join_requested",
                                   group_id=group_id, request_id=item.id)
