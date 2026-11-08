#!/usr/bin/env python3
"""Add a text overlay box to a dashboard screenshot."""
from __future__ import annotations

import sys
from pathlib import Path


def annotate(image_in: Path, image_out: Path, lines: list[str], *, title: str = "") -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        image_out.write_bytes(image_in.read_bytes())
        Path(str(image_out) + ".txt").write_text("\n".join(lines))
        print("Pillow missing; copied raw image +", image_out.with_suffix(".txt"))
        return

    img = Image.open(image_in).convert("RGBA")
    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    pad = 14
    line_h = 20
    all_lines = ([title] if title else []) + lines
    box_h = pad * 2 + line_h * len(all_lines)
    box_w = min(img.width - 24, 980)
    draw.rectangle([8, 8, 8 + box_w, 8 + box_h], fill=(255, 255, 255, 235))
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Andale Mono.ttf", 13)
        font_b = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 14)
    except OSError:
        font = font_b = ImageFont.load_default()
    y = 8 + pad
    for i, line in enumerate(all_lines):
        f = font_b if i == 0 and title else font
        draw.text((18, y), line, fill=(25, 25, 25, 255), font=f)
        y += line_h
    out = Image.alpha_composite(img, overlay)
    out.convert("RGB").save(image_out)
    print("wrote", image_out)


def main() -> None:
    if len(sys.argv) < 3:
        print("usage: annotate_dashboard_png.py in.png out.png [line...]")
        sys.exit(1)
    image_in = Path(sys.argv[1])
    image_out = Path(sys.argv[2])
    title = ""
    lines = sys.argv[3:]
    if lines and lines[0].startswith("TITLE:"):
        title = lines[0][6:]
        lines = lines[1:]
    annotate(image_in, image_out, lines, title=title)


if __name__ == "__main__":
    main()
