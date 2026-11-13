import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import case, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_context import AuthContext, require_auth
from app.database import get_db
from app.http import ApiProblem, success
from app.models import Checkin, GroupCheckinShare, GroupGoal, GroupJoinRequest, GroupMember, GroupMemberEvent, Profile, StudyGroup, User, utc_now
from app.services.group_notifications import add_group_notification, handoff_group_requests, mark_group_request_handled
from app.services.buddy_connections import commit_changes, flush_changes, iso
from app.services.groups import get_group, goal_payload, group_payloads, member_count, rankings, require_member, shared_query, statistics
from app.services.matching import CATEGORIES
from app.services.study_calendar import local_date, study_today

router = APIRouter(prefix="/groups", tags=["study groups"])


class GroupPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=50)
    category: str = Field(max_length=40)
    description: str = Field(min_length=1, max_length=500)
    max_members: int = Field(default=30, alias="maxMembers", ge=2, le=200, strict=True)
    requires_approval: bool = Field(default=False, alias="requiresApproval", strict=True)
    tags: list[str] = Field(default_factory=list, max_length=10)
    announcement: str = Field(default="", max_length=500)

    @field_validator("category")
    @classmethod
    def category_valid(cls, value):
        if value not in CATEGORIES:
            raise ValueError("请选择预设学习方向")
        return value

    @field_validator("tags")
    @classmethod
    def tags_valid(cls, values):
        result = []
        for value in values:
            if not 1 <= len(value.strip()) <= 32:
                raise ValueError("标签需为 1–32 字")
            if value.strip() not in result:
                result.append(value.strip())
        return result


class TransferPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    new_owner_id: uuid.UUID = Field(alias="newOwnerId")


class GroupGoalPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=120)
    start_date: date = Field(alias="startDate")
    end_date: date = Field(alias="endDate")
    target_minutes: int = Field(alias="targetMinutes", ge=1, le=525600, strict=True)

    @model_validator(mode="after")
    def dates_valid(self):
        days = (self.end_date - self.start_date).days + 1
        if not 1 <= days <= 366 or self.target_minutes > days * 1440:
            raise ValueError("目标周期需为 1–366 天，时长不能超过每天 24 小时")
        return self


@router.get("")
async def list_groups(request: Request, q: str = Query("", max_length=100), category: str | None = None,
                      mine: bool = False, page: int = Query(1, ge=1, le=10000), page_size: int = Query(12, alias="pageSize", ge=1, le=50),
                      auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    if category is not None and category not in CATEGORIES:
        raise ApiProblem(422, "VALIDATION_ERROR", "请选择预设方向")
    own = select(GroupMember.group_id).where(GroupMember.user_id == auth.user.id)
    conditions = [StudyGroup.archived_at.is_(None)]
    if mine:
        conditions.append(StudyGroup.id.in_(own))
    if category:
        conditions.append(StudyGroup.category == category)
    if q.strip():
        pattern = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        conditions.append(or_(StudyGroup.name.ilike(pattern, escape="\\"), StudyGroup.description.ilike(pattern, escape="\\")))
    total = await db.scalar(select(func.count()).select_from(StudyGroup).where(*conditions))
    joined_total = await db.scalar(select(func.count()).select_from(StudyGroup).where(StudyGroup.archived_at.is_(None), StudyGroup.id.in_(own)))
    groups = list(await db.scalars(select(StudyGroup).where(*conditions).order_by(StudyGroup.created_at.desc(), StudyGroup.id).offset((page - 1) * page_size).limit(page_size)))
    return success(request, {"items": await group_payloads(db, groups, auth.user.id), "total": total,
                             "page": page, "pageSize": page_size, "joinedTotal": joined_total})


@router.post("", status_code=201)
async def create_group(payload: GroupPayload, request: Request, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    if await db.scalar(select(StudyGroup.id).where(StudyGroup.owner_id == auth.user.id, StudyGroup.name == payload.name, StudyGroup.archived_at.is_(None))):
        raise ApiProblem(409, "GROUP_NAME_EXISTS", "你已有同名小组，请刷新列表查看或更换名称")
    group = StudyGroup(id=uuid.uuid4(), owner_id=auth.user.id, **payload.model_dump())
    db.add(group)
    await flush_changes(db)
    db.add(GroupMember(group_id=group.id, user_id=auth.user.id, role="owner"))
    await commit_changes(db)
    return success(request, (await group_payloads(db, [group], auth.user.id))[0])


@router.get("/{group_id}/preview")
async def preview(group_id: uuid.UUID, request: Request, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    group = await get_group(db, group_id)
    return success(request, (await group_payloads(db, [group], auth.user.id))[0])


@router.get("/{group_id}")
async def group_detail(group_id: uuid.UUID, request: Request, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    group = await get_group(db, group_id)
    member = await require_member(db, group, auth.user.id)
    return success(request, {**(await group_payloads(db, [group], auth.user.id))[0], "announcement": group.announcement,
                             "myJoinedAt": iso(member.joined_at), "statistics": await statistics(db, group),
                             "goal": await goal_payload(db, group_id, auth.user.id)})


@router.put("/{group_id}")
async def edit_group(group_id: uuid.UUID, payload: GroupPayload, request: Request,
                      auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    group = await get_group(db, group_id, write=True)
    await require_member(db, group, auth.user.id, owner=True)
    if payload.max_members < await member_count(db, group_id):
        raise ApiProblem(409, "GROUP_CAPACITY_TOO_SMALL", "人数上限不能小于现有成员数")
    for key, value in payload.model_dump().items():
        setattr(group, key, value)
    group.updated_at = utc_now()
    await commit_changes(db)
    return success(request, {**(await group_payloads(db, [group], auth.user.id))[0], "announcement": group.announcement})


@router.post("/{group_id}/join")
async def join_group(group_id: uuid.UUID, request: Request, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    group = await get_group(db, group_id, write=True)
    existing = await db.get(GroupMember, (group_id, auth.user.id))
    pending = await db.scalar(select(GroupJoinRequest).where(GroupJoinRequest.group_id == group_id, GroupJoinRequest.user_id == auth.user.id, GroupJoinRequest.status == "pending"))
    if existing or pending:
        return success(request, {"state": "joined" if existing else "pending", "requestId": str(pending.id) if pending else None})
    if await member_count(db, group_id) >= group.max_members:
        raise ApiProblem(409, "GROUP_FULL", "小组人数已满")
    if group.requires_approval:
        pending = GroupJoinRequest(id=uuid.uuid4(), group_id=group_id, user_id=auth.user.id)
        db.add(pending)
        await flush_changes(db)
        add_group_notification(db, recipient=group.owner_id, actor=auth.user.id, kind="group_join_requested", group_id=group_id, request_id=pending.id)
    else:
        db.add(GroupMember(group_id=group_id, user_id=auth.user.id, role="member"))
    await commit_changes(db)
    return JSONResponse(status_code=201, content=success(request, {"state": "pending" if pending else "joined", "requestId": str(pending.id) if pending else None}))


@router.get("/{group_id}/join-requests")
async def join_requests(group_id: uuid.UUID, request: Request, status: Literal["pending", "approved", "rejected", "cancelled"] = "pending",
                         page: int = Query(1, ge=1, le=10000), page_size: int = Query(12, alias="pageSize", ge=1, le=50),
                         auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    group = await get_group(db, group_id)
    await require_member(db, group, auth.user.id, owner=True)
    conditions = [GroupJoinRequest.group_id == group_id, GroupJoinRequest.status == status]
    total = await db.scalar(select(func.count()).select_from(GroupJoinRequest).where(*conditions))
    rows = (await db.execute(select(GroupJoinRequest, Profile.display_name).join(Profile, Profile.user_id == GroupJoinRequest.user_id)
                            .where(*conditions).order_by(GroupJoinRequest.created_at, GroupJoinRequest.id).offset((page - 1) * page_size).limit(page_size))).all()
    return success(request, {"items": [{"id": str(r.id), "userId": str(r.user_id), "name": name,
                                       "status": r.status, "createdAt": iso(r.created_at)} for r, name in rows],
                             "total": total, "page": page, "pageSize": page_size})


@router.post("/{group_id}/join-requests/{request_id}/{action}")
async def resolve_join(group_id: uuid.UUID, request_id: uuid.UUID, action: Literal["approve", "reject", "cancel"], request: Request,
                        auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    group = await get_group(db, group_id, write=True)
    if action != "cancel":
        await require_member(db, group, auth.user.id, owner=True)
    item = await db.scalar(select(GroupJoinRequest).where(GroupJoinRequest.id == request_id, GroupJoinRequest.group_id == group_id).with_for_update())
    if not item or (action == "cancel" and item.user_id != auth.user.id):
        raise ApiProblem(404, "JOIN_REQUEST_NOT_FOUND", "申请不存在")
    desired = {"approve": "approved", "reject": "rejected", "cancel": "cancelled"}[action]
    member = await db.get(GroupMember, (group_id, item.user_id))
    if item.status != "pending":
        if item.status == desired and (action != "approve" or (member and member.source_request_id == item.id)):
            return success(request, {"id": str(item.id), "status": item.status})
        raise ApiProblem(409, "JOIN_REQUEST_CLOSED", "申请已处理或对应成员已退出，请重新申请")
    if action == "approve":
        user = await db.get(User, item.user_id)
        if not user or not user.is_active or user.status != "active":
            raise ApiProblem(409, "APPLICANT_UNAVAILABLE", "申请账号当前不可用")
        if member:
            raise ApiProblem(409, "ALREADY_GROUP_MEMBER", "对方已经是小组成员")
        if await member_count(db, group_id) >= group.max_members:
            raise ApiProblem(409, "GROUP_FULL", "小组人数已满，申请仍保留待处理")
        db.add(GroupMember(group_id=group_id, user_id=item.user_id, role="member", source_request_id=item.id))
    item.status, item.resolved_at, item.resolved_by = desired, utc_now(), auth.user.id
    await mark_group_request_handled(db, item.id)
    if action in {"approve", "reject"}:
        add_group_notification(db, recipient=item.user_id, actor=auth.user.id,
                               kind="group_join_approved" if action == "approve" else "group_join_rejected",
                               group_id=group_id, request_id=item.id)
    await commit_changes(db)
    return success(request, {"id": str(item.id), "status": item.status})


@router.get("/{group_id}/members")
async def members(group_id: uuid.UUID, request: Request, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    group = await get_group(db, group_id)
    await require_member(db, group, auth.user.id)
    rows = (await db.execute(select(GroupMember, Profile.display_name).join(Profile, Profile.user_id == GroupMember.user_id)
                            .where(GroupMember.group_id == group_id).order_by(GroupMember.role.desc(), GroupMember.joined_at, GroupMember.user_id))).all()
    return success(request, {"items": [{"userId": str(m.user_id), "name": name, "avatar": name[:1], "role": m.role,
                                       "joinedAt": iso(m.joined_at), "isMe": m.user_id == auth.user.id} for m, name in rows]})


@router.post("/{group_id}/leave", status_code=204)
async def leave(group_id: uuid.UUID, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    group = await get_group(db, group_id, write=True)
    member = await db.get(GroupMember, (group_id, auth.user.id))
    if member and member.role == "owner":
        raise ApiProblem(409, "OWNER_MUST_TRANSFER", "组长请先转让或明确解散小组")
    if member:
        await db.delete(member)  # Composite FK retracts every share for this membership.
        await commit_changes(db)
    return Response(status_code=204)


@router.delete("/{group_id}/members/{user_id}", status_code=204)
async def remove_member(group_id: uuid.UUID, user_id: uuid.UUID, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    group = await get_group(db, group_id, write=True)
    await require_member(db, group, auth.user.id, owner=True)
    if user_id == group.owner_id:
        raise ApiProblem(409, "OWNER_MUST_TRANSFER", "不能移除组长，请先转让或解散")
    member = await db.get(GroupMember, (group_id, user_id))
    if member:
        event = GroupMemberEvent(id=uuid.uuid4(), group_id=group_id, user_id=user_id,
                                 actor_id=auth.user.id, membership_joined_at=member.joined_at)
        db.add(event)
        await flush_changes(db)
        add_group_notification(db, recipient=user_id, actor=auth.user.id, kind="group_member_removed",
                               group_id=group_id, event_id=event.id)
        await db.delete(member)
    await commit_changes(db)
    return Response(status_code=204)


@router.post("/{group_id}/transfer")
async def transfer(group_id: uuid.UUID, payload: TransferPayload, request: Request, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    group = await get_group(db, group_id, write=True)
    owner = await require_member(db, group, auth.user.id, owner=True)
    if payload.new_owner_id != auth.user.id:
        target = await db.get(GroupMember, (group_id, payload.new_owner_id))
        user = await db.get(User, payload.new_owner_id)
        if not target or not user or not user.is_active or user.status != "active":
            raise ApiProblem(404, "GROUP_MEMBER_NOT_FOUND", "请选择有效的现有成员")
        if await db.scalar(select(StudyGroup.id).where(StudyGroup.owner_id == payload.new_owner_id, StudyGroup.name == group.name, StudyGroup.archived_at.is_(None))):
            raise ApiProblem(409, "GROUP_NAME_EXISTS", "新组长已有同名小组，请先修改当前小组名称")
        owner.role = "member"
        await flush_changes(db)  # Release the partial single-owner index first.
        target.role, group.owner_id = "owner", target.user_id
        group.updated_at = utc_now()
        await handoff_group_requests(db, group_id, target.user_id)
        await commit_changes(db)
    return success(request, (await group_payloads(db, [group], auth.user.id))[0])


@router.delete("/{group_id}", status_code=204)
async def dissolve(group_id: uuid.UUID, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    group = await get_group(db, group_id, write=True, include_archived=True)
    if group.archived_at:
        if group.owner_id == auth.user.id:
            return Response(status_code=204)
        raise ApiProblem(404, "GROUP_NOT_FOUND", "小组不存在")
    await require_member(db, group, auth.user.id, owner=True)
    now = utc_now()
    group.archived_at = group.updated_at = now
    pending_ids = list(await db.scalars(select(GroupJoinRequest.id).where(GroupJoinRequest.group_id == group_id, GroupJoinRequest.status == "pending")))
    for pending_id in pending_ids:
        await mark_group_request_handled(db, pending_id)
    await db.execute(update(GroupJoinRequest).where(GroupJoinRequest.group_id == group_id, GroupJoinRequest.status == "pending")
                     .values(status="cancelled", resolved_at=now, resolved_by=auth.user.id))
    await db.execute(delete(GroupMember).where(GroupMember.group_id == group_id))
    await commit_changes(db)
    return Response(status_code=204)


@router.put("/{group_id}/goal")
async def set_goal(group_id: uuid.UUID, payload: GroupGoalPayload, request: Request, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    group = await get_group(db, group_id, write=True)
    await require_member(db, group, auth.user.id, owner=True)
    goal = await db.scalar(select(GroupGoal).where(GroupGoal.group_id == group_id))
    if goal:
        for key, value in payload.model_dump().items():
            setattr(goal, key, value)
        goal.updated_at = utc_now()
    else:
        db.add(GroupGoal(group_id=group_id, created_by=auth.user.id, **payload.model_dump()))
    await commit_changes(db)
    return success(request, await goal_payload(db, group_id, auth.user.id))


@router.get("/{group_id}/rankings")
async def get_rankings(group_id: uuid.UUID, request: Request, period: Literal["day", "week", "month", "days"] = "week",
                        auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    group = await get_group(db, group_id)
    await require_member(db, group, auth.user.id)
    return success(request, await rankings(db, group, auth.user.id, period))


@router.get("/{group_id}/checkins")
async def group_feed(group_id: uuid.UUID, request: Request, page: int = Query(1, ge=1, le=10000), page_size: int = Query(12, alias="pageSize", ge=1, le=50),
                      auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    group = await get_group(db, group_id)
    await require_member(db, group, auth.user.id)
    base = shared_query(db, group_id, study_today())
    total = await db.scalar(base.add_columns(func.count()))
    rows = (await db.execute(base.add_columns(
        Checkin.id, Checkin.study_date, Checkin.duration_minutes,
        case((GroupCheckinShare.share_content.is_(True), Checkin.content), else_=None),
        GroupCheckinShare.share_content, GroupCheckinShare.shared_at, Profile.user_id, Profile.display_name,
    ).join(Profile, Profile.user_id == GroupCheckinShare.user_id)
        .order_by(GroupCheckinShare.shared_at.desc(), Checkin.id).offset((page - 1) * page_size).limit(page_size))).all()
    return success(request, {"items": [{"checkinId": str(r[0]), "date": r[1].isoformat(), "duration": r[2],
                                       "content": r[3], "shareContent": r[4], "sharedAt": iso(r[5]),
                                       "user": {"id": str(r[6]), "name": r[7], "avatar": r[7][:1]}} for r in rows],
                             "total": total, "page": page, "pageSize": page_size})
