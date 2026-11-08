#!/usr/bin/env python3
"""Side-by-side annotated Grafana captures: main jar (left) vs branch jar (right)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHOT = ROOT / "craft-demo/results/dashboard/screenshots"
LEFT = SHOT / "grafana-pagination-main-jar.png"
RIGHT = SHOT / "grafana-pagination-branch-jar.png"
OUT = SHOT / "grafana-pagination-side-by-side.png"
METRICS = ROOT / "craft-demo/results/dashboard/pagination-jar-metrics.json"


def caption_lines() -> list[str]:
    if METRICS.exists():
        m = json.loads(METRICS.read_text())
        main_b = m.get("main", {}).get("bytes", "?")
        br_d = m.get("branch_default", {}).get("bytes", "?")
        br_10 = m.get("branch_page10", {}).get("bytes", "?")
        return [
            f"HTTP bytes (live curl): main list={main_b:,}  |  branch default={br_d:,}  branch size=10={br_10:,}"
        ]
    return ["See pagination-jar-metrics.json — run scripts/start_dual_jars.sh"]


def crop_halves(raw: Path) -> None:
    """Split a single pagination-compare kiosk capture into left/right panes."""
    try:
        from PIL import Image
    except ImportError:
        return
    img = Image.open(raw).convert("RGB")
    w, h = img.size
    mid = w // 2
    img.crop((0, 0, mid - 6, h)).save(LEFT, optimize=True)
    img.crop((mid + 6, 0, w, h)).save(RIGHT, optimize=True)


def main() -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow required")
        return
    raw = SHOT / "grafana-pagination-compare-raw.png"
    if raw.exists() and (not LEFT.exists() or not RIGHT.exists()):
        crop_halves(raw)
    if not LEFT.exists() or not RIGHT.exists():
        print(f"Missing {LEFT} or {RIGHT}; run scripts/capture_grafana_live.sh")
        return

    li = Image.open(LEFT).convert("RGB")
    ri = Image.open(RIGHT).convert("RGB")
    w1, h1 = li.size
    w2, h2 = ri.size
    h = max(h1, h2)
    w = w1 + w2 + 20
    header = 70
    canvas = Image.new("RGB", (w, h + header), (24, 27, 31))
    canvas.paste(li, (0, header))
    canvas.paste(ri, (w1 + 20, header))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 20)
        font_sm = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 16)
    except OSError:
        font = font_sm = ImageFont.load_default()
    draw.text((12, 8), "Before: main jar :18080 (unbounded list)", fill=(255, 180, 120), font=font)
    draw.text((w1 + 32, 8), "After: branch jar :8080 (paged list)", fill=(140, 220, 160), font=font)
    y = 36
    for line in caption_lines():
        draw.text((12, y), line, fill=(210, 210, 210), font=font_sm)
        y += 22
    x = w1 + 10
    draw.line((x, header, x, header + h), fill=(80, 80, 80), width=2)
    canvas.save(OUT, format="PNG", optimize=True)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
