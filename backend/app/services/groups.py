"""Membership authorization, consent-based aggregates and safe group projections."""
from datetime import timedelta

from sqlalchemy import Date, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.http import ApiProblem
from app.models import Checkin, GroupCheckinShare, GroupGoal, GroupJoinRequest, GroupMember, Profile, StudyGroup, User
from app.services.buddy_connections import iso
from app.services.study_calendar import STUDY_TIMEZONE, local_date, period_bounds, study_today


async def get_group(db: AsyncSession, group_id, *, write=False, include_archived=False):
    query = select(StudyGroup).where(StudyGroup.id == group_id)
    if not include_archived:
        query = query.where(StudyGroup.archived_at.is_(None))
    # Read locks keep membership revocations from racing a private response.
    group = await db.scalar(query.with_for_update(read=not write).execution_options(populate_existing=True))
    if not group:
        raise ApiProblem(404, "GROUP_NOT_FOUND", "小组不存在或已解散")
    return group


async def require_member(db: AsyncSession, group: StudyGroup, user_id, *, owner=False):
    member = await db.get(GroupMember, (group.id, user_id))
    if not member:
        raise ApiProblem(404, "GROUP_NOT_FOUND", "小组不存在或你尚未加入")
    if owner and (member.role != "owner" or group.owner_id != user_id):
        raise ApiProblem(403, "GROUP_OWNER_REQUIRED", "仅组长可以进行此操作")
    return member


async def member_count(db: AsyncSession, group_id):
    return await db.scalar(select(func.count()).select_from(GroupMember).where(GroupMember.group_id == group_id))


async def group_payloads(db: AsyncSession, groups: list[StudyGroup], viewer) -> list[dict]:
    if not groups:
        return []
    ids = [g.id for g in groups]
    counts = dict((await db.execute(select(GroupMember.group_id, func.count()).where(GroupMember.group_id.in_(ids)).group_by(GroupMember.group_id))).all())
    memberships = {m.group_id: m for m in await db.scalars(select(GroupMember).where(GroupMember.group_id.in_(ids), GroupMember.user_id == viewer))}
    names = dict((await db.execute(select(Profile.user_id, Profile.display_name).where(Profile.user_id.in_([g.owner_id for g in groups])))).all())
    own_requests = {}
    for item in await db.scalars(select(GroupJoinRequest).where(GroupJoinRequest.group_id.in_(ids), GroupJoinRequest.user_id == viewer).order_by(GroupJoinRequest.created_at.desc(), GroupJoinRequest.id)):
        own_requests.setdefault(item.group_id, item)
    result = []
    for group in groups:
        member, pending = memberships.get(group.id), own_requests.get(group.id)
        result.append({
            "id": str(group.id), "name": group.name, "category": group.category,
            "description": group.description, "tags": group.tags, "memberCount": counts.get(group.id, 0),
            "maxMembers": group.max_members, "requiresApproval": group.requires_approval,
            "ownerName": names.get(group.owner_id, "学习伙伴"), "myRole": member.role if member else None,
            "isJoined": member is not None,
            "joinRequest": {"id": str(pending.id), "status": pending.status} if pending and not member else None,
            "createdAt": iso(group.created_at),
        })
    return result


def shared_query(db: AsyncSession, group_id, today):
    joined_date = cast(func.timezone(STUDY_TIMEZONE, GroupMember.joined_at), Date) if db.bind.dialect.name == "postgresql" else func.date(GroupMember.joined_at, "+8 hours")
    return (select().select_from(GroupCheckinShare)
            .join(Checkin, (Checkin.id == GroupCheckinShare.checkin_id) & (Checkin.user_id == GroupCheckinShare.user_id))
            .join(GroupMember, (GroupMember.group_id == GroupCheckinShare.group_id) & (GroupMember.user_id == GroupCheckinShare.user_id))
            .join(User, User.id == GroupMember.user_id)
            .where(GroupCheckinShare.group_id == group_id, User.is_active.is_(True), User.status == "active",
                   Checkin.study_date <= today, Checkin.study_date >= joined_date))


async def statistics(db: AsyncSession, group: StudyGroup):
    today = study_today()
    week_start, week_end = period_bounds("week", today, local_date(group.created_at))
    base = shared_query(db, group.id, today)
    row = (await db.execute(base.add_columns(
        func.coalesce(func.sum(Checkin.duration_minutes), 0),
        func.count(func.distinct(case((Checkin.study_date == today, GroupCheckinShare.user_id), else_=None))),
        func.coalesce(func.sum(case((Checkin.study_date >= week_start, Checkin.duration_minutes), else_=0)), 0),
        func.count(func.distinct(case((Checkin.study_date >= week_start, GroupCheckinShare.user_id), else_=None))),
    ))).one()
    by_day = {r[0]: r for r in (await db.execute(base.add_columns(
        Checkin.study_date, func.sum(Checkin.duration_minutes), func.count(func.distinct(GroupCheckinShare.user_id)), func.count(),
    ).where(Checkin.study_date >= week_start).group_by(Checkin.study_date))).all()}
    days = []
    for index in range(7):
        current = week_start + timedelta(days=index)
        item = by_day.get(current)
        days.append({"date": current.isoformat(), "minutes": int(item[1]) if item else 0,
                     "memberCount": item[2] if item else 0, "recordCount": item[3] if item else 0})
    return {"todayMembers": row[1], "totalMinutes": int(row[0]), "weekMinutes": int(row[2]),
            "weekMembers": row[3], "weekStart": week_start.isoformat(), "weekEnd": week_end.isoformat(),
            "weekDays": days, "asOfDate": today.isoformat(), "timezone": STUDY_TIMEZONE}


async def goal_payload(db: AsyncSession, group_id, viewer):
    goal = await db.scalar(select(GroupGoal).where(GroupGoal.group_id == group_id))
    if not goal:
        return None
    row = (await db.execute(shared_query(db, group_id, study_today()).add_columns(
        func.coalesce(func.sum(Checkin.duration_minutes), 0), func.count(func.distinct(Checkin.study_date)),
    ).where(GroupCheckinShare.user_id == viewer, Checkin.study_date >= goal.start_date, Checkin.study_date <= goal.end_date))).one()
    minutes = int(row[0])
    return {"id": str(goal.id), "title": goal.title, "startDate": goal.start_date.isoformat(),
            "endDate": goal.end_date.isoformat(), "targetMinutes": goal.target_minutes,
            "myMinutes": minutes, "myDays": row[1], "progress": min(100, round(minutes / goal.target_minutes * 100, 1)),
            "updatedAt": iso(goal.updated_at)}


async def rankings(db: AsyncSession, group: StudyGroup, viewer, period: str):
    today = study_today()
    start, end = period_bounds(period, today, local_date(group.created_at))
    aggregate = shared_query(db, group.id, today).add_columns(
        GroupCheckinShare.user_id.label("user_id"), func.sum(Checkin.duration_minutes).label("minutes"),
        func.count(func.distinct(Checkin.study_date)).label("days"), func.count().label("records"),
    ).where(Checkin.study_date >= start, Checkin.study_date <= end).group_by(GroupCheckinShare.user_id).subquery()
    minutes, days = func.coalesce(aggregate.c.minutes, 0), func.coalesce(aggregate.c.days, 0)
    query = (select(GroupMember.user_id, Profile.display_name, GroupMember.role, minutes, days, func.coalesce(aggregate.c.records, 0))
             .select_from(GroupMember).join(Profile, Profile.user_id == GroupMember.user_id).join(User, User.id == GroupMember.user_id)
             .outerjoin(aggregate, aggregate.c.user_id == GroupMember.user_id)
             .where(GroupMember.group_id == group.id, User.is_active.is_(True), User.status == "active"))
    order = [days.desc(), minutes.desc()] if period == "days" else [minutes.desc(), days.desc()]
    items = [{"rank": i + 1, "userId": str(r[0]), "name": r[1], "avatar": r[1][:1], "role": r[2],
              "minutes": int(r[3]), "days": r[4], "records": r[5], "isMe": r[0] == viewer}
             for i, r in enumerate((await db.execute(query.order_by(*order, GroupMember.user_id))).all())]
    return {"items": items, "period": period, "startDate": start.isoformat(), "endDate": end.isoformat(),
            "asOfDate": today.isoformat(), "timezone": STUDY_TIMEZONE}
