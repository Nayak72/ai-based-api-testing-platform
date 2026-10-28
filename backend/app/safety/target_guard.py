"""Target safety guard — validates URLs against LOCAL/ONLINE mode rules."""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse

import structlog

logger = structlog.get_logger()


class TargetPolicy(StrEnum):
    LOCAL = "local"
    ONLINE = "online"


RunMode = TargetPolicy


@dataclass
class GuardDecision:
    allowed: bool
    reason: str
    classification: str  # "loopback", "private", "link_local", "metadata", "public", "invalid"


class TargetGuard:
    """
    Validates request targets against the active mode policy.

    LOCAL:  allows loopback + private/RFC1918 + host.docker.internal; blocks public.
    ONLINE: allows public IPs only; blocks loopback, private, link-local, metadata.
    """

    SAFE_LOCAL_HOSTS = {"host.docker.internal", "localhost"}

    def __init__(
        self,
        mode: TargetPolicy | str = TargetPolicy.LOCAL,
        owned_allowlist: list[str] | set[str] | None = None,
    ) -> None:
        if isinstance(mode, str):
            self.mode = TargetPolicy(mode.lower())
        else:
            self.mode = mode
        self.owned_allowlist = set(owned_allowlist or [])

    def check_url(self, url: str) -> tuple[bool, str]:
        """Convenience method returning (allowed, reason)."""
        decision = self.check(url, self.mode, self.owned_allowlist)
        return decision.allowed, decision.reason

    def check(
        self,
        url: str,
        policy: TargetPolicy,
        allowlist: set[str] = frozenset(),
    ) -> GuardDecision:
        """Return a GuardDecision for the given URL and policy."""
        url = (url or "").strip().strip("'\"")
        if not url:
            return GuardDecision(False, "URL is required", "invalid")

        # Auto-prefix http:// or https:// if protocol was omitted
        if not (url.startswith("http://") or url.startswith("https://")):
            if url.startswith(("localhost", "127.0.0.1", "0.0.0.0", "host.docker.internal")):
                url = f"http://{url}"
            else:
                url = f"https://{url}"

        try:
            parsed = urlparse(url)
        except Exception:
            return GuardDecision(False, "URL parse error", "invalid")

        # Scheme check
        if parsed.scheme not in ("http", "https"):
            return GuardDecision(
                False,
                f"Scheme '{parsed.scheme}' not allowed; use http or https",
                "invalid",
            )

        # Credentials in URL
        if parsed.username or parsed.password:
            return GuardDecision(False, "Credentials embedded in URL are not allowed", "invalid")

        host = parsed.hostname or ""
        if not host:
            return GuardDecision(False, "No host in URL", "invalid")

        classification = self._classify_host(host)

        # An allowlist can narrow which targets a deployment permits, but it
        # must never bypass IP-class safety checks.
        allowlisted = host.casefold() in {entry.casefold() for entry in allowlist}

        if policy == TargetPolicy.LOCAL:
            allowed = classification in ("loopback", "private", "local_special")
            if not allowed:
                return GuardDecision(
                    False,
                    f"LOCAL mode: public host '{host}' is not allowed (use ONLINE mode or add to allowlist)",
                    classification,
                )
            return GuardDecision(True, f"LOCAL mode: {classification} host allowed", classification)

        elif policy == TargetPolicy.ONLINE:
            if classification in ("loopback", "private", "link_local", "metadata", "local_special", "mixed"):
                return GuardDecision(
                    False,
                    f"ONLINE mode: {classification} host '{host}' blocked for safety",
                    classification,
                )
            if classification == "invalid":
                return GuardDecision(False, f"Cannot resolve host '{host}'", classification)
            suffix = " (allowlisted)" if allowlisted else ""
            return GuardDecision(True, f"ONLINE mode: public host allowed{suffix}", classification)

        return GuardDecision(False, "Unknown policy", "invalid")

    def _classify_host(self, host: str) -> str:
        if host in self.SAFE_LOCAL_HOSTS:
            return "loopback"
        try:
            # Attempt direct IP parse first (no DNS)
            ip = ipaddress.ip_address(host)
            return self._classify_ip(str(ip))
        except ValueError:
            pass
        # DNS resolution
        try:
            addrs = socket.getaddrinfo(host, None)
            ips = {info[4][0] for info in addrs}
        except socket.gaierror:
            return "invalid"

        classifications = {self._classify_ip(ip) for ip in ips}

        # Do not allow a hostname that resolves to both a safe and unsafe
        # network. Selecting a different A/AAAA record later would bypass the
        # original check.
        if len(classifications) > 1:
            return "mixed"

        # Priority: most dangerous first
        for cls in ("metadata", "link_local", "loopback", "private", "public"):
            if cls in classifications:
                return cls
        return "invalid"

    def _classify_ip(self, ip_str: str) -> str:
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return "invalid"

        # Normalise IPv4-mapped IPv6 before applying address-class policy.
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            return self._classify_ip(str(ip.ipv4_mapped))

        # Link-local and metadata check first (169.254.x.x)
        if ip.is_link_local:
            return "metadata" if str(ip).startswith("169.254.") else "link_local"
        if ip.is_loopback:
            return "loopback"
        if ip.is_private:
            return "private"
        if ip.is_multicast or ip.is_unspecified or ip.is_reserved or not ip.is_global:
            return "invalid"
        return "public"


target_guard = TargetGuard()
