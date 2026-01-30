"""Connector factory for production and stub integrations."""

from __future__ import annotations

import os
from typing import Any, Callable, Dict

from backend.services.aconex import AconexClient
from backend.services.primavera import PrimaveraClient
from backend.services.vision import VisionClient


def _stub_connector(name: str) -> Dict[str, str]:
    return {"status": "stubbed", "connector": name}


def get_connector(connector_type: str) -> Any:
    """
    Factory for connectors: returns live or stub based on env.
    """
    use_stubs = os.getenv("USE_STUB_CONNECTORS", "true").lower() == "true"

    connectors: Dict[str, Callable[[], Any]] = {
        "aconex": (lambda: _stub_connector("aconex")) if use_stubs else AconexClient,
        "p6": (lambda: _stub_connector("p6")) if use_stubs else PrimaveraClient,
        "primavera": (lambda: _stub_connector("primavera")) if use_stubs else PrimaveraClient,
        "vision": (lambda: _stub_connector("vision")) if use_stubs else VisionClient,
    }

    if connector_type not in connectors:
        raise ValueError(f"Unknown connector: {connector_type}")

    return connectors[connector_type]()
