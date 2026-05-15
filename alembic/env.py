import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

config = context.config

# Use DATABASE_URL_SYNC from environment (psycopg2 — sync driver required by alembic)
db_url = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql+psycopg2://trid_user:password@localhost:5432/trid_db",
)
config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so autogenerate can detect them
from app.database.base import Base  # noqa
import app.models.pricing_snapshot   # noqa
import app.models.user                # noqa
import app.models.otp                 # noqa
import app.models.refresh_token       # noqa
import app.models.order               # noqa
import app.models.order_status_log    # noqa
import app.models.payment             # noqa

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
