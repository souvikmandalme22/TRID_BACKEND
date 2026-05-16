import os

from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# =========================================================
# CONFIG
# =========================================================

config = context.config

# =========================================================
# DATABASE URL
# =========================================================

db_url = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql+psycopg2://trid_user:password@localhost:5432/trid_db",
)

config.set_main_option(
    "sqlalchemy.url",
    db_url,
)

# =========================================================
# LOGGING
# =========================================================

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# =========================================================
# IMPORT BASE
# =========================================================

from app.db.session import Base

# =========================================================
# IMPORT ALL MODELS
# =========================================================

import app.models.pricing
import app.models.user
import app.models.otp
import app.models.refresh_token
import app.models.order
import app.models.order_status_log
import app.models.payment

# =========================================================
# METADATA
# =========================================================

target_metadata = Base.metadata

# =========================================================
# OFFLINE MIGRATIONS
# =========================================================

def run_migrations_offline() -> None:

    url = config.get_main_option(
        "sqlalchemy.url"
    )

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named"
        },
    )

    with context.begin_transaction():
        context.run_migrations()


# =========================================================
# ONLINE MIGRATIONS
# =========================================================

def run_migrations_online() -> None:

    connectable = engine_from_config(
        config.get_section(
            config.config_ini_section,
            {}
        ),
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


# =========================================================
# EXECUTION
# =========================================================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
