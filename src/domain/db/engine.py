"""Engine factory and schema creation for the SQLite persistence layer.

Schema migrations are intentionally out of scope (no Alembic): the database
is always rebuildable from the JSON archive via scripts/import-runs.py, so
dropping the file and re-importing is the migration path.
"""

import json
import logging
import domain.db.tables

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, create_engine

from config import Config, DB_DIR


logger = logging.getLogger(__name__)


def create_db_engine(config: Config) -> Engine:
    """Create the (single, shared) engine from config.database_url,
    defaulting to a SQLite file under resource/db/."""
    
    url = config.database_url
    if not url:
        DB_DIR.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{(DB_DIR / 'llm-review.sqlite').as_posix()}"

    is_sqlite = url.startswith("sqlite")
    engine = create_engine(
        url,
        echo=config.db_echo,
        connect_args={"check_same_thread": False} if is_sqlite else {},
        json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
    )
    if is_sqlite:
        event.listen(engine, "connect", _set_sqlite_pragmas)

    logger.info("Database engine created: %s", url)
    
    init_db(engine=engine);
    
    return engine


def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")  
    cursor.execute("PRAGMA journal_mode=WAL") 
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def init_db(engine: Engine) -> None:
    """Create all tables if they do not exist."""

    SQLModel.metadata.create_all(engine)
