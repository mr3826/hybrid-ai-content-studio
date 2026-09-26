import asyncio
from logging.config import fileConfig
from pathlib import Path
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

from app.core.config import settings
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def get_db_url(async_driver: bool = True) -> str:
    url = settings.DATABASE_URL
    if url.startswith("sqlite"):
        db_part = url.split(":///")[-1]
        if db_part and not db_part.startswith(":memory:"):
            db_file = (ROOT_DIR / db_part).resolve()
            db_file.parent.mkdir(parents=True, exist_ok=True)
            driver = "sqlite+aiosqlite" if async_driver else "sqlite"
            return f"{driver}:///{db_file.as_posix()}"
    return url if async_driver else url.replace("+aiosqlite", "")


def run_migrations_offline() -> None:
    url = get_db_url(async_driver=False)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_db_url(async_driver=True)

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
