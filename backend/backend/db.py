import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")


def _connect_args_for_url(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    if url.startswith("postgresql") or url.startswith("postgres"):
        return {"connect_timeout": 5}
    return {}


connect_args = _connect_args_for_url(DATABASE_URL)
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


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
