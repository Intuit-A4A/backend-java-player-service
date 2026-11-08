#!/usr/bin/env python3
"""Build a one-page presenter scorecard from ramp-baseline.json and ramp-timeouts.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "craft-demo" / "results" / "dashboard"

PLAYER_APIS = (
    "GET /v1/players",
    "GET /v1/players/{id}",
)

CHAT_APIS = (
    "GET /v1/chat/list-models",
    "POST /v1/chat",
)


def peak_busy(data: dict) -> float:
    snaps = data.get("stepSnapshots") or []
    if not snaps:
        return 0.0
    return max(float(s.get("tomcatThreadsBusy") or 0) for s in snaps)


def format_outcomes(outcomes: dict) -> str:
    parts = []
    for label in sorted(outcomes.keys()):
        parts.append(f"{label}: **{outcomes[label]}**")
    return "; ".join(parts) if parts else "—"


def player_totals(totals: dict) -> tuple[int, int, int]:
    ok = 0
    timeouts = 0
    total = 0
    for api in PLAYER_APIS:
        for label, count in totals.get(api, {}).items():
            total += count
            if label == "http_200":
                ok += count
            if label == "client_timeout":
                timeouts += count
    return ok, timeouts, total


def load(name: str) -> dict:
    return json.loads((DASH / name).read_text())


def main() -> None:
    baseline = load("ramp-baseline.json")
    timeouts = load("ramp-timeouts.json")
    b_tot = baseline["summary"]["totalsByApi"]
    t_tot = timeouts["summary"]["totalsByApi"]

    b_ok, b_ct, b_all = player_totals(b_tot)
    t_ok, t_ct, t_all = player_totals(t_tot)

    lines = [
        "# Presenter scorecard (from ramp JSON)",
        "",
        "Use this **instead of** waiting on Grafana during the talk. "
        "Numbers are from checked-in `ramp-baseline.json` / `ramp-timeouts.json`.",
        "",
        "Screenshots (frozen Grafana): [`screenshots/`](screenshots/) — see README.",
        "",
        "## Player API — before vs after",
        "",
        "| Player endpoint | **Before (baseline)** | **After (timeouts)** |",
        "|-----------------|----------------------|----------------------|",
    ]

    for api in PLAYER_APIS:
        lines.append(
            f"| `{api}` | {format_outcomes(b_tot.get(api, {}))} "
            f"| {format_outcomes(t_tot.get(api, {}))} |"
        )

    lines.extend(
        [
            "",
            f"| **Player totals** | **{b_ok}** `http_200`, **{b_ct}** `client_timeout` (of {b_all}) "
            f"| **{t_ok}** `http_200`, **{t_ct}** `client_timeout` (of {t_all}) |",
            "",
            "## Chat API (context)",
            "",
            "| Chat endpoint | **Before (baseline)** | **After (timeouts)** |",
            "|---------------|----------------------|----------------------|",
        ]
    )

    for api in CHAT_APIS:
        lines.append(
            f"| `{api}` | {format_outcomes(b_tot.get(api, {}))} "
            f"| {format_outcomes(t_tot.get(api, {}))} |"
        )

    lines.extend(
        [
            "",
            "## Pool saturation",
            "",
            "| Signal | **Before** | **After** |",
            "|--------|------------|-----------|",
            f"| Tomcat busy (peak) | **{peak_busy(baseline):.0f}** / 40 | **{peak_busy(timeouts):.0f}** / 40 |",
            "",
            "## Story in one sentence",
            "",
            "**Before:** pool fills → **player APIs** stop finishing → load script records `client_timeout`. "
            "**After:** chat returns **503** quickly on a side pool → Tomcat stays idle → **both player APIs** finish **http_200**.",
            "",
            "## Mermaid (optional slide)",
            "",
            "```mermaid",
            "flowchart LR",
            "  subgraph before [Baseline profile]",
            "    H1[Hang peer 11434]",
            "    T1[Tomcat busy 40]",
            "    P1[Players client_timeout]",
            "    H1 --> T1 --> P1",
            "  end",
            "  subgraph after [Timeouts profile]",
            "    H2[Same hang peer]",
            "    T2[Tomcat busy ~2]",
            "    P2[Players http_200]",
            "    C2[Chat http_503]",
            "    H2 --> T2",
            "    H2 --> C2",
            "    T2 --> P2",
            "  end",
            "```",
            "",
            "## Regenerate",
            "",
            "```bash",
            "python3 scripts/ramp_load_test.py baseline",
            "python3 scripts/ramp_load_test.py timeouts",
            "python3 scripts/render_ramp_scorecard.py",
            "sh scripts/capture_grafana_screenshots.sh",
            "```",
            "",
        ]
    )

    out = DASH / "presenter-scorecard.md"
    out.write_text("\n".join(lines))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
