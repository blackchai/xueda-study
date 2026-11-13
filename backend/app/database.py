from collections.abc import AsyncIterator
import ssl

from fastapi import Request
from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


def build_engine(database_url: str, *, migrations: bool = False):
    """Adapt libpq-style cloud URLs without passing unknown SSL keywords to asyncpg."""
    url = make_url(database_url)
    if url.drivername in {"postgres", "postgresql"}:
        url = url.set(drivername="postgresql+asyncpg")
    options = {"pool_pre_ping": True, "hide_parameters": True}
    if url.drivername == "postgresql+asyncpg":
        query = dict(url.query)
        mode = query.pop("sslmode", None)
        explicit_ssl = query.pop("ssl", None)
        root_cert = query.pop("sslrootcert", None)
        binding = query.pop("channel_binding", None)
        if binding not in {None, "disable", "prefer"}:
            raise ValueError("asyncpg does not support channel_binding=require; use an asyncpg connection template with verified TLS")
        if mode is not None and explicit_ssl is not None:
            raise ValueError("Use either sslmode or ssl, not both")
        mode = mode or explicit_ssl
        if mode not in {None, "disable", "allow", "prefer", "require", "verify-ca", "verify-full"}:
            raise ValueError("Unsupported PostgreSQL TLS mode")
        host = url.host or query.get("host", "")
        local = not host or str(host).startswith("/") or host in {"localhost", "127.0.0.1", "::1", "database"}
        if migrations and "-pooler." in str(host):
            raise ValueError("Alembic requires a direct database URL; set STUDYMATE_MIGRATION_DATABASE_URL")
        if not local and mode in {"disable", "allow", "prefer"}:
            raise ValueError("Remote databases require verified TLS")
        connect = {"timeout": 15, "command_timeout": 180 if migrations else 60}
        if mode in {"require", "verify-ca", "verify-full"} or not local:
            context = ssl.create_default_context(cafile=root_cert)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.check_hostname = mode != "verify-ca"
            connect["ssl"] = context
        elif mode is not None:
            connect["ssl"] = mode
        elif root_cert:
            raise ValueError("sslrootcert requires a TLS mode")
        application_name = query.pop("application_name", None)
        if application_name:
            connect["server_settings"] = {"application_name": application_name}
        url = url.set(query=query)
        options["connect_args"] = connect
        if migrations:
            options["poolclass"] = NullPool
        else:
            options.update(pool_size=3, max_overflow=2, pool_recycle=300)
    elif migrations:
        options["poolclass"] = NullPool
    return create_async_engine(url, **options)


def create_database(database_url: str):
    engine = build_engine(database_url)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine.sync_engine, "connect")
        def enable_foreign_keys(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_factory


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session

