#!/usr/bin/env python3
"""Build a single presenter PNG: Grafana ramp crop + pagination curl summary."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOT = ROOT / "craft-demo/results/dashboard/screenshots"
SRC = SHOT / "grafana-ramp-annotated.png"
OUT = SHOT / "grafana-players-pagination-story.png"

SUMMARY = """
Players API — pagination & availability

Curl (branch):  default page ~23 KB  |  ?size=10 ~4.7 KB
Ramp baseline:  GET /v1/players → 6×200, 22×client_timeout
Ramp timeouts:  GET /v1/players → 28×http_200

Use presenter-scorecard.md for full tables.
"""


def main() -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow not installed; copy grafana-ramp-annotated.png as story fallback")
        if SRC.exists():
            OUT.write_bytes(SRC.read_bytes())
            print(f"Wrote {OUT} (copy of annotated ramp)")
        return

    if not SRC.exists():
        print(f"Missing {SRC}")
        return

    img = Image.open(SRC).convert("RGB")
    w, h = img.size
    # Use upper ~55% (Tomcat + players list panel in typical layout)
    crop = img.crop((0, 0, w, int(h * 0.55)))

    pad_h = 120
    canvas = Image.new("RGB", (w, crop.height + pad_h), color=(24, 27, 31))
    canvas.paste(crop, (0, 0))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 18)
    except OSError:
        font = ImageFont.load_default()
    y = crop.height + 8
    for line in SUMMARY.strip().splitlines():
        draw.text((12, y), line, fill=(220, 220, 220), font=font)
        y += 22

    canvas.save(OUT, format="PNG", optimize=True)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
