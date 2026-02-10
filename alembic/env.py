from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import create_engine, engine_from_config, pool
from sqlmodel import SQLModel

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# Ensure alembic has a database URL; prefer project setting if not provided in alembic.ini
try:
    db_mod = __import__("app.db", fromlist=["DATABASE_URL"])
    project_db_url = getattr(db_mod, "DATABASE_URL", None)
    if project_db_url and not config.get_main_option("sqlalchemy.url"):
        config.set_main_option("sqlalchemy.url", project_db_url)
except Exception:
    # best-effort: if import fails, rely on alembic.ini to provide the URL
    pass

# add your model's MetaData object here
import sys  # noqa: E402

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app.models import *  # noqa: F401,F403,E402

target_metadata = SQLModel.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    section = config.get_section(config.config_ini_section) or {}
    # engine_from_config expects a 'sqlalchemy.url' in the section dict.
    # If it's missing, try to use the project's DATABASE_URL as a fallback.
    if not section.get("sqlalchemy.url"):
        try:
            from app.db import DATABASE_URL as project_db_url
        except Exception:
            project_db_url = None

        if project_db_url:
            connectable = create_engine(project_db_url, poolclass=pool.NullPool)
        else:
            # Fall back to engine_from_config which will raise a helpful error
            connectable = engine_from_config(
                section,
                prefix="sqlalchemy.",
                poolclass=pool.NullPool,
            )
    else:
        connectable = engine_from_config(
            section,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
