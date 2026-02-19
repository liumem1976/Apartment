import os
import shutil
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config


# Module-level setup: ensure env var is set before test modules import `app`.
data_dir = Path("./data")
data_dir.mkdir(exist_ok=True)
test_db_path = data_dir / "test.db"
if test_db_path.exists():
    try:
        test_db_path.unlink()
    except Exception:
        try:
            shutil.rmtree(str(test_db_path))
        except Exception:
            pass

test_db_url = f"sqlite:///{str(test_db_path)}"
os.environ["DATABASE_URL"] = test_db_url

# Run alembic migrations once at import time so `app` imports see the schema.
cfg = Config("alembic.ini")
cfg.set_main_option("sqlalchemy.url", test_db_url)
command.upgrade(cfg, "head")


@pytest.fixture(scope="session", autouse=True)
def prepare_test_db():
    """Session-scoped fixture available to tests; cleanup happens after session."""
    yield
    # teardown: remove test db file
    try:
        if test_db_path.exists():
            test_db_path.unlink()
    except Exception:
        pass
