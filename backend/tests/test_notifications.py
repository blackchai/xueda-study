import asyncio
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.config import Settings
from app.models import AuthSession, GroupJoinRequest, GroupMember, GroupMemberEvent, Notification, utc_now
from test_account_auth import client_for, login, register
from test_groups import count, create, join, trio


async def notices(client):
    response = await client.get('/api/v1/notifications')
    assert response.status_code == 200
    return response.json()['data']


async def apply(client, gid):
    response = await client.post(f'/api/v1/groups/{gid}/join')
    assert response.status_code in (200, 201)
    return response.json()['data']['requestId']


@pytest.mark.asyncio
async def test_group_event_notifications_persist_are_private_and_deduplicated(app, trio):
    a, b, c, a_id, b_id, _ = trio
    gid = await create(a)
    rid = await apply(b, gid)
    assert await apply(b, gid) == rid
    received = await notices(a)
    assert received['total'] == received['unreadCount'] == 1
    item = received['items'][0]
    assert item['kind'] == 'group_join_requested' and item['groupRequestId'] == rid
    assert item['groupId'] == gid and item['actor']['id'] == b_id
    assert item['href'] == f'/groups/{gid}?tab=requests'
    assert not any(key in str(received) for key in ('event_key', 'email', 'password', 'MEMBERS_ONLY', 'school'))
    assert (await c.patch(f"/api/v1/notifications/{item['id']}/read")).status_code == 404
    assert (await c.get('/api/v1/notifications')).json()['data']['total'] == 0
    assert (await a.post(f'/api/v1/groups/{gid}/join-requests/{rid}/approve')).status_code == 200
    assert (await a.post(f'/api/v1/groups/{gid}/join-requests/{rid}/approve')).status_code == 200
    assert (await notices(a))['unreadCount'] == 0
    accepted = (await notices(b))['items'][0]
    assert accepted['kind'] == 'group_join_approved' and accepted['groupRequestId'] == rid
    assert accepted['href'] == f'/groups/{gid}'
    assert (await a.delete(f'/api/v1/groups/{gid}/members/{b_id}')).status_code == 204
    assert (await a.delete(f'/api/v1/groups/{gid}/members/{b_id}')).status_code == 204
    removed = (await notices(b))['items'][0]
    assert removed['kind'] == 'group_member_removed' and removed['groupEventId'] and removed['href'] == '/groups'
    assert await count(app, GroupMemberEvent) == 1
    async with app.state.session_factory() as db:
        event = await db.get(GroupMemberEvent, uuid.UUID(removed['groupEventId']))
        assert str(event.user_id) == b_id and str(event.actor_id) == a_id
    assert (await b.post('/api/v1/auth/logout')).status_code == 204
    assert (await login(b, 'match_group_1')).status_code == 200
    assert (await notices(b))['total'] == 2
    # A fresh membership removal is a different durable event.
    await join(a, b, gid)
    await a.delete(f'/api/v1/groups/{gid}/members/{b_id}')
    assert await count(app, GroupMemberEvent) == 2
    assert await count(app, Notification, Notification.kind == 'group_member_removed') == 2


@pytest.mark.asyncio
async def test_read_all_is_own_idempotent_preserves_first_read_and_does_not_hide_future_events(app, trio):
    a, b, _, _, _, _ = trio
    gid = await create(a)
    rid = await apply(b, gid)
    notice = (await notices(a))['items'][0]
    first = (await a.patch(f"/api/v1/notifications/{notice['id']}/read")).json()['data']['readAt']
    assert (await a.patch('/api/v1/notifications/read-all')).json()['data']['updatedCount'] == 0
    assert (await a.patch(f"/api/v1/notifications/{notice['id']}/read")).json()['data']['readAt'] == first
    await a.post(f'/api/v1/groups/{gid}/join-requests/{rid}/reject')
    assert (await notices(b))['unreadCount'] == 1
    assert (await a.patch('/api/v1/notifications/read-all')).json()['data']['updatedCount'] == 0
    assert (await notices(b))['unreadCount'] == 1
    assert (await b.patch('/api/v1/notifications/read-all')).json()['data'] == {'updatedCount': 1, 'unreadCount': 0}
    assert (await b.patch('/api/v1/notifications/read-all')).json()['data']['updatedCount'] == 0
    rid2 = await apply(b, gid)
    assert rid2 != rid
    assert (await a.get('/api/v1/notifications/unread-count')).json()['data']['unreadCount'] == 1
    assert (await a.get('/api/v1/notifications?unreadOnly=true')).json()['data']['total'] == 1
    assert (await a.patch('/api/v1/notifications/read-all')).json()['data']['updatedCount'] == 1
    assert (await notices(a))['items'][-1]['readAt'] == first


@pytest.mark.asyncio
async def test_notification_pagination_validation_and_no_client_creation(app, trio):
    a, b, c, _, _, _ = trio
    for i in range(13):
        gid = await create(a, name=f'分页小组{i}')
        await apply(b, gid)
    first = (await a.get('/api/v1/notifications?pageSize=12')).json()['data']
    second = (await a.get('/api/v1/notifications?page=2&pageSize=12')).json()['data']
    assert first['total'] == first['unreadCount'] == 13
    assert len(first['items']) == 12 and len(second['items']) == 1
    assert not {x['id'] for x in first['items']} & {x['id'] for x in second['items']}
    for query in ('page=0', 'pageSize=51', 'unreadOnly=invalid'):
        assert (await a.get(f'/api/v1/notifications?{query}')).status_code == 422
    assert (await c.post('/api/v1/notifications', json={'userId': 'fake', 'title': 'fake'})).status_code == 405
    async with client_for(app) as anonymous:
        for path in ('/notifications', '/notifications/unread-count'):
            assert (await anonymous.get('/api/v1' + path)).status_code == 401
        assert (await anonymous.patch('/api/v1/notifications/read-all')).status_code == 401


@pytest.mark.asyncio
async def test_cancel_archive_and_ownership_handoff_do_not_leave_unactionable_unread(app, trio):
    a, b, c, _, _, c_id = trio
    gid = await create(a)
    rid = await apply(b, gid)
    await b.post(f'/api/v1/groups/{gid}/join-requests/{rid}/cancel')
    assert (await notices(a))['unreadCount'] == 0
    await join(a, c, gid)
    rid = await apply(b, gid)
    await a.post(f'/api/v1/groups/{gid}/transfer', json={'newOwnerId': c_id})
    assert (await notices(a))['unreadCount'] == 0
    incoming = next(x for x in (await notices(c))['items'] if x['kind'] == 'group_join_requested')
    assert incoming['groupRequestId'] == rid
    await c.delete(f'/api/v1/groups/{gid}')
    archived = await notices(c)
    assert archived['items'][0]['href'] == '/groups'
    assert archived['unreadCount'] == 1  # C's earlier approval result, not the cancelled pending request.
    assert all(x['readAt'] for x in archived['items'] if x['kind'] == 'group_join_requested')
    assert (await notices(b))['total'] == 0


@pytest.mark.asyncio
@pytest.mark.parametrize('operation', ['apply', 'approve', 'remove'])
async def test_notification_failure_rolls_back_group_transaction(app, trio, monkeypatch, operation):
    a, b, _, _, b_id, _ = trio
    gid = await create(a)
    rid = await apply(b, gid) if operation != 'apply' else None
    if operation == 'remove':
        await a.post(f'/api/v1/groups/{gid}/join-requests/{rid}/approve')
    previous = await count(app, Notification)
    def fail(*_args, **_kwargs):
        raise RuntimeError('injected group notification failure')
    monkeypatch.setattr('app.api.groups.add_group_notification', fail)
    with pytest.raises(RuntimeError, match='injected group notification failure'):
        if operation == 'apply':
            await b.post(f'/api/v1/groups/{gid}/join')
        elif operation == 'approve':
            await a.post(f'/api/v1/groups/{gid}/join-requests/{rid}/approve')
        else:
            await a.delete(f'/api/v1/groups/{gid}/members/{b_id}')
    assert await count(app, Notification) == previous
    assert await count(app, GroupMember) == (2 if operation == 'remove' else 1)
    assert await count(app, GroupMemberEvent) == 0
    if operation == 'apply':
        assert await count(app, GroupJoinRequest) == 0
    elif operation == 'approve':
        async with app.state.session_factory() as db:
            assert (await db.get(GroupJoinRequest, uuid.UUID(rid))).status == 'pending'


@pytest.mark.asyncio
async def test_postgres_concurrent_group_events_and_reads_are_idempotent(app, trio):
    if app.state.engine.dialect.name != 'postgresql':
        pytest.skip('Requires PostgreSQL row locks')
    a, b, _, _, b_id, _ = trio
    gid = await create(a)
    responses = await asyncio.gather(*(b.post(f'/api/v1/groups/{gid}/join') for _ in range(6)))
    assert all(r.status_code in (200, 201) for r in responses)
    rid = responses[0].json()['data']['requestId']
    assert await count(app, Notification) == 1
    responses = await asyncio.gather(*(a.post(f'/api/v1/groups/{gid}/join-requests/{rid}/approve') for _ in range(6)))
    assert all(r.status_code == 200 for r in responses)
    assert await count(app, Notification, Notification.kind == 'group_join_approved') == 1
    notice = (await notices(b))['items'][0]
    responses = await asyncio.gather(b.patch('/api/v1/notifications/read-all'), b.patch(f"/api/v1/notifications/{notice['id']}/read"))
    assert all(r.status_code == 200 for r in responses)
    assert (await notices(b))['unreadCount'] == 0
    responses = await asyncio.gather(*(a.delete(f'/api/v1/groups/{gid}/members/{b_id}') for _ in range(6)))
    assert all(r.status_code == 204 for r in responses)
    assert await count(app, GroupMemberEvent) == 1
    assert await count(app, Notification, Notification.kind == 'group_member_removed') == 1


@pytest.mark.asyncio
@pytest.mark.parametrize('origin', ['http://evil.example', 'http://testserver:9090', 'http://testserver:0', 'https://testserver', 'null', 'http://testserver/path', 'http://user@testserver', 'http://testserver:bad'])
async def test_browser_origin_is_exact_and_also_protects_anonymous_login(app, origin):
    async with client_for(app) as client:
        result = await client.post('/api/v1/auth/login', headers={'Origin': origin}, json={'account': 'missing', 'password': 'FakePassword2026!'})
        assert result.status_code == 403 and result.json()['code'] == 'CSRF_ORIGIN_REJECTED'


@pytest.mark.asyncio
async def test_secure_cookie_cors_revocation_and_expiry(app):
    async with client_for(app) as client:
        await register(client, 'secure_user', 'secure@example.com')
        valid = await client.options('/api/v1/notifications/read-all', headers={'Origin': 'http://testserver', 'Access-Control-Request-Method': 'PATCH'})
        assert valid.status_code == 200 and valid.headers['access-control-allow-origin'] == 'http://testserver'
        denied = await client.options('/api/v1/notifications/read-all', headers={'Origin': 'http://evil.example', 'Access-Control-Request-Method': 'PATCH'})
        assert denied.status_code == 400 and 'access-control-allow-origin' not in denied.headers
        app.state.settings.auth_cookie_secure = True
        client.base_url = 'https://testserver'
        response = await login(client, 'secure_user')
        assert response.status_code == 200
        assert all(value in response.headers['set-cookie'] for value in ('HttpOnly', 'Secure', 'SameSite=lax', 'Max-Age='))
        old = client.cookies.get('studymate_session')
        assert (await client.patch('/api/v1/notifications/read-all', headers={'Sec-Fetch-Site': 'cross-site'})).status_code == 403
        assert (await client.post('/api/v1/auth/logout')).status_code == 204
        client.cookies.set('studymate_session', old)
        assert (await client.get('/api/v1/notifications')).status_code == 401
        await login(client, 'secure_user')
        async with app.state.session_factory() as db:
            for session in await db.scalars(select(AuthSession).where(AuthSession.revoked_at.is_(None))):
                session.expires_at = utc_now() - timedelta(seconds=1)
            await db.commit()
        assert (await client.get('/api/v1/notifications/unread-count')).status_code == 401


def test_production_rejects_placeholder_secret_sqlite_and_auto_schema():
    base = dict(app_env='production', database_url='postgresql+asyncpg://test@localhost/test',
                auth_signing_secret='testing-only-unique-secret-longer-than-32-bytes', auth_cookie_secure=True)
    Settings(**base).validate_for_startup()
    for patch in ({'auth_signing_secret': 'development-only-change-before-deploying'}, {'database_url': 'sqlite+aiosqlite:///test.db'}, {'auto_create_schema': True}):
        with pytest.raises(ValueError):
            Settings(**{**base, **patch}).validate_for_startup()


@pytest.mark.asyncio
async def test_database_rejects_duplicate_notification_event(app, trio):
    a, b, _, a_id, b_id, _ = trio
    gid = await create(a)
    rid = await apply(b, gid)
    async with app.state.session_factory() as db:
        db.add(Notification(user_id=uuid.UUID(a_id), actor_id=uuid.UUID(b_id), kind='group_join_requested',
                            group_id=uuid.UUID(gid), group_request_id=uuid.UUID(rid),
                            event_key=f'group_join_requested:{rid}:{a_id}'))
        with pytest.raises(IntegrityError):
            await db.flush()
        await db.rollback()
