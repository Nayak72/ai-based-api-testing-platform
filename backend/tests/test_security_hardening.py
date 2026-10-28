"""Regression tests for fail-closed security boundaries."""

from types import SimpleNamespace

import pytest


def test_encrypt_value_never_falls_back_to_plaintext(monkeypatch):
    import app.safety.secrets as secrets
    from app.core.security import encrypt_value

    monkeypatch.setattr(secrets, "get_settings", lambda: SimpleNamespace(secrets_encryption_key=None))
    with pytest.raises(RuntimeError):
        encrypt_value("sensitive-token")


def test_refresh_token_is_not_serialized_in_token_response():
    from app.api.schemas.auth import TokenResponse

    response = TokenResponse(access_token="access", expires_in=60)
    assert response.model_dump()["refresh_token"] is None
