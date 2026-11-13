from datetime import timedelta
import re

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.auth_context import AuthContext, require_auth
from app.database import get_db
from app.http import ApiProblem, success
from app.models import AuthSession, LoginThrottle, Profile, User, as_utc, utc_now
from app.security import hash_password, hash_secret, password_needs_rehash, random_token, verify_password

router = APIRouter(prefix="/auth", tags=["authentication"])

USERNAME_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]{2,31}$")
PASSWORD_LETTER = re.compile(r"[A-Za-z]")
PASSWORD_DIGIT = re.compile(r"\d")
DUMMY_PASSWORD_HASH = hash_password("not-a-real-user-password-2026")


class RegisterPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=32)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(alias="confirmPassword", min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip().lower()
        if not USERNAME_PATTERN.fullmatch(value):
            raise ValueError("用户名需以字母开头，只能包含字母、数字和下划线")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not PASSWORD_LETTER.search(value) or not PASSWORD_DIGIT.search(value):
            raise ValueError("密码必须同时包含字母和数字")
        return value

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("两次输入的密码不一致")
        return self


class LoginPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)


def auth_user_payload(user: User, profile: Profile) -> dict[str, object]:
    return {
        "userId": str(user.id),
        "username": user.username,
        "email": user.email,
        "displayName": profile.display_name,
        "avatarUrl": profile.avatar_url,
        "onboardingCompleted": profile.onboarding_completed,
    }


def set_session_cookie(response: JSONResponse, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.auth_session_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/",
    )


def throttle_key(request: Request, account: str, settings: Settings) -> str:
    client_host = request.client.host if request.client else "unknown"
    return hash_secret(f"{settings.auth_signing_secret}:{client_host}:{account}")


async def record_failed_login(
    db: AsyncSession,
    key: str,
    settings: Settings,
) -> bool:
    now = utc_now()
    throttle = await db.scalar(
        select(LoginThrottle).where(LoginThrottle.key_hash == key).with_for_update()
    )
    window = timedelta(minutes=settings.login_window_minutes)
    if not throttle:
        throttle = LoginThrottle(key_hash=key, failure_count=1, window_started_at=now)
        db.add(throttle)
    elif now - as_utc(throttle.window_started_at) > window:
        throttle.failure_count = 1
        throttle.window_started_at = now
        throttle.locked_until = None
    else:
        throttle.failure_count += 1

    locked = throttle.failure_count >= settings.login_max_failures
    if locked:
        throttle.locked_until = now + timedelta(minutes=settings.login_lock_minutes)
    await db.commit()
    return locked


@router.post("/register", status_code=201)
async def register(
    payload: RegisterPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    duplicate = await db.scalar(
        select(User.id).where(or_(User.username == payload.username, User.email == payload.email))
    )
    if duplicate:
        raise ApiProblem(409, "ACCOUNT_ALREADY_EXISTS", "用户名或邮箱已被注册")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        status="active",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    profile = Profile(user_id=user.id, display_name=payload.username, onboarding_completed=False)
    db.add(profile)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ApiProblem(409, "ACCOUNT_ALREADY_EXISTS", "用户名或邮箱已被注册") from None
    return success(request, auth_user_payload(user, profile), "注册成功，请登录")


@router.post("/login")
async def login(
    payload: LoginPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    settings: Settings = request.app.state.settings
    account = payload.account.strip().lower()
    key = throttle_key(request, account, settings)
    throttle = await db.get(LoginThrottle, key)
    now = utc_now()
    if throttle and throttle.locked_until and as_utc(throttle.locked_until) > now:
        raise ApiProblem(429, "LOGIN_RATE_LIMITED", "登录尝试过多，请稍后再试")

    user = await db.scalar(
        select(User).where(or_(User.username == account, User.email == account))
    )
    encoded_hash = user.password_hash if user and user.password_hash else DUMMY_PASSWORD_HASH
    password_ok = verify_password(payload.password, encoded_hash)
    if not user or not user.is_active or user.status != "active" or not password_ok:
        locked = await record_failed_login(db, key, settings)
        if locked:
            raise ApiProblem(429, "LOGIN_RATE_LIMITED", "登录尝试过多，请稍后再试")
        raise ApiProblem(401, "INVALID_CREDENTIALS", "账号或密码错误")

    profile = await db.get(Profile, user.id)
    if not profile:
        raise ApiProblem(401, "INVALID_CREDENTIALS", "账号或密码错误")

    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
    user.last_login_at = now
    await db.execute(delete(LoginThrottle).where(LoginThrottle.key_hash == key))
    raw_token = random_token(32)
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_secret(raw_token),
            expires_at=now + timedelta(days=settings.auth_session_days),
        )
    )
    await db.commit()

    response = JSONResponse(success(request, auth_user_payload(user, profile), "登录成功"))
    set_session_cookie(response, settings, raw_token)
    return response


@router.get("/me")
async def auth_me(
    request: Request,
    auth: AuthContext = Depends(require_auth),
):
    return success(request, auth_user_payload(auth.user, auth.profile))


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    settings: Settings = request.app.state.settings
    raw_token = request.cookies.get(settings.auth_cookie_name)
    if raw_token:
        auth_session = await db.scalar(
            select(AuthSession).where(AuthSession.token_hash == hash_secret(raw_token))
        )
        if auth_session and not auth_session.revoked_at:
            auth_session.revoked_at = utc_now()
            await db.commit()
    response = Response(status_code=204)
    response.delete_cookie(
        settings.auth_cookie_name,
        path="/",
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )
    return response
