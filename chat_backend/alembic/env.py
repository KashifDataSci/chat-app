import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# 1. Load environment variables at the very top
from dotenv import load_dotenv
load_dotenv()

# This is the Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 2. FORCE TEMPORARY NONE METADATA
# This bypasses loading your broken models so Alembic can run without crashing.
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # Read from .env first; fall back to alembic.ini if not found
    url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Dynamically inject the .env URL into the alembic config context
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        config.set_main_option("sqlalchemy.url", database_url)

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()