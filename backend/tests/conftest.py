"""Each PostgreSQL test owns a new schema; never clear an existing application's data."""
import os
import uuid

import pytest_asyncio
from sqlalchemy import event

from app.config import Settings
from app.main import create_app
from app.models import Base


@pytest_asyncio.fixture
async def app(tmp_path):
    database_url = os.environ.get("STUDYMATE_TEST_DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    settings = Settings(
        app_env="test", database_url=database_url, auto_create_schema=False,
        auth_signing_secret="test-signing-secret-with-more-than-32-bytes",
        auth_cookie_secure=False, auth_cookie_samesite="lax", login_max_failures=3,
        canonical_host="xueda.study", cors_origins="http://testserver",
    )
    application = create_app(settings)
    engine = application.state.engine
    schema = f"studymate_test_{uuid.uuid4().hex}" if engine.dialect.name == "postgresql" else None
    if schema:
        @event.listens_for(engine.sync_engine, "connect")
        def isolate_schema(connection, _record):
            # SET must survive a read-only request's ROLLBACK on a pooled
            # connection, including connections first opened during concurrency.
            previous = connection.autocommit
            connection.autocommit = True
            try:
                cursor = connection.cursor()
                cursor.execute(f'SET search_path TO "{schema}"')
                cursor.close()
            finally:
                connection.autocommit = previous

    async with engine.begin() as connection:
        if schema:
            await connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        await connection.run_sync(Base.metadata.create_all)
    try:
        yield application
    finally:
        if schema:
            async with engine.begin() as connection:
                await connection.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        await engine.dispose()
