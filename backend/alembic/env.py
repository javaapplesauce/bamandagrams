# backend/alembic/env.py (excerpt)
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Interpret the config file (alembic.ini)
config = context.config
fileConfig(config.config_file_name)

# Import ORM models to populate metadata
from backend.app import models
target_metadata = models.Base.metadata

# Override the SQLAlchemy URL from env (to use DATABASE_URL)
import os
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    config.set_main_option('sqlalchemy.url', DATABASE_URL)

def run_migrations_offline():
    context.configure(
        url=config.get_main_option('sqlalchemy.url'),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    engine = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.", poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
