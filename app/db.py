from sqlmodel import SQLModel, create_engine
from sqlalchemy import event
from sqlalchemy.engine import Engine

# SQLite database file (named params enforced via SQLModel/SQLAlchemy usage)
DATABASE_URL = "sqlite:///./data/app.db"

# create_engine with check_same_thread False for uvicorn async workers
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    # Enable WAL and foreign keys on each new connection
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()


def init_db():
    SQLModel.metadata.create_all(engine)
    # Database schema changes should be applied via Alembic migrations.
    # The `alembic/versions/0002_add_unit_remark.py` revision was added to
    # add the `remark` column to `unit` — run `alembic upgrade head` in
    # your environment to apply it. We avoid making schema changes at
    # runtime in `init_db()` to keep behavior predictable in production.
