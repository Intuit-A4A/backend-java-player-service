#!/usr/bin/env python3
"""Same concurrent GET /v1/players against main (:18080) and branch (:8080)."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "craft-demo/results/dashboard/pagination-load-compare.json"
CONCURRENCY = 30
ROUNDS = 1
TIMEOUT = 20


def one(url: str) -> str:
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            resp.read()
            return f"http_{resp.status}"
    except urllib.error.HTTPError as e:
        return f"http_{e.code}"
    except Exception as e:
        name = type(e).__name__
        if "timeout" in name.lower() or "timeout" in str(e).lower():
            return "client_timeout"
        return f"client_{name}"


def burst(url: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = [pool.submit(one, url) for _ in range(CONCURRENCY * ROUNDS)]
        for fut in as_completed(futures):
            key = fut.result()
            counts[key] = counts.get(key, 0) + 1
    return counts


def main() -> None:
    main_url = "http://127.0.0.1:18080/v1/players"
    branch_url = "http://127.0.0.1:8080/v1/players"
    print(f"load {CONCURRENCY * ROUNDS} calls, concurrency {CONCURRENCY}, timeout {TIMEOUT}s", flush=True)
    print("main ...", flush=True)
    main_counts = burst(main_url)
    print(main_counts, flush=True)
    print("branch ...", flush=True)
    branch_counts = burst(branch_url)
    print(branch_counts, flush=True)
    payload = {
        "heap": "128m on both JVMs",
        "concurrency": CONCURRENCY,
        "attempts_each": CONCURRENCY * ROUNDS,
        "timeout_s": TIMEOUT,
        "note": "Main 500s are OutOfMemoryError while materializing the full roster. Branch returns one page and stays 200.",
        "main": {"url": main_url, "outcomes": main_counts},
        "branch": {"url": branch_url, "outcomes": branch_counts},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
