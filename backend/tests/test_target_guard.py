"""Tests for TargetGuard."""

import pytest

from app.safety.target_guard import RunMode, TargetGuard


@pytest.fixture
def local_guard():
    return TargetGuard(mode=RunMode.LOCAL, owned_allowlist=[])


@pytest.fixture
def online_guard():
    return TargetGuard(mode=RunMode.ONLINE, owned_allowlist=[])


def test_localhost_allowed_in_local(local_guard):
    ok, _ = local_guard.check_url("http://localhost:8080/api")
    assert ok


def test_loopback_blocked_in_online(online_guard):
    ok, reason = online_guard.check_url("http://127.0.0.1/api")
    assert not ok
    assert "blocked" in reason.lower() or "private" in reason.lower() or "loopback" in reason.lower()


def test_link_local_blocked_in_online(online_guard):
    ok, reason = online_guard.check_url("http://169.254.169.254/latest/meta-data/")
    assert not ok


def test_private_range_blocked_in_online(online_guard):
    ok, reason = online_guard.check_url("http://192.168.1.1/api")
    assert not ok


def test_public_url_allowed_in_online(online_guard):
    ok, _ = online_guard.check_url("https://93.184.216.34/v1")
    assert ok


def test_public_hostname_with_dns(online_guard):
    from unittest.mock import patch

    with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("93.184.216.34", 443))]):
        ok, _ = online_guard.check_url("https://api.example.com/v1")
        assert ok


def test_owned_allowlist():
    guard = TargetGuard(mode=RunMode.ONLINE, owned_allowlist=["myapi.internal.example.com"])
    ok, _ = guard.check_url("https://myapi.internal.example.com/api")
    assert ok


def test_url_whitespace_and_auto_protocol(local_guard):
    # Leading whitespace and quotes
    ok, _ = local_guard.check_url("  http://localhost:8080/api  ")
    assert ok

    # Auto-protocol for localhost
    ok2, _ = local_guard.check_url("localhost:8080/api")
    assert ok2
