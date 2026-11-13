import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_context import AuthContext, require_auth
from app.database import get_db
from app.http import ApiProblem, success
from app.models import Checkin, GroupCheckinShare, GroupMember, StudyGroup
from app.services.buddy_connections import commit_changes, iso
from app.services.groups import get_group, require_member
from app.services.study_calendar import local_date, study_today

router = APIRouter(prefix="/checkins", tags=["group checkin sharing"])


class SharePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    share_content: bool = Field(default=False, alias="shareContent", strict=True)


async def owned_checkin(db, checkin_id, viewer, *, lock=False):
    query = select(Checkin).where(Checkin.id == checkin_id, Checkin.user_id == viewer)
    if lock:
        query = query.with_for_update()
    item = await db.scalar(query)
    if not item:
        raise ApiProblem(404, "CHECKIN_NOT_FOUND", "打卡记录不存在")
    return item


@router.get("/{checkin_id}/group-shares")
async def my_shares(checkin_id: uuid.UUID, request: Request, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    await owned_checkin(db, checkin_id, auth.user.id)
    rows = (await db.execute(select(GroupCheckinShare, StudyGroup.name).join(StudyGroup, StudyGroup.id == GroupCheckinShare.group_id)
                            .join(GroupMember, (GroupMember.group_id == GroupCheckinShare.group_id) & (GroupMember.user_id == auth.user.id))
                            .where(GroupCheckinShare.checkin_id == checkin_id, GroupCheckinShare.user_id == auth.user.id, StudyGroup.archived_at.is_(None)))).all()
    return success(request, {"items": [{"groupId": str(s.group_id), "groupName": name, "shareContent": s.share_content, "sharedAt": iso(s.shared_at)} for s, name in rows]})


@router.put("/{checkin_id}/groups/{group_id}")
async def share_checkin(checkin_id: uuid.UUID, group_id: uuid.UUID, payload: SharePayload, request: Request,
                        auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    group = await get_group(db, group_id, write=True)
    member = await require_member(db, group, auth.user.id)
    checkin = await owned_checkin(db, checkin_id, auth.user.id, lock=True)
    if checkin.study_date < local_date(member.joined_at) or checkin.study_date > study_today():
        raise ApiProblem(422, "CHECKIN_OUTSIDE_MEMBERSHIP", "只能分享本次入组当地日期起、且不晚于今天的打卡")
    already = await db.get(GroupCheckinShare, (group_id, checkin_id))
    day_minutes = await db.scalar(select(func.coalesce(func.sum(Checkin.duration_minutes), 0)).select_from(GroupCheckinShare)
                                  .join(Checkin, Checkin.id == GroupCheckinShare.checkin_id)
                                  .where(GroupCheckinShare.group_id == group_id, GroupCheckinShare.user_id == auth.user.id,
                                         Checkin.study_date == checkin.study_date, Checkin.id != checkin_id))
    if day_minutes + checkin.duration_minutes > 1440:
        raise ApiProblem(409, "GROUP_DAILY_DURATION_EXCEEDED", "同一成员每天分享到本组的时长不能超过 24 小时")
    if already:
        already.share_content = payload.share_content
    else:
        already = GroupCheckinShare(group_id=group_id, checkin_id=checkin_id, user_id=auth.user.id, share_content=payload.share_content)
        db.add(already)
    await commit_changes(db)
    return success(request, {"groupId": str(group_id), "checkinId": str(checkin_id), "shareContent": already.share_content, "sharedAt": iso(already.shared_at)})


@router.delete("/{checkin_id}/groups/{group_id}", status_code=204)
async def unshare_checkin(checkin_id: uuid.UUID, group_id: uuid.UUID, auth: AuthContext = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    group = await get_group(db, group_id, write=True)
    await require_member(db, group, auth.user.id)
    await owned_checkin(db, checkin_id, auth.user.id)
    await db.execute(delete(GroupCheckinShare).where(GroupCheckinShare.group_id == group_id, GroupCheckinShare.checkin_id == checkin_id, GroupCheckinShare.user_id == auth.user.id))
    await commit_changes(db)
    return Response(status_code=204)
