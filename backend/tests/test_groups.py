import asyncio
import uuid
from contextlib import AsyncExitStack
from datetime import date, datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import Checkin, GroupCheckinShare, GroupJoinRequest, GroupMember, StudyGroup
from app.services.study_calendar import local_date, period_bounds, study_today
from test_account_auth import client_for, login
from test_profiles_and_buddies import account


@pytest_asyncio.fixture
async def trio(app):
    async with AsyncExitStack() as stack:
        clients = [await stack.enter_async_context(client_for(app)) for _ in range(3)]
        ids = [await account(client, f"group_{i}") for i, client in enumerate(clients)]
        yield (*clients, *ids)


def payload(name="C++ 共学组", approval=True, capacity=3):
    return {"name": name, "category": "编程开发", "description": "一起学习 C++", "maxMembers": capacity,
            "requiresApproval": approval, "tags": ["C++"], "announcement": "MEMBERS_ONLY_ANNOUNCEMENT"}


async def create(a, **kwargs):
    response = await a.post("/api/v1/groups", json=payload(**kwargs))
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


async def join(a, b, group_id):
    response = await b.post(f"/api/v1/groups/{group_id}/join")
    assert response.status_code in (200, 201), response.text
    data = response.json()["data"]
    if data["state"] == "pending":
        accepted = await a.post(f"/api/v1/groups/{group_id}/join-requests/{data['requestId']}/approve")
        assert accepted.status_code == 200, accepted.text
    return data.get("requestId")


async def checkin(client, minutes, content="PRIVATE_CONTENT", day=None):
    response = await client.post("/api/v1/checkins", json={"date": (day or study_today()).isoformat(), "duration": minutes,
                                                         "content": content, "mood": "专注在线"})
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


async def share(client, record_id, group_id, content=False):
    return await client.put(f"/api/v1/checkins/{record_id}/groups/{group_id}", json={"shareContent": content})


async def count(app, model, *conditions):
    async with app.state.session_factory() as db:
        return await db.scalar(select(func.count()).select_from(model).where(*conditions))


@pytest.mark.asyncio
async def test_complete_three_account_group_flow_privacy_progress_and_exit(app, trio):
    a, b, c, a_id, b_id, _ = trio
    gid = await create(a)
    detail = await a.get(f"/api/v1/groups/{gid}")
    assert detail.status_code == 200 and detail.json()["data"]["myRole"] == "owner"
    assert (await c.get(f"/api/v1/groups/{gid}/preview")).status_code == 200
    public = (await c.get("/api/v1/groups?category=编程开发&q=C%2B%2B")).json()["data"]
    assert public["total"] == 1 and public["items"][0]["memberCount"] == 1
    assert "MEMBERS_ONLY" not in str(public) and "members" not in public["items"][0]
    pending_id = await join(a, b, gid)
    assert (await b.get(f"/api/v1/groups/{gid}")).json()["data"]["myRole"] == "member"

    r_a = await checkin(a, 180, "PUBLIC_CPP_A")
    r_b = await checkin(b, 120, "PUBLIC_CPP_B")
    private_b = await checkin(b, 600, "NEVER_SHARE_THIS")
    assert (await share(a, r_a, gid, True)).status_code == 200
    assert (await share(b, r_b, gid)).status_code == 200
    assert (await share(b, r_b, gid)).status_code == 200
    assert await count(app, GroupCheckinShare) == 2
    feed = (await b.get(f"/api/v1/groups/{gid}/checkins")).json()["data"]
    assert feed["total"] == 2 and "PUBLIC_CPP_A" in str(feed)
    assert "PUBLIC_CPP_B" not in str(feed) and "NEVER_SHARE_THIS" not in str(feed)
    assert all("mood" not in r and "goalId" not in r and "email" not in str(r) for r in feed["items"])
    assert (await share(b, r_b, gid, True)).status_code == 200
    assert "PUBLIC_CPP_B" in str((await b.get(f"/api/v1/groups/{gid}/checkins")).json())
    stats = (await a.get(f"/api/v1/groups/{gid}")).json()["data"]["statistics"]
    assert stats["totalMinutes"] == stats["weekMinutes"] == 300 and stats["todayMembers"] == 2
    ranking = (await b.get(f"/api/v1/groups/{gid}/rankings?period=week")).json()["data"]
    assert [r["userId"] for r in ranking["items"]] == [a_id, b_id]
    assert [r["minutes"] for r in ranking["items"]] == [180, 120]
    assert ranking["timezone"] == "Asia/Shanghai"
    today = study_today()
    target = {"title": "本周每人学习 C++ 10 小时", "startDate": today.isoformat(), "endDate": (today + timedelta(days=6)).isoformat(), "targetMinutes": 600}
    assert (await a.put(f"/api/v1/groups/{gid}/goal", json=target)).status_code == 200
    progress = (await b.get(f"/api/v1/groups/{gid}")).json()["data"]["goal"]
    assert progress["myMinutes"] == 120 and progress["progress"] == 20
    # The third account cannot read any member-only resource or another's private checkin.
    for path in ("", "/members", "/checkins", "/rankings", "/join-requests"):
        assert (await c.get(f"/api/v1/groups/{gid}{path}")).status_code == 404
    assert (await c.get(f"/api/v1/checkins/{r_b}")).status_code == 404
    assert (await share(c, private_b, gid, True)).status_code == 404
    assert (await b.put(f"/api/v1/groups/{gid}/goal", json=target)).status_code == 403
    assert (await b.put(f"/api/v1/groups/{gid}", json=payload())).status_code == 403
    assert (await b.delete(f"/api/v1/groups/{gid}/members/{a_id}")).status_code == 403
    async with client_for(app) as reopened:
        assert (await login(reopened, "match_group_1")).status_code == 200
        assert (await reopened.get(f"/api/v1/groups/{gid}")).json()["data"]["goal"]["myMinutes"] == 120
    assert (await b.post(f"/api/v1/groups/{gid}/leave")).status_code == 204
    assert (await b.get(f"/api/v1/groups/{gid}")).status_code == 404
    assert await count(app, GroupCheckinShare) == 1
    assert await count(app, Checkin) == 3
    assert (await a.get(f"/api/v1/groups/{gid}")).json()["data"]["statistics"]["totalMinutes"] == 180
    assert (await a.post(f"/api/v1/groups/{gid}/join-requests/{pending_id}/approve")).status_code == 409


@pytest.mark.asyncio
async def test_duplicate_application_roles_capacity_transfer_and_dissolve(app, trio):
    a, b, c, a_id, b_id, c_id = trio
    gid = await create(a, capacity=2)
    assert (await a.post("/api/v1/groups", json=payload(capacity=2))).status_code == 409
    first = (await b.post(f"/api/v1/groups/{gid}/join")).json()["data"]["requestId"]
    again = await b.post(f"/api/v1/groups/{gid}/join")
    assert again.status_code == 200 and again.json()["data"]["requestId"] == first
    other = (await c.post(f"/api/v1/groups/{gid}/join")).json()["data"]["requestId"]
    assert (await c.post(f"/api/v1/groups/{gid}/join-requests/{first}/approve")).status_code == 404
    assert (await c.post(f"/api/v1/groups/{gid}/join-requests/{first}/cancel")).status_code == 404
    assert (await a.post(f"/api/v1/groups/{gid}/join-requests/{first}/approve")).status_code == 200
    assert (await a.post(f"/api/v1/groups/{gid}/join-requests/{other}/approve")).status_code == 409
    assert (await a.post(f"/api/v1/groups/{gid}/leave")).status_code == 409
    assert (await a.delete(f"/api/v1/groups/{gid}/members/{a_id}")).status_code == 409
    assert (await a.put(f"/api/v1/groups/{gid}", json={**payload(capacity=2), "maxMembers": 1})).status_code == 422
    assert (await a.post(f"/api/v1/groups/{gid}/transfer", json={"newOwnerId": c_id})).status_code == 404
    assert (await a.post(f"/api/v1/groups/{gid}/transfer", json={"newOwnerId": b_id})).status_code == 200
    assert (await a.delete(f"/api/v1/groups/{gid}")).status_code == 403
    assert (await a.post(f"/api/v1/groups/{gid}/leave")).status_code == 204
    assert (await b.get(f"/api/v1/groups/{gid}")).json()["data"]["myRole"] == "owner"
    assert (await b.delete(f"/api/v1/groups/{gid}")).status_code == 204
    assert (await b.delete(f"/api/v1/groups/{gid}")).status_code == 204
    assert (await b.get(f"/api/v1/groups/{gid}")).status_code == 404
    assert (await c.get("/api/v1/groups")).json()["data"]["total"] == 0
    assert await count(app, GroupMember) == 0


@pytest.mark.asyncio
async def test_share_revocation_delete_and_removed_member_do_not_copy_private_data(app, trio):
    a, b, c, _, b_id, _ = trio
    gid = await create(a, approval=False)
    await join(a, b, gid)
    rid = await checkin(b, 80)
    assert (await share(a, rid, gid, True)).status_code == 404
    assert (await share(b, rid, gid, True)).status_code == 200
    assert (await b.get(f"/api/v1/checkins/{rid}/group-shares")).json()["data"]["items"][0]["groupId"] == gid
    assert (await b.delete(f"/api/v1/checkins/{rid}/groups/{gid}")).status_code == 204
    assert (await a.get(f"/api/v1/groups/{gid}/checkins")).json()["data"]["total"] == 0
    assert (await b.get(f"/api/v1/checkins/{rid}")).status_code == 200
    await share(b, rid, gid)
    assert (await a.delete(f"/api/v1/groups/{gid}/members/{b_id}")).status_code == 204
    assert await count(app, GroupCheckinShare) == 0
    assert (await b.get(f"/api/v1/groups/{gid}/rankings")).status_code == 404
    assert (await share(b, rid, gid)).status_code == 404
    await join(a, b, gid)
    await share(b, rid, gid)
    assert (await b.delete(f"/api/v1/checkins/{rid}")).status_code == 204
    assert await count(app, GroupCheckinShare) == 0
    assert (await a.get(f"/api/v1/groups/{gid}")).json()["data"]["statistics"]["totalMinutes"] == 0


@pytest.mark.asyncio
async def test_record_shared_to_two_groups_is_once_per_group_and_days_are_distinct(app, trio):
    a, b, c, _, b_id, c_id = trio
    g1, g2 = await create(a, approval=False), await create(a, name="第二小组", approval=False)
    await join(a, b, g1)
    await join(a, b, g2)
    await join(a, c, g1)
    r1, r2 = await checkin(b, 60), await checkin(b, 30)
    for group_id in (g1, g2):
        for record_id in (r1, r2):
            assert (await share(b, record_id, group_id)).status_code == 200
    assert await count(app, Checkin) == 2 and await count(app, GroupCheckinShare) == 4
    for period in ("day", "week", "month", "days"):
        data = (await a.get(f"/api/v1/groups/{g1}/rankings?period={period}")).json()["data"]
        assert data["items"][0]["userId"] == b_id and data["items"][0]["minutes"] == 90
        assert data["items"][0]["days"] == 1 and data["items"][0]["records"] == 2
        assert len(data["items"]) == 3 and data["items"][-1]["minutes"] == 0
    assert (await a.get(f"/api/v1/groups/{g1}")).json()["data"]["statistics"]["todayMembers"] == 1


@pytest.mark.asyncio
async def test_share_rules_limits_and_validation(app, trio):
    a, b, c, _, _, _ = trio
    gid = await create(a, approval=False)
    await join(a, b, gid)
    old = await checkin(b, 20, day=study_today() - timedelta(days=1))
    assert (await share(b, old, gid)).status_code == 422
    r1, r2 = await checkin(b, 1440), await checkin(b, 1)
    assert (await share(b, r1, gid)).status_code == 200
    assert (await share(b, r2, gid)).status_code == 409
    assert (await b.put(f"/api/v1/checkins/{r1}/groups/{gid}", json={"shareContent": "yes"})).status_code == 422
    assert (await b.put(f"/api/v1/checkins/{r1}/groups/{gid}", json={"shareContent": True, "userId": "fake"})).status_code == 422
    for change in ({"name": " "}, {"category": "bad"}, {"maxMembers": 201}, {"requiresApproval": "yes"}, {"ownerId": str(uuid.uuid4())}):
        assert (await a.post("/api/v1/groups", json={**payload(), **change})).status_code == 422
    assert (await a.get("/api/v1/groups?category=bad")).status_code == 422
    assert (await a.get(f"/api/v1/groups/{gid}/rankings?period=year")).status_code == 422
    async with client_for(app) as anonymous:
        assert (await anonymous.get("/api/v1/groups")).status_code == 401
        assert (await anonymous.post("/api/v1/groups", json=payload())).status_code == 401


@pytest.mark.asyncio
async def test_approval_rejection_cancellation_and_member_permissions(app, trio):
    a, b, c, _, _, _ = trio
    gid = await create(a)
    req = (await b.post(f"/api/v1/groups/{gid}/join")).json()["data"]["requestId"]
    assert (await b.post(f"/api/v1/groups/{gid}/join-requests/{req}/cancel")).status_code == 200
    assert (await a.post(f"/api/v1/groups/{gid}/join-requests/{req}/approve")).status_code == 409
    req = (await b.post(f"/api/v1/groups/{gid}/join")).json()["data"]["requestId"]
    assert (await a.post(f"/api/v1/groups/{gid}/join-requests/{req}/reject")).status_code == 200
    assert (await a.get(f"/api/v1/groups/{gid}/join-requests?status=rejected")).json()["data"]["total"] == 1
    assert (await b.get(f"/api/v1/groups/{gid}")).status_code == 404
    await join(a, b, gid)
    assert (await b.get(f"/api/v1/groups/{gid}/join-requests")).status_code == 403


@pytest.mark.asyncio
async def test_archive_retracts_shares_and_preserves_personal_checkins(app, trio):
    a, b, c, _, _, _ = trio
    gid = await create(a, approval=False)
    await join(a, b, gid)
    rid = await checkin(b, 90)
    await share(b, rid, gid, True)
    assert (await a.delete(f"/api/v1/groups/{gid}")).status_code == 204
    assert await count(app, GroupCheckinShare) == await count(app, GroupMember) == 0
    assert await count(app, Checkin) == 1
    assert (await b.get(f"/api/v1/checkins/{rid}")).status_code == 200
    assert (await b.get(f"/api/v1/groups/{gid}/checkins")).status_code == 404


def test_calendar_uses_beijing_midnight_week_month_and_leap_year():
    assert local_date(datetime(2026, 11, 12, 16, 1, tzinfo=timezone.utc)) == date(2026, 11, 13)
    assert period_bounds("week", date(2026, 11, 15), date(2026, 1, 1)) == (date(2026, 11, 9), date(2026, 11, 15))
    assert period_bounds("month", date(2024, 2, 28), date(2024, 1, 1)) == (date(2024, 2, 1), date(2024, 2, 29))


def postgres_only(app):
    if app.state.engine.dialect.name != "postgresql":
        pytest.skip("Group concurrency requires PostgreSQL row locks")


@pytest.mark.asyncio
async def test_concurrent_last_seat_and_repeated_join(app, trio):
    postgres_only(app)
    a, b, c, _, _, _ = trio
    gid = await create(a, approval=False, capacity=2)
    responses = await asyncio.gather(b.post(f"/api/v1/groups/{gid}/join"), c.post(f"/api/v1/groups/{gid}/join"))
    assert sorted(r.status_code for r in responses) == [201, 409]
    winner = b if responses[0].status_code == 201 else c
    repeated = await asyncio.gather(*(winner.post(f"/api/v1/groups/{gid}/join") for _ in range(6)))
    assert all(r.status_code == 200 for r in repeated)
    assert await count(app, GroupMember) == 2


@pytest.mark.asyncio
async def test_concurrent_approval_only_one_final_seat(app, trio):
    postgres_only(app)
    a, b, c, _, _, _ = trio
    gid = await create(a, capacity=2)
    ids = [(await client.post(f"/api/v1/groups/{gid}/join")).json()["data"]["requestId"] for client in (b, c)]
    responses = await asyncio.gather(*(a.post(f"/api/v1/groups/{gid}/join-requests/{rid}/approve") for rid in ids))
    assert sorted(r.status_code for r in responses) == [200, 409]
    assert await count(app, GroupMember) == 2
    assert await count(app, GroupJoinRequest, GroupJoinRequest.status == "pending") == 1


@pytest.mark.asyncio
async def test_concurrent_share_retry_and_membership_revocation(app, trio):
    postgres_only(app)
    a, b, c, _, b_id, _ = trio
    gid = await create(a, approval=False)
    await join(a, b, gid)
    rid = await checkin(b, 90)
    responses = await asyncio.gather(*(share(b, rid, gid, True) for _ in range(6)))
    assert all(r.status_code == 200 for r in responses)
    assert await count(app, GroupCheckinShare) == 1
    race = await asyncio.gather(share(b, rid, gid), a.delete(f"/api/v1/groups/{gid}/members/{b_id}"))
    assert race[0].status_code in (200, 404) and race[1].status_code == 204
    assert await count(app, GroupCheckinShare) == 0
    assert await count(app, Checkin) == 1


@pytest.mark.asyncio
async def test_real_date_range_aggregates_and_beijing_join_boundary(app, trio, monkeypatch):
    a, b, c, _, b_id, _ = trio
    fixed = date(2026, 3, 2)
    for path in ("app.api.checkins.study_today", "app.api.group_shares.study_today", "app.services.groups.study_today"):
        monkeypatch.setattr(path, lambda: fixed)
    gid = await create(a, approval=False)
    await join(a, b, gid)
    async with app.state.session_factory() as db:
        group = await db.get(StudyGroup, uuid.UUID(gid))
        group.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for member in await db.scalars(select(GroupMember).where(GroupMember.group_id == uuid.UUID(gid))):
            member.joined_at = group.created_at
        await db.commit()
    for day, minutes in ((date(2026, 2, 28), 30), (date(2026, 3, 1), 60), (fixed, 120)):
        rid = await checkin(b, minutes, day=day)
        assert (await share(b, rid, gid)).status_code == 200
    for period, minutes, days in (("day", 120, 1), ("week", 120, 1), ("month", 180, 2), ("days", 210, 3)):
        result = (await a.get(f"/api/v1/groups/{gid}/rankings?period={period}")).json()["data"]
        assert result["items"][0]["minutes"] == minutes and result["items"][0]["days"] == days
    async with app.state.session_factory() as db:
        member = await db.get(GroupMember, (uuid.UUID(gid), uuid.UUID(b_id)))
        member.joined_at = datetime(2026, 3, 1, 16, 30, tzinfo=timezone.utc)  # Mar 2 in Beijing.
        await db.commit()
    assert (await a.get(f"/api/v1/groups/{gid}/rankings?period=month")).json()["data"]["items"][0]["minutes"] == 120


@pytest.mark.asyncio
async def test_capacity_cannot_shrink_below_members_and_goal_input_is_validated(app, trio):
    a, b, c, _, _, _ = trio
    gid = await create(a, approval=False, capacity=4)
    await join(a, b, gid)
    await join(a, c, gid)
    assert (await a.put(f"/api/v1/groups/{gid}", json=payload(approval=False, capacity=2))).status_code == 409
    target = {"title": "目标", "startDate": "2026-11-13", "endDate": "2026-11-13", "targetMinutes": 60}
    for patch in ({"title": " "}, {"endDate": "2026-11-12"}, {"targetMinutes": 1441}, {"userId": "x"}):
        assert (await a.put(f"/api/v1/groups/{gid}/goal", json={**target, **patch})).status_code == 422


@pytest.mark.asyncio
async def test_group_and_owner_creation_are_atomic(app, trio, monkeypatch):
    a, _, _, _, _, _ = trio
    async def fail(_db):
        raise RuntimeError("injected creation failure")
    monkeypatch.setattr("app.api.groups.commit_changes", fail)
    with pytest.raises(RuntimeError, match="injected creation failure"):
        await a.post("/api/v1/groups", json=payload())
    assert await count(app, StudyGroup) == await count(app, GroupMember) == 0


@pytest.mark.asyncio
async def test_database_sharing_foreign_keys_enforce_checkin_owner_and_membership(app, trio):
    a, b, c, a_id, b_id, c_id = trio
    gid = await create(a, approval=False)
    rid = await checkin(b, 60)
    async with app.state.session_factory() as db:
        db.add(GroupCheckinShare(group_id=uuid.UUID(gid), checkin_id=uuid.UUID(rid), user_id=uuid.UUID(a_id)))
        with pytest.raises(IntegrityError):
            await db.flush()
        await db.rollback()
        db.add(GroupCheckinShare(group_id=uuid.UUID(gid), checkin_id=uuid.UUID(rid), user_id=uuid.UUID(b_id)))
        with pytest.raises(IntegrityError):
            await db.flush()
        await db.rollback()


@pytest.mark.asyncio
async def test_concurrent_share_daily_cap_is_enforced(app, trio):
    postgres_only(app)
    a, b, _, _, _, _ = trio
    gid = await create(a, approval=False)
    await join(a, b, gid)
    r1, r2 = await checkin(b, 900), await checkin(b, 900)
    responses = await asyncio.gather(share(b, r1, gid), share(b, r2, gid))
    assert sorted(r.status_code for r in responses) == [200, 409]
    assert await count(app, GroupCheckinShare) == 1


@pytest.mark.asyncio
async def test_concurrent_application_retries_and_cancel_approval_race(app, trio):
    postgres_only(app)
    a, b, _, _, _, _ = trio
    gid = await create(a)
    responses = await asyncio.gather(*(b.post(f"/api/v1/groups/{gid}/join") for _ in range(6)))
    assert sorted(r.status_code for r in responses) == [200] * 5 + [201]
    ids = {r.json()["data"]["requestId"] for r in responses}
    assert len(ids) == 1
    req = ids.pop()
    responses = await asyncio.gather(a.post(f"/api/v1/groups/{gid}/join-requests/{req}/approve"),
                                     b.post(f"/api/v1/groups/{gid}/join-requests/{req}/cancel"))
    assert sorted(r.status_code for r in responses) == [200, 409]
    async with app.state.session_factory() as db:
        record = await db.get(GroupJoinRequest, uuid.UUID(req))
        assert await count(app, GroupMember) == (2 if record.status == "approved" else 1)
