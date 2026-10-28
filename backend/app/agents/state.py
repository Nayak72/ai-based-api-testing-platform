"""Session state shared across all agents in the LangGraph pipeline."""

from __future__ import annotations

from typing import TypedDict


class SessionState(TypedDict, total=False):
    session_id: str
    user_id: str
    spec_id: str
    mode: str  # "local" | "online"
    routing: dict  # RoutingConfig-like dict
    categories: list[str]
    plan: dict | None  # PlannerAgent output
    test_cases: list[dict]
    critic_report: dict | None
    run_id: str | None
    results: list[dict]
    triage: list[dict]
    report_id: str | None
    errors: list[str]
    interrupts: list[str]  # pending interrupt types
    human_input: dict  # collected human inputs (plan edits, auth tokens)
    agentic: bool
    base_url: str | None
    auth: dict | None  # {type, token}
    auth_secondary: dict | None
    owned_host_attestation: bool
    intensity: str
    max_tests_per_endpoint: int
    max_total_requests: int
