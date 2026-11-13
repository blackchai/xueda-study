from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.http import ApiProblem
from app.models import AuthSession, Profile, User, as_utc
from app.security import hash_secret


@dataclass(slots=True)
class AuthContext:
    session: AuthSession
    user: User
    profile: Profile


async def require_auth(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    settings = request.app.state.settings
    raw_token = request.cookies.get(settings.auth_cookie_name)
    if not raw_token:
        raise ApiProblem(401, "UNAUTHENTICATED", "请先登录")

    auth_session = await db.scalar(
        select(AuthSession).where(AuthSession.token_hash == hash_secret(raw_token))
    )
    if (
        not auth_session
        or auth_session.revoked_at
        or as_utc(auth_session.expires_at) <= datetime.now(timezone.utc)
    ):
        raise ApiProblem(401, "UNAUTHENTICATED", "登录会话已失效")

    user = await db.get(User, auth_session.user_id)
    profile = await db.get(Profile, auth_session.user_id)
    if not user or not user.is_active or user.status != "active" or not profile:
        raise ApiProblem(401, "UNAUTHENTICATED", "账号不可用")
    return AuthContext(session=auth_session, user=user, profile=profile)
