#!/usr/bin/env python3
"""Overlay ramp run summary on a Grafana screenshot PNG."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "craft-demo" / "results" / "dashboard"


def player_totals(stage_data):
    totals = stage_data["summary"]["totalsByApi"]
    apis = ["GET /v1/players", "GET /v1/players/{id}"]
    attempts = 0
    ok = 0
    for api in apis:
        counts = totals.get(api, {})
        attempts += sum(counts.values())
        ok += counts.get("http_200", 0)
    return ok, attempts


def main():
    image_in = Path(sys.argv[1]) if len(sys.argv) > 1 else DASH / "grafana-ramp-raw.png"
    image_out = Path(sys.argv[2]) if len(sys.argv) > 2 else DASH / "grafana-ramp-annotated.png"
    baseline = json.loads((DASH / "ramp-baseline.json").read_text())
    timeouts = json.loads((DASH / "ramp-timeouts.json").read_text())
    b_ok, b_attempts = player_totals(baseline)
    t_ok, t_attempts = player_totals(timeouts)
    peak = max(
        baseline["stepSnapshots"],
        key=lambda s: s.get("tomcatThreadsBusy") or 0,
    )
    lines = [
        "Run 1 baseline (chat on Tomcat, hang on :11434)",
        f"  Player calls: {b_attempts} (28 list + 28 by-id) → {b_ok} HTTP 200, rest client_timeout",
        f"  Tomcat busy peaked at {peak.get('tomcatThreadsBusy')} (max pool 40)",
        "Run 2 timeouts (chat async, 2s ollama4j timeout, same hang)",
        f"  Player calls: {t_attempts} (same count) → {t_ok} HTTP 200",
        "  Chat HTTP 503 (read timeout); Tomcat stays low",
        "Busy = workers actively serving a request (saturation signal).",
        "Same player attempt count; more 200 ⇒ availability improves.",
    ]
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        (DASH / "grafana-ramp-annotation.txt").write_text("\n".join(lines) + "\n")
        print("Pillow missing; wrote", DASH / "grafana-ramp-annotation.txt")
        return
    img = Image.open(image_in).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    pad = 16
    line_h = 22
    box_h = pad * 2 + line_h * len(lines)
    box_w = min(img.width - 40, 920)
    draw.rectangle([10, 10, 10 + box_w, 10 + box_h], fill=(255, 255, 255, 230))
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Andale Mono.ttf", 14)
    except OSError:
        font = ImageFont.load_default()
    y = 10 + pad
    for line in lines:
        draw.text((20, y), line, fill=(20, 20, 20, 255), font=font)
        y += line_h
    out = Image.alpha_composite(img, overlay)
    out.convert("RGB").save(image_out)
    print("wrote", image_out)


if __name__ == "__main__":
    main()
