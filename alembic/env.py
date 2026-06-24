import logging.config

from sqlalchemy import engine_from_config, pool
from alembic import context

from app.core.database import Base
from app.core.config import settings, ALEMBIC_LOGGING_CONF
from app.modules import init_all_models_for_metadata

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.\
logging.config.dictConfig(ALEMBIC_LOGGING_CONF)

# MetaData object for 'autogenerate' support
target_metadata = Base.metadata
init_all_models_for_metadata()
# target_metadata - лишь ссылка на объект в памяти,
# его изменения отразится и здесь, так что всё в порядке

db_url = settings.psycopg2_db_url

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    context.configure(
        url=db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    alembic_conf = config.get_section(config.config_ini_section, {})
    alembic_conf['sqlalchemy.url'] = db_url
    connectable = engine_from_config(
        alembic_conf,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
