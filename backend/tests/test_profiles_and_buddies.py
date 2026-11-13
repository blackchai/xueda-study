import json
import uuid
from datetime import date

import pytest
from sqlalchemy import select

from app.models import Profile, ProfileTimeSlot, User
from test_account_auth import client_for, goal_payload, login, register


def profile_payload(name="学习者", category="编程开发", tag="C++", start="19:00", end="22:00", enabled=True):
    return {
        "name": name, "school": "PRIVATE_SCHOOL", "major": "PRIVATE_MAJOR", "bio": "PRIVATE_BIO",
        "categories": [category], "tags": [tag], "styles": ["共同讨论"], "stage": "强化",
        "timeSlots": [{"day": 1, "start": start, "end": end}],
        "dailyTargetMinutes": 180, "publicProfile": enabled, "timezone": "Asia/Shanghai",
    }


async def account(client, suffix):
    response = await register(client, f"match_{suffix}", f"match_{suffix}@example.com")
    assert response.status_code == 201
    assert (await login(client, f"match_{suffix}")).status_code == 200
    return response.json()["data"]["userId"]


async def save(client, payload):
    response = await client.put("/api/v1/profiles/me", json=payload)
    assert response.status_code == 200, response.text
    return response.json()["data"]


@pytest.mark.asyncio
async def test_three_real_accounts_ranking_updates_optin_and_persistence(app):
    async with client_for(app) as a, client_for(app) as b, client_for(app) as c:
        a_id, b_id, c_id = await account(a, "a"), await account(b, "b"), await account(c, "c")
        for client in (a, b, c):
            own = (await client.get("/api/v1/profiles/me")).json()["data"]
            assert own["publicProfile"] is False
            assert own["timeSlots"] == []
        assert (await a.get("/api/v1/buddies/recommendations")).json()["data"]["total"] == 0

        await save(a, profile_payload("A"))
        b_profile = profile_payload("B", start="19:30", end="22:30")
        await save(b, b_profile)
        await save(c, profile_payload("C", "考研", "考研英语", "08:00", "11:00"))
        data = (await a.get("/api/v1/buddies/recommendations")).json()["data"]
        assert [p["id"] for p in data["items"]] == [b_id, c_id]
        assert [p["score"] for p in data["items"]] == [94, 25]
        assert all(p["id"] != a_id for p in data["items"])
        assert data["items"][0]["overlapMinutes"] == 150

        # B changes their actual database availability; A's next query must change.
        b_profile["timeSlots"] = [{"day": 1, "start": "08:00", "end": "11:00"}]
        await save(b, b_profile)
        updated = (await a.get("/api/v1/buddies/recommendations")).json()["data"]["items"][0]
        assert updated["id"] == b_id and updated["score"] == 65
        assert updated["dimensions"]["time"] == 0

        # Removing opt-in takes effect on every subsequent query; no cached public copy.
        b_profile["publicProfile"] = False
        await save(b, b_profile)
        assert [p["id"] for p in (await a.get("/api/v1/buddies/recommendations")).json()["data"]["items"]] == [c_id]
        # Disabled accounts are never candidates, even with an opted-in profile.
        async with app.state.session_factory() as db:
            user_c = await db.get(User, uuid.UUID(c_id))
            user_c.is_active = False
            await db.commit()
        assert (await a.get("/api/v1/buddies/recommendations")).json()["data"]["total"] == 0

    async with client_for(app) as reopened:
        assert (await login(reopened, "match_b")).status_code == 200
        saved = (await reopened.get("/api/v1/profiles/me")).json()["data"]
        assert saved["id"] == b_id and saved["publicProfile"] is False
        assert saved["timeSlots"][0]["start"] == "08:00"
    async with app.state.session_factory() as db:
        profiles = (await db.scalars(select(Profile))).all()
        slots = (await db.scalars(select(ProfileTimeSlot))).all()
        assert len(profiles) == 3 and len(slots) == 3


@pytest.mark.asyncio
async def test_private_records_and_profile_ownership_are_not_exposed(app):
    async with client_for(app) as a, client_for(app) as b, client_for(app) as anonymous:
        a_id, b_id = await account(a, "owner"), await account(b, "viewer")
        private = profile_payload("公开昵称")
        await save(a, private)
        goal = await a.post("/api/v1/goals", json=goal_payload("PRIVATE_GOAL"))
        assert goal.status_code == 201
        checkin = await a.post("/api/v1/checkins", json={
            "date": date.today().isoformat(), "duration": 60, "content": "PRIVATE_CHECKIN",
            "mood": "专注在线", "goalId": goal.json()["data"]["id"],
        })
        assert checkin.status_code == 201
        result = (await b.get("/api/v1/buddies/recommendations")).json()["data"]["items"][0]
        assert set(result) == {"id", "name", "avatar", "categories", "tags", "styles", "stage", "timezone", "timeSlots", "score", "dimensions", "reasons", "caveats", "overlapMinutes", "allowInvites", "connection"}
        text = json.dumps(result)
        for secret in ("PRIVATE", "example.com", "email", "password", "school", "major", "bio", "checkins", "weeklyHours", "streakDays"):
            assert secret not in text
        assert (await b.get("/api/v1/goals")).json()["data"] == []
        assert (await b.get("/api/v1/checkins")).json()["data"] == []
        assert (await b.get(f"/api/v1/profiles/{a_id}")).status_code == 404
        assert (await b.put(f"/api/v1/profiles/{a_id}", json=private)).status_code == 404
        assert (await b.put("/api/v1/profiles/me", json={**private, "userId": a_id})).status_code == 422
        assert (await b.get("/api/v1/profiles/me")).json()["data"]["id"] == b_id
        assert (await a.get("/api/v1/profiles/me")).json()["data"]["name"] == "公开昵称"
        for path in ("/api/v1/profiles/me", "/api/v1/buddies/recommendations"):
            assert (await anonymous.get(path)).status_code == 401
        assert (await anonymous.put("/api/v1/profiles/me", json=private)).status_code == 401


@pytest.mark.asyncio
async def test_filters_and_global_sort_before_pagination(app):
    async with client_for(app) as a, client_for(app) as b, client_for(app) as c:
        await account(a, "filter_a")
        b_id, c_id = await account(b, "filter_b"), await account(c, "filter_c")
        await save(a, profile_payload("A"))
        await save(b, profile_payload("C++伙伴", start="19:30", end="22:30"))
        await save(c, profile_payload("英语伙伴", "考研", "英语", "08:00", "11:00"))
        for query in ("category=编程开发", "period=evening", "day=1&start=21:00&end=23:00", "overlapOnly=true", "q=c%2B%2B"):
            data = (await a.get(f"/api/v1/buddies/recommendations?{query}")).json()["data"]
            assert [r["id"] for r in data["items"]] == [b_id]
        assert (await a.get("/api/v1/buddies/recommendations?day=2")).json()["data"]["total"] == 0
        first = (await a.get("/api/v1/buddies/recommendations?pageSize=1")).json()["data"]
        second = (await a.get("/api/v1/buddies/recommendations?pageSize=1&page=2")).json()["data"]
        assert first["total"] == second["total"] == 2
        assert first["items"][0]["id"] == b_id and second["items"][0]["id"] == c_id
        assert (await a.get("/api/v1/buddies/recommendations?page=99")).json()["data"]["items"] == []
        # Intersect intervals instead of filtering only by the start hour.
        await save(c, profile_payload("跨时段", "考研", "英语", "17:30", "19:30"))
        assert (await a.get("/api/v1/buddies/recommendations?period=evening")).json()["data"]["total"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("patch", [
    {"name": "   "}, {"categories": ["不存在的方向"]}, {"tags": ["x" * 33]},
    {"styles": ["无效方式"]}, {"stage": "神级"}, {"dailyTargetMinutes": 0},
    {"publicProfile": "yes"}, {"timezone": "America/New_York"},
    {"timeSlots": [{"day": 8, "start": "19:00", "end": "22:00"}]},
    {"timeSlots": [{"day": 1, "start": "22:00", "end": "19:00"}]},
    {"timeSlots": [{"day": 1, "start": "9:00", "end": "22:00"}]},
    {"timeSlots": [{"day": 1, "start": "24:00", "end": "24:00"}]},
    {"timeSlots": [{"day": 1, "start": "19:00", "end": "22:00"}] * 2},
])
async def test_invalid_updates_leave_saved_profile_unchanged(app, patch):
    async with client_for(app) as client:
        await account(client, "validation")
        original = await save(client, profile_payload())
        response = await client.put("/api/v1/profiles/me", json={**profile_payload(), **patch})
        assert response.status_code == 422
        assert (await client.get("/api/v1/profiles/me")).json()["data"] == original


@pytest.mark.asyncio
@pytest.mark.parametrize("query", ["category=bad", "page=0", "pageSize=51", "day=8", "period=night", "start=19:00", "start=22:00&end=19:00", "start=9:00&end=22:00", "period=evening&start=19:00&end=22:00"])
async def test_invalid_filters_are_rejected(app, query):
    async with client_for(app) as client:
        await account(client, "bad_filter")
        assert (await client.get(f"/api/v1/buddies/recommendations?{query}")).status_code == 422
