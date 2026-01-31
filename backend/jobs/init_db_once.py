#!/usr/bin/env python3
"""One-off DB initialization.
Run: python -m backend.jobs.init_db_once
"""
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger("init_db_once")


def main() -> int:
    try:
        from backend.backend.db import engine, Base
    except Exception as exc:
        logger.error(f"Failed importing DB engine/Base: {exc}")
        return 1

    try:
        import backend.backend.models  # noqa: F401
    except Exception as exc:
        logger.warning(f"Models import warning (verify models module path): {exc}")

    try:
        logger.info("Creating tables...")
        Base.metadata.create_all(bind=engine)

        from sqlalchemy import inspect
        insp = inspect(engine)
        tables = set(insp.get_table_names())
        logger.info("Tables present: %s", sorted(tables))
        if "policies" not in tables:
            logger.error("CRITICAL: 'policies' table missing after create_all()")
            return 1

        logger.info("OK: DB initialized")
        return 0
    except Exception as exc:
        logger.error(f"DB init failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
