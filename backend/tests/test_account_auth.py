from datetime import date, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.config import Settings
from app.models import Checkin, Goal, User


PASSWORD = "StudyMate2026!"


def client_for(app) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


async def register(client: AsyncClient, username: str, email: str):
    return await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": PASSWORD,
            "confirmPassword": PASSWORD,
        },
    )


async def login(client: AsyncClient, account: str, password: str = PASSWORD):
    return await client.post(
        "/api/v1/auth/login",
        json={"account": account, "password": password},
    )


def goal_payload(title: str = "A 的考研目标") -> dict[str, object]:
    today = date.today()
    return {
        "title": title,
        "description": "测试真实持久化和资源所有权",
        "category": "考研",
        "tags": ["408", "数学"],
        "startDate": today.isoformat(),
        "targetDate": (today + timedelta(days=90)).isoformat(),
        "status": "进行中",
        "color": "#5b5ce2",
    }


@pytest.mark.asyncio
async def test_register_login_refresh_logout_and_password_storage(app):
    async with client_for(app) as anonymous:
        assert (await anonymous.get("/api/v1/auth/me")).status_code == 401
        assert (await anonymous.get("/api/v1/goals")).status_code == 401

    async with client_for(app) as client:
        response = await register(client, "user_a", "USER_A@example.com")
        assert response.status_code == 201
        assert response.json()["data"]["username"] == "user_a"
        assert response.json()["data"]["email"] == "user_a@example.com"
        assert "studymate_session" not in response.cookies

        duplicate = await register(client, "another_user", "user_a@example.com")
        assert duplicate.status_code == 409
        assert duplicate.json()["code"] == "ACCOUNT_ALREADY_EXISTS"

        wrong = await login(client, "user_a", "WrongPassword2026!")
        assert wrong.status_code == 401
        assert wrong.json()["message"] == "账号或密码错误"

        authenticated = await login(client, "USER_A@example.com")
        assert authenticated.status_code == 200
        cookie = authenticated.headers["set-cookie"]
        assert "studymate_session=" in cookie
        assert "HttpOnly" in cookie
        assert "SameSite=lax" in cookie
        assert "Secure" not in cookie

        # A subsequent request with the same cookie jar models a browser refresh.
        me = await client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["data"]["username"] == "user_a"

        logged_out = await client.post("/api/v1/auth/logout")
        assert logged_out.status_code == 204
        assert (await client.get("/api/v1/auth/me")).status_code == 401

    async with app.state.session_factory() as session:
        user = await session.scalar(select(User).where(User.username == "user_a"))
        assert user is not None
        assert user.password_hash != PASSWORD
        assert user.password_hash.startswith("$argon2id$")
        assert await session.scalar(select(func.count()).select_from(User)) == 1

    # A new client has no old cookie, but the database-backed account can log in again.
    async with client_for(app) as reopened_browser:
        assert (await reopened_browser.get("/api/v1/auth/me")).status_code == 401
        assert (await login(reopened_browser, "user_a")).status_code == 200
        assert (await reopened_browser.get("/api/v1/auth/me")).status_code == 200


@pytest.mark.asyncio
async def test_registration_validation_and_generic_login_error(app):
    async with client_for(app) as client:
        weak = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "user_a",
                "email": "user_a@example.com",
                "password": "password",
                "confirmPassword": "password",
            },
        )
        assert weak.status_code == 422
        assert weak.json()["message"] == "请求参数不符合要求"

        mismatch = await client.post(
            "/api/v1/auth/register",
            json={
                "username": "user_a",
                "email": "not-an-email",
                "password": PASSWORD,
                "confirmPassword": "Another2026!",
            },
        )
        assert mismatch.status_code == 422

        missing = await login(client, "missing_user", "WrongPassword2026!")
        assert missing.status_code == 401
        assert missing.json()["message"] == "账号或密码错误"


@pytest.mark.asyncio
async def test_login_rate_limit_blocks_correct_password_during_lock(app):
    async with client_for(app) as client:
        assert (await register(client, "rate_user", "rate@example.com")).status_code == 201
        for attempt in range(3):
            response = await login(client, "rate_user", f"WrongPassword{attempt}!")
        assert response.status_code == 429
        assert response.json()["code"] == "LOGIN_RATE_LIMITED"

        blocked = await login(client, "rate_user")
        assert blocked.status_code == 429
        assert blocked.json()["message"] == "登录尝试过多，请稍后再试"


@pytest.mark.asyncio
async def test_two_accounts_have_independent_sessions_and_private_data(app):
    client_a = client_for(app)
    client_b = client_for(app)
    async with client_a, client_b:
        assert (await register(client_a, "user_a", "a@example.com")).status_code == 201
        assert (await register(client_b, "user_b", "b@example.com")).status_code == 201
        assert (await login(client_a, "user_a")).status_code == 200
        assert (await login(client_b, "b@example.com")).status_code == 200

        assert (await client_a.get("/api/v1/auth/me")).json()["data"]["username"] == "user_a"
        assert (await client_b.get("/api/v1/auth/me")).json()["data"]["username"] == "user_b"

        created_goal = await client_a.post("/api/v1/goals", json=goal_payload())
        assert created_goal.status_code == 201
        goal = created_goal.json()["data"]
        goal_id = goal["id"]
        assert goal["tasks"] == []

        task = await client_a.post(
            f"/api/v1/goals/{goal_id}/tasks",
            json={
                "title": "完成一组算法题",
                "dueDate": date.today().isoformat(),
                "estimatedMinutes": 60,
                "completed": False,
            },
        )
        assert task.status_code == 201

        checkin = await client_a.post(
            "/api/v1/checkins",
            json={
                "date": date.today().isoformat(),
                "duration": 90,
                "content": "完成数据结构练习",
                "mood": "专注在线",
                "goalId": goal_id,
            },
        )
        assert checkin.status_code == 201
        checkin_id = checkin.json()["data"]["id"]

        assert len((await client_a.get("/api/v1/goals")).json()["data"]) == 1
        assert len((await client_a.get("/api/v1/checkins")).json()["data"]) == 1
        assert (await client_b.get("/api/v1/goals")).json()["data"] == []
        assert (await client_b.get("/api/v1/checkins")).json()["data"] == []

        # Ownership checks deliberately return 404 so private-resource existence is not disclosed.
        assert (await client_b.get(f"/api/v1/goals/{goal_id}")).status_code == 404
        assert (
            await client_b.put(f"/api/v1/goals/{goal_id}", json=goal_payload("B 尝试篡改"))
        ).status_code == 404
        assert (await client_b.delete(f"/api/v1/goals/{goal_id}")).status_code == 404
        assert (await client_b.get(f"/api/v1/checkins/{checkin_id}")).status_code == 404
        foreign_goal_checkin = await client_b.post(
            "/api/v1/checkins",
            json={
                "date": date.today().isoformat(),
                "duration": 30,
                "content": "不应保存",
                "mood": "稳步推进",
                "goalId": goal_id,
            },
        )
        assert foreign_goal_checkin.status_code == 404

        # User B remains fully functional inside the independent cookie session.
        own_goal = await client_b.post("/api/v1/goals", json=goal_payload("B 的四六级目标"))
        assert own_goal.status_code == 201

    async with app.state.session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(User)) == 2
        assert await session.scalar(select(func.count()).select_from(Goal)) == 2
        assert await session.scalar(select(func.count()).select_from(Checkin)) == 1

    # Persistence survives client replacement and data remains tied to each login identity.
    async with client_for(app) as next_session_a:
        assert (await login(next_session_a, "user_a")).status_code == 200
        assert len((await next_session_a.get("/api/v1/goals")).json()["data"]) == 1
        assert len((await next_session_a.get("/api/v1/checkins")).json()["data"]) == 1


@pytest.mark.asyncio
async def test_csrf_origin_check_rejects_untrusted_cookie_request(app):
    async with client_for(app) as client:
        assert (await register(client, "csrf_user", "csrf@example.com")).status_code == 201
        assert (await login(client, "csrf_user")).status_code == 200
        response = await client.post(
            "/api/v1/goals",
            json=goal_payload(),
            headers={"Origin": "https://attacker.example"},
        )
        assert response.status_code == 403
        assert response.json()["code"] == "CSRF_ORIGIN_REJECTED"


@pytest.mark.asyncio
async def test_www_host_redirects_to_canonical_domain(app):
    async with client_for(app) as client:
        response = await client.get(
            "/auth?next=dashboard",
            headers={"Host": "www.xueda.study"},
            follow_redirects=False,
        )
    assert response.status_code == 301
    assert response.headers["location"] == "http://xueda.study/auth?next=dashboard"


def test_production_settings_normalize_managed_postgres_url():
    settings = Settings(
        app_env="production",
        database_url="postgresql://user:password@db.example/studymate",
        auth_signing_secret="a-production-signing-secret-longer-than-32-bytes",
        auth_cookie_secure=True,
    )
    settings.validate_for_startup()
    assert settings.database_url.startswith("postgresql+asyncpg://")
