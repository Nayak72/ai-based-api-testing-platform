#!/usr/bin/env python3
"""Evaluation harness: runs sessions and scores them against GROUND_TRUTH.json."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import time
from typing import Any

import httpx
import yaml


DEFAULT_BACKEND = "http://localhost:8000"
VULNSHOP_GROUND_TRUTH = Path(__file__).parent.parent.parent / "demo_targets/vulnshop/GROUND_TRUTH.json"


def load_ground_truth(path: Path = VULNSHOP_GROUND_TRUTH) -> dict[str, Any]:
    with open(path) as f:
        return json.load(f)


async def wait_for_run(client: httpx.AsyncClient, run_id: str, timeout: int = 300) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        r = await client.get(f"/api/v1/runs/{run_id}")
        run = r.json()
        if run["status"] in ("completed", "failed", "error"):
            return run
        await asyncio.sleep(3)
    raise TimeoutError(f"Run {run_id} did not complete in {timeout}s")


def score_results(results: list[dict], ground_truth: dict) -> dict[str, Any]:
    """Score results against ground truth expected findings."""
    expected_findings = {f["finding_id"] for f in ground_truth.get("expected_findings", [])}
    found = set()
    false_positives = []

    for r in results:
        if r.get("status") == "failed":
            fid = r.get("metadata", {}).get("finding_id") or r.get("category")
            if fid and fid in expected_findings:
                found.add(fid)
            elif fid:
                false_positives.append(fid)

    missing = expected_findings - found
    recall = len(found) / len(expected_findings) if expected_findings else 0
    precision = len(found) / (len(found) + len(false_positives)) if (found or false_positives) else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

    return {
        "total_expected": len(expected_findings),
        "found": len(found),
        "missing": list(missing),
        "false_positives": false_positives,
        "recall": round(recall, 3),
        "precision": round(precision, 3),
        "f1": round(f1, 3),
    }


async def run_eval(config_path: str, backend_url: str = DEFAULT_BACKEND) -> None:
    with open(config_path) as f:
        if config_path.endswith(".yaml") or config_path.endswith(".yml"):
            config = yaml.safe_load(f)
        else:
            config = json.load(f)

    gt = load_ground_truth()
    token = config.get("auth_token", "")

    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient(base_url=backend_url, headers=headers, timeout=60.0) as client:
        # Create run
        run_data = {
            "spec_id": config["spec_id"],
            "name": config.get("name", "eval-run"),
            "config": config.get("run_config", {}),
        }
        r = await client.post("/api/v1/runs", json=run_data)
        r.raise_for_status()
        run = r.json()
        run_id = run["id"]
        print(f"Created run {run_id}")

        # Wait for completion
        completed = await wait_for_run(client, run_id)
        print(f"Run status: {completed['status']}")
        print(f"Summary: {completed['summary']}")

        # Fetch results
        r = await client.get(f"/api/v1/runs/{run_id}/results", params={"page_size": 500})
        results = r.json().get("results", [])

        # Score
        scores = score_results(results, gt)
        print("\n=== EVAL SCORES ===")
        print(f"  Expected findings: {scores['total_expected']}")
        print(f"  Found:             {scores['found']}")
        print(f"  Missing:           {scores['missing']}")
        print(f"  False positives:   {scores['false_positives']}")
        print(f"  Recall:            {scores['recall']:.1%}")
        print(f"  Precision:         {scores['precision']:.1%}")
        print(f"  F1:                {scores['f1']:.3f}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("config", help="Eval config YAML/JSON")
    parser.add_argument("--backend", default=DEFAULT_BACKEND)
    args = parser.parse_args()
    asyncio.run(run_eval(args.config, args.backend))

