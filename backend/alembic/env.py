from logging.config import fileConfig

from alembic import context
from sqlalchemy import text

from app.config import get_settings
from app.database import build_engine
from app.models import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

settings = get_settings()
database_url = settings.migration_database_url or settings.database_url
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        render_as_batch=connection.dialect.name == "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = build_engine(database_url, migrations=True)
    async with connectable.connect() as connection:
        postgres = connection.dialect.name == "postgresql"
        if postgres:
            await connection.execute(text("SELECT pg_advisory_lock(831705062)"))
            await connection.commit()
        try:
            await connection.run_sync(do_run_migrations)
        finally:
            if postgres:
                if connection.in_transaction():
                    await connection.rollback()
                await connection.execute(text("SELECT pg_advisory_unlock(831705062)"))
                await connection.commit()
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio

    asyncio.run(run_async_migrations())
