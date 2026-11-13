import asyncio
import uuid
from contextlib import AsyncExitStack

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import BuddyRelation, BuddyRequest, Notification, Profile, User
from test_account_auth import client_for, login
from test_profiles_and_buddies import account, profile_payload, save


@pytest_asyncio.fixture
async def trio(app):
    async with AsyncExitStack() as stack:
        clients = [await stack.enter_async_context(client_for(app)) for _ in range(3)]
        ids = []
        for index, client in enumerate(clients):
            ids.append(await account(client, f"buddy_{index}"))
            await save(client, {**profile_payload(f"搭子{index}"), "allowInvites": True})
        yield (*clients, *ids)


async def send(client, recipient, message="一起学习 C++"):
    return await client.post("/api/v1/buddy-requests", json={"recipientId": recipient, "message": message})


async def rows(app, model, *conditions):
    async with app.state.session_factory() as db:
        return await db.scalar(select(func.count()).select_from(model).where(*conditions))


async def establish(a, b, b_id):
    sent = await send(a, b_id)
    assert sent.status_code == 201, sent.text
    req = sent.json()["data"]
    accepted = await b.post(f"/api/v1/buddy-requests/{req['id']}/accept")
    assert accepted.status_code == 200, accepted.text
    return req["id"], accepted.json()["data"]["connection"]["relationId"]


@pytest.mark.asyncio
async def test_send_receive_accept_persist_and_notifications(app, trio):
    a, b, c, a_id, b_id, _ = trio
    sent = await send(a, b_id)
    assert sent.status_code == 201
    item = sent.json()["data"]
    assert item["status"] == "pending" and item["direction"] == "outgoing"
    assert item["peer"]["id"] == b_id
    repeated = await send(a, b_id, "重复点击不能覆盖原留言")
    assert repeated.status_code == 200
    assert repeated.json()["data"]["id"] == item["id"]
    assert repeated.json()["data"]["message"] == item["message"]
    incoming = (await b.get("/api/v1/buddy-requests")).json()["data"]
    assert incoming["total"] == incoming["pendingCount"] == 1
    assert incoming["items"][0]["peer"]["id"] == a_id
    assert (await c.get("/api/v1/buddy-requests")).json()["data"]["total"] == 0
    notice = (await b.get("/api/v1/notifications")).json()["data"]
    assert notice["unreadCount"] == 1 and notice["items"][0]["kind"] == "buddy_request_received"
    for forbidden in ("school", "major", "bio", "password", "email", "event_key", "PRIVATE"):
        assert forbidden not in str(incoming) and forbidden not in str(notice)

    resolved = await b.post(f"/api/v1/buddy-requests/{item['id']}/accept")
    assert resolved.status_code == 200
    assert resolved.json()["data"]["status"] == "accepted"
    relation_id = resolved.json()["data"]["connection"]["relationId"]
    for client, peer in ((a, b_id), (b, a_id)):
        data = (await client.get("/api/v1/buddies")).json()["data"]
        assert data["total"] == 1
        assert data["items"][0]["id"] == relation_id and data["items"][0]["peer"]["id"] == peer
        assert data["items"][0]["peer"]["tags"] == ["C++"]
    assert (await b.post(f"/api/v1/buddy-requests/{item['id']}/accept")).status_code == 200
    assert await rows(app, BuddyRelation) == 1
    assert await rows(app, Notification, Notification.kind == "buddy_request_accepted") == 1
    assert (await b.get("/api/v1/notifications")).json()["data"]["unreadCount"] == 0

    notification = (await a.get("/api/v1/notifications")).json()["data"]["items"][0]
    assert notification["kind"] == "buddy_request_accepted"
    assert (await c.patch(f"/api/v1/notifications/{notification['id']}/read")).status_code == 404
    read = await a.patch(f"/api/v1/notifications/{notification['id']}/read")
    assert read.status_code == 200 and read.json()["data"]["readAt"]
    again = await a.patch(f"/api/v1/notifications/{notification['id']}/read")
    assert again.json()["data"]["readAt"] == read.json()["data"]["readAt"]
    assert (await a.get("/api/v1/notifications?unreadOnly=true")).json()["data"]["total"] == 0
    async with client_for(app) as reopened:
        assert (await login(reopened, "match_buddy_0")).status_code == 200
        assert (await reopened.get("/api/v1/buddies")).json()["data"]["items"][0]["id"] == relation_id
        assert (await reopened.get("/api/v1/notifications")).json()["data"]["items"][0]["readAt"]


@pytest.mark.asyncio
async def test_reject_cancel_and_other_user_cannot_operate_private_invites(app, trio):
    a, b, c, _, b_id, c_id = trio
    sent = (await send(a, b_id)).json()["data"]
    for action in ("accept", "reject", "cancel"):
        assert (await c.post(f"/api/v1/buddy-requests/{sent['id']}/{action}")).status_code == 404
    assert (await c.get(f"/api/v1/buddy-requests/{sent['id']}")).status_code == 404
    assert (await a.post(f"/api/v1/buddy-requests/{sent['id']}/accept")).status_code == 404
    assert (await b.post(f"/api/v1/buddy-requests/{sent['id']}/cancel")).status_code == 404
    assert (await b.post(f"/api/v1/buddy-requests/{sent['id']}/reject")).status_code == 200
    assert (await b.post(f"/api/v1/buddy-requests/{sent['id']}/reject")).status_code == 200
    assert (await b.post(f"/api/v1/buddy-requests/{sent['id']}/accept")).status_code == 409
    assert (await a.get("/api/v1/buddy-requests?direction=outgoing")).json()["data"]["items"][0]["status"] == "rejected"
    assert await rows(app, BuddyRelation) == 0
    assert await rows(app, Notification, Notification.kind == "buddy_request_rejected") == 1
    cancelled = (await send(a, c_id)).json()["data"]
    assert (await a.post(f"/api/v1/buddy-requests/{cancelled['id']}/cancel")).status_code == 200
    assert (await a.post(f"/api/v1/buddy-requests/{cancelled['id']}/cancel")).status_code == 200
    assert (await c.post(f"/api/v1/buddy-requests/{cancelled['id']}/accept")).status_code == 409
    assert await rows(app, BuddyRelation) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("remover", [0, 1])
async def test_either_party_unlink_idempotently_without_resurrecting_old_request(app, trio, remover):
    a, b, c, _, b_id, _ = trio
    request_id, relation_id = await establish(a, b, b_id)
    assert (await send(a, b_id)).status_code == 409
    assert (await c.delete(f"/api/v1/buddies/{relation_id}")).status_code == 404
    actor = (a, b)[remover]
    assert (await actor.delete(f"/api/v1/buddies/{relation_id}")).status_code == 204
    assert (await actor.delete(f"/api/v1/buddies/{relation_id}")).status_code == 204
    for client in (a, b):
        assert (await client.get("/api/v1/buddies")).json()["data"]["total"] == 0
    assert await rows(app, BuddyRelation, BuddyRelation.ended_at.is_(None)) == 0
    assert await rows(app, Notification, Notification.kind == "buddy_relation_removed") == 1
    assert (await b.post(f"/api/v1/buddy-requests/{request_id}/accept")).status_code == 409
    # A new explicit invitation may establish a new relation, not revive history.
    app.state.settings.buddy_pair_cooldown_seconds = 0
    _, next_relation = await establish(a, b, b_id)
    assert next_relation != relation_id
    assert (await b.post(f"/api/v1/buddy-requests/{request_id}/accept")).status_code == 409
    assert await rows(app, BuddyRelation) == 2
    assert await rows(app, BuddyRelation, BuddyRelation.ended_at.is_(None)) == 1


@pytest.mark.asyncio
async def test_eligibility_reverse_invite_and_cooldown(app, trio):
    a, b, _, a_id, b_id, _ = trio
    assert (await send(a, a_id)).status_code == 422
    assert (await send(a, str(uuid.uuid4()))).status_code == 404
    assert (await a.post("/api/v1/buddy-requests", json={"recipientId": b_id, "senderId": b_id})).status_code == 422
    assert (await send(a, b_id, "x" * 201)).status_code == 422
    await save(b, {**profile_payload(), "allowInvites": False})
    assert (await send(a, b_id)).status_code == 404
    await save(b, {**profile_payload(enabled=False), "allowInvites": True})
    assert (await send(a, b_id)).status_code == 404
    await save(b, {**profile_payload(), "allowInvites": True})
    sent = await send(a, b_id)
    assert sent.status_code == 201
    assert (await send(b, a_id)).status_code == 409
    assert await rows(app, BuddyRequest) == 1
    request_id = sent.json()["data"]["id"]
    await b.post(f"/api/v1/buddy-requests/{request_id}/reject")
    assert (await send(a, b_id)).json()["code"] == "BUDDY_PAIR_COOLDOWN"


@pytest.mark.asyncio
async def test_visibility_after_cancel_and_disabled_sender_cannot_be_accepted(app, trio):
    a, b, _, a_id, b_id, _ = trio
    await save(a, {**profile_payload("私密推荐档案", enabled=False), "allowInvites": False})
    invitation = (await send(a, b_id)).json()["data"]
    req_id = invitation["id"]
    shared = (await b.get(f"/api/v1/buddy-requests/{req_id}")).json()["data"]["peer"]
    assert shared["profileVisible"] and shared["tags"] == ["C++"]
    await a.post(f"/api/v1/buddy-requests/{req_id}/cancel")
    hidden = (await b.get(f"/api/v1/buddy-requests/{req_id}")).json()["data"]["peer"]
    assert hidden["profileVisible"] is False and hidden["tags"] == hidden["timeSlots"] == []
    app.state.settings.buddy_pair_cooldown_seconds = 0
    req_id = (await send(a, b_id)).json()["data"]["id"]
    async with app.state.session_factory() as db:
        user = await db.get(User, uuid.UUID(a_id))
        user.is_active = False
        await db.commit()
    assert (await b.post(f"/api/v1/buddy-requests/{req_id}/accept")).status_code == 409
    assert await rows(app, BuddyRelation) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", ["buddy_invites_per_hour", "buddy_invites_per_day", "buddy_pending_limit"])
async def test_persistent_limits(app, trio, limit):
    a, _, _, _, b_id, c_id = trio
    setattr(app.state.settings, limit, 1)
    first = await send(a, b_id)
    assert first.status_code == 201
    # Duplicate click is idempotent even after consuming the quota.
    assert (await send(a, b_id)).status_code == 200
    if limit != "buddy_pending_limit":
        await a.post(f"/api/v1/buddy-requests/{first.json()['data']['id']}/cancel")
    assert (await send(a, c_id)).status_code == 429
    assert await rows(app, BuddyRequest) == 1


@pytest.mark.asyncio
async def test_recommendation_states_and_all_private_list_filters(app, trio):
    a, b, c, _, b_id, c_id = trio
    def state(data, user_id):
        return next(p["connection"]["status"] for p in data["items"] if p["id"] == user_id)
    first = (await a.get("/api/v1/buddies/recommendations")).json()["data"]
    assert state(first, b_id) == "none"
    req_id = (await send(a, b_id)).json()["data"]["id"]
    assert state((await a.get("/api/v1/buddies/recommendations")).json()["data"], b_id) == "outgoing_pending"
    await b.post(f"/api/v1/buddy-requests/{req_id}/accept")
    assert state((await a.get("/api/v1/buddies/recommendations")).json()["data"], b_id) == "connected"
    await send(a, c_id)
    pending = (await a.get("/api/v1/buddy-requests?direction=outgoing&status=pending&pageSize=1")).json()["data"]
    assert pending["total"] == pending["pendingCount"] == 1
    assert pending["items"][0]["peer"]["id"] == c_id
    assert (await b.get("/api/v1/notifications?page=99")).json()["data"]["items"] == []
    assert (await c.get("/api/v1/notifications")).json()["data"]["total"] == 1
    for query in ("direction=bad", "status=bad", "page=0", "pageSize=51"):
        assert (await a.get(f"/api/v1/buddy-requests?{query}")).status_code == 422
    async with client_for(app) as anonymous:
        for path in ("/buddy-requests", "/buddies", "/notifications"):
            assert (await anonymous.get(f"/api/v1{path}")).status_code == 401
        assert (await send(anonymous, b_id)).status_code == 401


def require_postgres(app):
    if app.state.engine.dialect.name != "postgresql":
        pytest.skip("Concurrent row locking must be verified against PostgreSQL")


@pytest.mark.asyncio
async def test_concurrent_duplicate_send_and_accept_are_single_transition(app, trio):
    require_postgres(app)
    a, b, _, _, b_id, _ = trio
    sent = await asyncio.gather(*(send(a, b_id) for _ in range(8)))
    assert sorted(r.status_code for r in sent) == [200] * 7 + [201]
    assert await rows(app, BuddyRequest) == await rows(app, Notification) == 1
    request_ids = {r.json()["data"]["id"] for r in sent}
    assert len(request_ids) == 1
    request_id = request_ids.pop()
    accepted = await asyncio.gather(*(b.post(f"/api/v1/buddy-requests/{request_id}/accept") for _ in range(8)))
    assert all(r.status_code == 200 for r in accepted)
    assert len({r.json()["data"]["connection"]["relationId"] for r in accepted}) == 1
    assert await rows(app, BuddyRelation) == 1
    assert await rows(app, Notification, Notification.kind == "buddy_request_accepted") == 1


@pytest.mark.asyncio
async def test_concurrent_reverse_send_is_serialized(app, trio):
    require_postgres(app)
    a, b, _, a_id, b_id, _ = trio
    sent = await asyncio.gather(send(a, b_id), send(b, a_id))
    assert sorted(r.status_code for r in sent) == [201, 409]
    assert await rows(app, BuddyRequest) == 1


@pytest.mark.asyncio
async def test_concurrent_different_recipients_share_sender_quota(app, trio):
    require_postgres(app)
    a, _, _, a_id, b_id, c_id = trio
    app.state.settings.buddy_invites_per_hour = 1
    responses = await asyncio.gather(send(a, b_id), send(a, c_id))
    assert sorted(r.status_code for r in responses) == [201, 429]
    assert await rows(app, BuddyRequest, BuddyRequest.sender_id == uuid.UUID(a_id)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["cancel", "reject"])
async def test_accept_racing_another_terminal_action_is_consistent(app, trio, action):
    require_postgres(app)
    a, b, _, _, b_id, _ = trio
    request_id = (await send(a, b_id)).json()["data"]["id"]
    actor = a if action == "cancel" else b
    responses = await asyncio.gather(b.post(f"/api/v1/buddy-requests/{request_id}/accept"),
                                     actor.post(f"/api/v1/buddy-requests/{request_id}/{action}"))
    assert sorted(r.status_code for r in responses) == [200, 409]
    status = (await a.get(f"/api/v1/buddy-requests/{request_id}")).json()["data"]["status"]
    assert await rows(app, BuddyRelation, BuddyRelation.ended_at.is_(None)) == int(status == "accepted")


@pytest.mark.asyncio
async def test_notification_failure_rolls_back_accept_and_relation(app, trio, monkeypatch):
    a, b, _, _, b_id, _ = trio
    request_id = (await send(a, b_id)).json()["data"]["id"]
    def fail(*_args, **_kwargs):
        raise RuntimeError("injected notification failure")
    monkeypatch.setattr("app.api.buddy_requests.add_notification", fail)
    with pytest.raises(RuntimeError, match="injected notification failure"):
        await b.post(f"/api/v1/buddy-requests/{request_id}/accept")
    assert (await a.get(f"/api/v1/buddy-requests/{request_id}")).json()["data"]["status"] == "pending"
    assert await rows(app, BuddyRelation) == 0
    assert await rows(app, Notification) == 1


@pytest.mark.asyncio
async def test_database_rejects_duplicate_pending_pair(app, trio):
    a, _, _, a_id, b_id, _ = trio
    await send(a, b_id)
    low, high = sorted((uuid.UUID(a_id), uuid.UUID(b_id)))
    async with app.state.session_factory() as db:
        db.add(BuddyRequest(sender_id=uuid.UUID(b_id), recipient_id=uuid.UUID(a_id),
                            user_low_id=low, user_high_id=high, message="", status="pending"))
        with pytest.raises(IntegrityError):
            await db.flush()
        await db.rollback()
