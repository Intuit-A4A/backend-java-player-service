#!/usr/bin/env python3
"""Capture Grafana dashboards via headless Chrome (osascript open + screencapture fallback)."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOT = ROOT / "craft-demo/results/dashboard/screenshots"
METRICS = ROOT / "craft-demo/results/dashboard/pagination-jar-metrics.json"

URLS = {
    "availability": "http://localhost:3000/d/availability/availability?orgId=1&from=now-15m&to=now&kiosk",
    "pagination": "http://localhost:3000/d/pagination-compare/pagination-compare?orgId=1&from=now-15m&to=now&kiosk",
}


def metrics_caption(prefix: str) -> list[str]:
    if not METRICS.exists():
        return [f"{prefix}: run start_dual_jars.sh for live curl bytes"]
    m = json.loads(METRICS.read_text())
    if prefix == "main":
        x = m.get("main", {})
        return [
            f"GET /v1/players — HTTP {x.get('http')}  {x.get('bytes', 0):,} bytes  {x.get('seconds', 0):.3f}s",
            "main jar @ :18080 — unbounded findAll()",
        ]
    x = m.get("branch_default", {})
    y = m.get("branch_page10", {})
    return [
        f"GET /v1/players — HTTP {x.get('http')}  {x.get('bytes', 0):,} bytes (page 50)",
        f"GET ?size=10 — {y.get('bytes', 0):,} bytes  totals {y.get('totalElements')} players",
        "branch jar @ :8080 — offset pagination",
    ]


def try_playwright(name: str, url: str, out: Path) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(url, wait_until="networkidle", timeout=120_000)
        time.sleep(3)
        page.screenshot(path=str(out), full_page=True)
        browser.close()
    print("playwright", out)
    return True


def try_mac_screencapture(url: str, out: Path) -> bool:
    """Open dashboard in default browser, capture front window (macOS only)."""
    subprocess.run(["open", url], check=False)
    time.sleep(8)
    proc = subprocess.run(
        ["screencapture", "-x", "-l", _front_window_id(), str(out)],
        capture_output=True,
    )
    if proc.returncode == 0 and out.stat().st_size > 50_000:
        print("screencapture", out)
        return True
    return False


def _front_window_id() -> str:
    script = """
    tell application "System Events"
      set frontApp to name of first application process whose frontmost is true
    end tell
    tell application frontApp
      set winId to id of front window
    end tell
    return winId
    """
    proc = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return proc.stdout.strip() or "0"


def capture_pair() -> None:
    SHOT.mkdir(parents=True, exist_ok=True)
    targets = [
        ("grafana-dashboard-live.png", URLS["availability"]),
        ("grafana-pagination-compare-raw.png", URLS["pagination"]),
    ]
    for fname, url in targets:
        raw = SHOT / fname.replace("-raw", "").replace(".png", "-raw.png") if "compare" in fname else SHOT / "grafana-dashboard-live-raw.png"
        if fname == "grafana-dashboard-live.png":
            raw = SHOT / "grafana-dashboard-live-raw.png"
        if not try_playwright(fname, url, raw):
            if not try_mac_screencapture(url, raw):
                print("Skip", url, "(install playwright or capture manually)")
                continue
        ann = raw.with_name(raw.name.replace("-raw", "-annotated"))
        if "pagination" in raw.name:
            ann_main = SHOT / "grafana-pagination-main-jar.png"
            ann_branch = SHOT / "grafana-pagination-branch-jar.png"
            # Same full compare dashboard on both sides with different overlay emphasis
            subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts/annotate_dashboard_png.py"),
                    str(raw),
                    str(ann_main),
                    "TITLE:Before — main jar",
                    *metrics_caption("main"),
                ],
                check=False,
            )
            subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts/annotate_dashboard_png.py"),
                    str(raw),
                    str(ann_branch),
                    "TITLE:After — branch jar",
                    *metrics_caption("branch"),
                ],
                check=False,
            )
        else:
            subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts/annotate_dashboard_png.py"),
                    str(raw),
                    str(SHOT / "grafana-dashboard-live-annotated.png"),
                    "TITLE:Availability — live window",
                    "Tomcat busy + per-API HTTP completions",
                    "Run ramp_load_test baseline then timeouts to populate",
                ],
                check=False,
            )
            # feed annotate_ramp pipeline
            dash = ROOT / "craft-demo/results/dashboard"
            dash.mkdir(parents=True, exist_ok=True)
            (dash / "grafana-ramp-raw.png").write_bytes(raw.read_bytes())


def main() -> None:
    capture_pair()


if __name__ == "__main__":
    main()
