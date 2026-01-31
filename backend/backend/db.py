import logging
import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger(__name__)


def _normalize_database_url(raw_url: str) -> str:
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql://", 1)
    return raw_url


def _sqlite_url_for_path(path: str) -> str:
    abs_path = Path(path).expanduser().resolve()
    return f"sqlite:////{abs_path}"


def _resolve_database_url() -> tuple[str, bool, str | None]:
    raw_database_url = os.getenv("DATABASE_URL")
    if raw_database_url:
        return _normalize_database_url(raw_database_url), True, None

    sqlite_path = os.getenv("SQLITE_PATH")
    if not sqlite_path:
        default_path = Path("/var/data/app.db") if Path("/var/data").exists() else Path("./app.db")
        sqlite_path = str(default_path)
    return _sqlite_url_for_path(sqlite_path), False, sqlite_path


DATABASE_URL, DATABASE_URL_SET, SQLITE_PATH = _resolve_database_url()


def _connect_args_for_url(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    if url.startswith("postgresql") or url.startswith("postgres"):
        return {"connect_timeout": 5}
    return {}


connect_args = _connect_args_for_url(DATABASE_URL)
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

logger.info(
    "Database configured: dialect=%s database_url_set=%s sqlite_path=%s",
    engine.url.get_backend_name(),
    DATABASE_URL_SET,
    SQLITE_PATH,
)


def _import_models() -> None:
    """Import all SQLAlchemy models so metadata is populated."""

    from backend.backend.pdp import models as _pdp_models  # noqa: F401
    from backend.events import models as _event_models  # noqa: F401
    from backend.hydration import models as _hydration_models  # noqa: F401
    from backend.learning import models as _learning_models  # noqa: F401
    from backend.ops import models as _ops_models  # noqa: F401
    from backend.regression import models as _regression_models  # noqa: F401
    from backend.runtime import models as _runtime_models  # noqa: F401


_import_models()


def init_db() -> None:
    """Ensure all tables exist for the current metadata."""

    _import_models()
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
