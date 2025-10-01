"""Minimal FastAPI application used by the test-suite fixtures."""
from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health():
    """Return a static health payload for the stub environment."""

    return {"status": "ok"}


__all__ = ["app"]
