"""Security configuration smoke tests.

These tests verify that security-sensitive configuration is properly enforced.
"""

import os
import pytest


class TestJWTSecretEnforcement:
    """Tests for JWT secret enforcement in production."""

    def test_jwt_secret_required_in_production(self, monkeypatch):
        """Missing JWT_SECRET_KEY in production should raise ValueError."""
        # Clear any existing values
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.delenv("ENV", raising=False)

        # Import the function fresh
        from importlib import reload
        import backend.main as main_module

        # The module should raise on import when JWT_SECRET_KEY is missing in prod
        with pytest.raises(ValueError, match="JWT_SECRET_KEY must be set"):
            reload(main_module)

    def test_jwt_secret_allowed_in_dev(self, monkeypatch):
        """JWT_SECRET_KEY can be omitted in development environments."""
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        monkeypatch.setenv("ENV", "development")

        from backend.main import _get_jwt_secret

        secret = _get_jwt_secret()
        assert secret == "insecure-dev-secret-do-not-use-in-prod"

    def test_jwt_secret_used_when_set(self, monkeypatch):
        """JWT_SECRET_KEY is used when provided."""
        monkeypatch.setenv("JWT_SECRET_KEY", "my-secure-secret")

        from backend.main import _get_jwt_secret

        secret = _get_jwt_secret()
        assert secret == "my-secure-secret"


class TestAdminCredentialsEnforcement:
    """Tests for admin credentials enforcement in production."""

    def test_admin_creds_required_in_production(self, monkeypatch):
        """Missing admin credentials in production should raise ValueError."""
        monkeypatch.delenv("AUTH_ADMIN_USER", raising=False)
        monkeypatch.delenv("AUTH_ADMIN_PASSWORD", raising=False)
        monkeypatch.delenv("ENV", raising=False)

        from backend.api.auth import _get_admin_credentials

        with pytest.raises(ValueError, match="AUTH_ADMIN_USER and AUTH_ADMIN_PASSWORD must be set"):
            _get_admin_credentials()

    def test_admin_creds_allowed_in_dev(self, monkeypatch):
        """Admin credentials can be omitted in development environments."""
        monkeypatch.delenv("AUTH_ADMIN_USER", raising=False)
        monkeypatch.delenv("AUTH_ADMIN_PASSWORD", raising=False)
        monkeypatch.setenv("ENV", "development")

        from backend.api.auth import _get_admin_credentials

        user, password = _get_admin_credentials()
        assert user == "dev-admin"
        assert password == "dev-password-insecure"

    def test_admin_creds_used_when_set(self, monkeypatch):
        """Admin credentials are used when provided."""
        monkeypatch.setenv("AUTH_ADMIN_USER", "myuser")
        monkeypatch.setenv("AUTH_ADMIN_PASSWORD", "mypassword")

        from backend.api.auth import _get_admin_credentials

        user, password = _get_admin_credentials()
        assert user == "myuser"
        assert password == "mypassword"


class TestPDPMiddlewareUserExtraction:
    """Tests for PDP middleware user_id extraction."""

    def test_no_default_user_id(self):
        """PDP middleware should NOT return a default user_id."""
        from unittest.mock import MagicMock
        from backend.backend.pdp.middleware import PDPMiddleware

        middleware = PDPMiddleware(app=MagicMock())
        request = MagicMock()
        request.headers = {}
        request.state = MagicMock(spec=[])  # No user_id attribute

        user_id = middleware._extract_user_id(request)
        assert user_id is None, "PDP should NOT invent a default user_id"

    def test_extracts_user_id_from_header(self):
        """PDP middleware should extract user_id from X-User-ID header."""
        from unittest.mock import MagicMock
        from backend.backend.pdp.middleware import PDPMiddleware

        middleware = PDPMiddleware(app=MagicMock())
        request = MagicMock()
        request.headers = {"X-User-ID": "42"}
        request.state = MagicMock(spec=[])

        user_id = middleware._extract_user_id(request)
        assert user_id == 42
