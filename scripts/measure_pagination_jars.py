#!/usr/bin/env python3
"""JSON snapshot of curl bytes/time for main vs branch list endpoints."""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.request


def measure(url: str) -> dict:
    proc = subprocess.run(
        ["curl", "-s", "-o", "/tmp/psj-body", "-w", "%{http_code} %{size_download} %{time_total}", url],
        capture_output=True,
        text=True,
        check=False,
    )
    parts = proc.stdout.strip().split()
    code, size, t = parts[0], int(parts[1]), float(parts[2])
    meta = {}
    if code == "200" and "size=10" in url:
        data = json.loads(urllib.request.urlopen(url, timeout=60).read())
        meta = {
            "totalElements": data.get("totalElements"),
            "totalPages": data.get("totalPages"),
            "playersOnPage": len(data.get("players", [])),
        }
    return {"url": url, "http": int(code), "bytes": size, "seconds": t, **meta}


def main() -> None:
    out = {
        "main": measure("http://127.0.0.1:18080/v1/players"),
        "branch_default": measure("http://127.0.0.1:8080/v1/players"),
        "branch_page10": measure("http://127.0.0.1:8080/v1/players?page=0&size=10"),
    }
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
