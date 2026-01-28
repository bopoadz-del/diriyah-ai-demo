"""Connector base interfaces for hydration sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Optional, Tuple


class BaseConnector(ABC):
    """Base connector interface."""

    def __init__(self, config: Dict[str, Any], secrets_ref: Optional[str] = None) -> None:
        self.config = config
        self.secrets_ref = secrets_ref

    @abstractmethod
    def validate_config(self) -> None:
        """Validate connector config and raise ValueError on errors."""

    @abstractmethod
    def list_changes(self, cursor_json: Optional[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Return list of changed items and updated cursor."""

    @abstractmethod
    def get_metadata(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize metadata for the connector item."""

    @abstractmethod
    def download(self, item: Dict[str, Any]) -> bytes:
        """Download content for item and return bytes."""

    def delete_supported(self) -> bool:
        return False


NormalizedItem = Dict[str, Any]
NormalizedChange = Dict[str, Any]
