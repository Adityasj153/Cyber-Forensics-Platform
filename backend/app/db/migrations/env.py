import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db.models.base_models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.getenv("DATABASE_URL_SYNC")
print(f"[ALEMBIC DEBUG] DATABASE_URL_SYNC = {database_url}", flush=True, file=sys.stderr)
print(f"[ALEMBIC DEBUG] config file = {config.config_file_name}", flush=True, file=sys.stderr)
print(
    f"[ALEMBIC DEBUG] script_location = {config.get_main_option('script_location')}",
    flush=True,
    file=sys.stderr,
)
print(
    f"[ALEMBIC DEBUG] sqlalchemy.url before override = {config.get_main_option('sqlalchemy.url')}",
    flush=True,
    file=sys.stderr,
)
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)
    print(
        f"[ALEMBIC DEBUG] sqlalchemy.url after override = {database_url}",
        flush=True,
        file=sys.stderr,
    )

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    print(f"[ALEMBIC DEBUG] run_migrations_offline: url = {url}", flush=True, file=sys.stderr)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    ini_url = config.get_section(config.config_ini_section, {}).get("sqlalchemy.url", "NOT SET")
    main_url = config.get_main_option("sqlalchemy.url")
    print(
        f"[ALEMBIC DEBUG] run_migrations_online: ini_section url = {ini_url}",
        flush=True,
        file=sys.stderr,
    )
    print(
        f"[ALEMBIC DEBUG] run_migrations_online: main_option url = {main_url}",
        flush=True,
        file=sys.stderr,
    )
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        echo=True,
    )
    print("[ALEMBIC DEBUG] engine created, connecting...", flush=True, file=sys.stderr)
    with connectable.connect() as connection:
        print("[ALEMBIC DEBUG] connected, configuring context...", flush=True, file=sys.stderr)
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            print("[ALEMBIC DEBUG] running migrations...", flush=True, file=sys.stderr)
            context.run_migrations()
            print("[ALEMBIC DEBUG] migrations complete", flush=True, file=sys.stderr)


if context.is_offline_mode():
    print(
        "[ALEMBIC DEBUG] offline mode, running run_migrations_offline", flush=True, file=sys.stderr
    )
    run_migrations_offline()
else:
    print("[ALEMBIC DEBUG] online mode, running run_migrations_online", flush=True, file=sys.stderr)
    run_migrations_online()
