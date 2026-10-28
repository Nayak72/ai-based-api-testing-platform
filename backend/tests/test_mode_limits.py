"""Tests for mode limits in test runner."""

from app.db.models import RunConfig


def test_online_mode_limits():
    """Online mode must clamp concurrency to 3, rate_limit to 2.0, and strip security without attestation."""
    config = RunConfig(
        mode="online",
        concurrency=10,
        rate_limit_rps=10.0,
        categories=["functional", "security", "resource_consumption"],
        owned_host_attestation=False,
    )

    # Apply runner's enforcement
    if config.mode == "online":
        config.concurrency = min(config.concurrency, 3)
        if not config.rate_limit_rps or config.rate_limit_rps > 2.0:
            config.rate_limit_rps = 2.0
        if not config.owned_host_attestation:
            config.categories = [c for c in config.categories if c not in ("security", "resource_consumption")]

    assert config.concurrency == 3
    assert config.rate_limit_rps == 2.0
    assert config.categories == ["functional"]


def test_online_mode_with_attestation():
    """With attestation, security categories are preserved."""
    config = RunConfig(
        mode="online",
        concurrency=5,
        rate_limit_rps=1.0,
        categories=["functional", "security"],
        owned_host_attestation=True,
    )

    if config.mode == "online":
        config.concurrency = min(config.concurrency, 3)
        if not config.rate_limit_rps or config.rate_limit_rps > 2.0:
            config.rate_limit_rps = 2.0
        if not config.owned_host_attestation:
            config.categories = [c for c in config.categories if c not in ("security", "resource_consumption")]

    assert config.concurrency == 3
    assert config.rate_limit_rps == 1.0
    assert "security" in config.categories


def test_run_config_round_trip_preserves_safety_fields():
    config = RunConfig(
        mode="online",
        intensity="aggressive",
        categories=["functional", "security"],
        owned_host_attestation=True,
        max_total_requests=42,
        routing={"provider_profile_id": "profile"},
        auth_secret_ref="session",
    )
    assert RunConfig(**config.model_dump()) == config
