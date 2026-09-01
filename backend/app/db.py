from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import BASE_DIR, settings


class Base(DeclarativeBase):
    pass


def _sqlite_url() -> str:
    if settings.database_url.startswith("sqlite:///./"):
        data_dir = BASE_DIR / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        db_name = settings.database_url.rsplit("/", 1)[-1]
        return f"sqlite:///{data_dir / db_name}"
    return settings.database_url


engine = create_engine(
    _sqlite_url(),
    connect_args={"check_same_thread": False},
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@event.listens_for(engine, "connect")
def _sqlite_wal(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
