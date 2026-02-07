from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, create_engine
from pathlib import Path
import os

# Base dir = repository root (one level above the package)
BASE_DIR = Path(__file__).resolve().parent.parent

# Default data dir next to repository root; ensure it exists
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Allow overriding via environment variable (useful in CI). Normalize
# any sqlite path to an absolute path under the repository to avoid
# "unable to open database file" when working directories differ.
env_database_url = os.getenv("DATABASE_URL")
if env_database_url:
    database_url = env_database_url
else:
    database_url = f"sqlite:///{(DATA_DIR / 'app.db').as_posix()}"

if database_url.startswith("sqlite:///"):
    # extract file part
    file_path = database_url.replace("sqlite:///", "", 1)
    p = Path(file_path)
    if not p.is_absolute():
        # Make path absolute relative to repo root
        p = (BASE_DIR / p).resolve()
        # ensure parent exists
        p.parent.mkdir(parents=True, exist_ok=True)
        database_url = f"sqlite:///{p.as_posix()}"
    else:
        # absolute path: ensure parent exists
        p.parent.mkdir(parents=True, exist_ok=True)

# create_engine with check_same_thread False for uvicorn async workers
engine = create_engine(
    database_url,
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
