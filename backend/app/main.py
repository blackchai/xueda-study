import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.routing import Match
from sqlalchemy import text

from app.api.account_auth import router as account_auth_router
from app.api.checkins import router as checkins_router
from app.api.goals import router as goals_router
from app.api.profiles import router as profiles_router
from app.api.buddies import router as buddies_router
from app.api.buddy_requests import router as buddy_requests_router
from app.api.notifications import router as notifications_router
from app.api.groups import router as groups_router
from app.api.group_shares import router as group_shares_router
from app.config import Settings, get_settings
from app.database import create_database
from app.http import ApiProblem, request_id, success
from app.models import Base


def create_app(
    settings: Settings | None = None,
) -> FastAPI:
    active_settings = settings or get_settings()
    active_settings.validate_for_startup()
    engine, session_factory = create_database(active_settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if active_settings.auto_create_schema:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
        yield
        await engine.dispose()

    app = FastAPI(
        title="StudyMate API",
        version="0.1.0",
        docs_url="/api/docs" if active_settings.app_env != "production" else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if active_settings.app_env != "production" else None,
        lifespan=lifespan,
    )
    app.state.settings = active_settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.logger = logging.getLogger("studymate.auth")

    if active_settings.parsed_cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=active_settings.parsed_cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Content-Type", "X-QR-Poll-Token", "X-CSRF-Token"],
        )

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        incoming = request.headers.get("X-Request-ID", "")
        request.state.request_id = incoming[:80] if incoming else f"req_{uuid.uuid4().hex}"
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.middleware("http")
    async def redirect_www_to_canonical_host(request: Request, call_next):
        host = request.headers.get("host", "").split(":", 1)[0].lower()
        canonical_host = active_settings.canonical_host.lower()
        if canonical_host and host == f"www.{canonical_host}":
            destination = request.url.replace(netloc=canonical_host)
            return RedirectResponse(str(destination), status_code=301)
        return await call_next(request)

    @app.middleware("http")
    async def enforce_cookie_origin(request: Request, call_next):
        """Compare complete origins, including scheme/port, even for login/register."""
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            def normalized(value):
                try:
                    parsed = urlparse(value)
                    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
                        return None
                    port = parsed.port if parsed.port is not None else (443 if parsed.scheme == "https" else 80)
                    return (parsed.scheme.lower(), parsed.hostname.lower(), port)
                except ValueError:
                    return None
            trusted = {normalized(active_settings.public_origin)} if active_settings.public_origin else {normalized(f"{request.url.scheme}://{request.headers.get('host', '')}")}
            trusted.update(normalized(item) for item in active_settings.parsed_cors_origins)
            trusted.discard(None)
            rejected = (origin is not None and normalized(origin) not in trusted) or (
                origin is None and request.cookies.get(active_settings.auth_cookie_name)
                and request.headers.get("sec-fetch-site") == "cross-site")
            if rejected:
                return JSONResponse(
                    status_code=403,
                    content={
                        "code": "CSRF_ORIGIN_REJECTED",
                        "message": "请求来源不受信任",
                        "data": None,
                        "requestId": getattr(request.state, "request_id", "unknown"),
                    },
                )
        return await call_next(request)

    @app.exception_handler(ApiProblem)
    async def handle_api_problem(request: Request, exc: ApiProblem):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "data": None,
                "requestId": request_id(request),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, _exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "code": "VALIDATION_ERROR",
                "message": "请求参数不符合要求",
                "data": None,
                "requestId": request_id(request),
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_routing_error(request: Request, exc: StarletteHTTPException):
        status = exc.status_code
        if status == 405:
            # The SPA GET fallback must not turn an unknown API path into a
            # misleading method error. Real API paths retain their 405 contract.
            known = any(getattr(route, "name", None) != "frontend" and route.matches(request.scope)[0] != Match.NONE
                        for route in app.router.routes)
            if not known:
                status = 404
        return JSONResponse(status_code=status, headers=exc.headers,
                            content={"code": "NOT_FOUND" if status == 404 else "METHOD_NOT_ALLOWED" if status == 405 else "HTTP_ERROR",
                                     "message": "接口或页面不存在" if status == 404 else "请求方法不支持" if status == 405 else "请求无法完成",
                                     "data": None, "requestId": request_id(request)})

    @app.get("/health/live", tags=["health"])
    async def live(request: Request):
        return success(request, {"status": "up"})

    @app.get("/health/ready", tags=["health"])
    async def ready(request: Request):
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        return success(
            request,
            {
                "status": "ready",
            },
        )

    app.include_router(account_auth_router, prefix="/api/v1")
    app.include_router(goals_router, prefix="/api/v1")
    app.include_router(checkins_router, prefix="/api/v1")
    app.include_router(profiles_router, prefix="/api/v1")
    app.include_router(buddies_router, prefix="/api/v1")
    app.include_router(buddy_requests_router, prefix="/api/v1")
    app.include_router(notifications_router, prefix="/api/v1")
    app.include_router(groups_router, prefix="/api/v1")
    app.include_router(group_shares_router, prefix="/api/v1")

    frontend_root = Path(active_settings.frontend_dist_dir).resolve() if active_settings.frontend_dist_dir else None
    if frontend_root and (frontend_root / "index.html").is_file():
        @app.api_route("/{full_path:path}", methods=["GET", "HEAD"], name="frontend", include_in_schema=False)
        async def serve_frontend(full_path: str):
            if full_path in {"api", "health"} or full_path.startswith("api/") or full_path.startswith("health/"):
                raise ApiProblem(404, "NOT_FOUND", "接口不存在")
            candidate = (frontend_root / full_path).resolve()
            if candidate != frontend_root and frontend_root in candidate.parents and candidate.is_file():
                cache = "public, max-age=31536000, immutable" if full_path.startswith("assets/") else "no-cache"
                return FileResponse(candidate, headers={"Cache-Control": cache})
            if full_path.startswith("assets/"):
                raise ApiProblem(404, "NOT_FOUND", "资源不存在")
            return FileResponse(frontend_root / "index.html", headers={"Cache-Control": "no-cache"})

    return app


app = create_app()
