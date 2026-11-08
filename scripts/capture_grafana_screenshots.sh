#!/usr/bin/env bash
# Capture Grafana views into craft-demo/results/dashboard/screenshots/
# NOTE: Grafana /render requires the image-renderer plugin (not in default up.sh).
# This script uses browser-free fallbacks: keep annotated ramp + build story composite.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/craft-demo/results/dashboard/screenshots"
mkdir -p "$OUT"

# Remove broken tiny "PNG" error pages from render API
for f in "$OUT/grafana-dashboard-full.png" "$OUT/grafana-panel-tomcat-busy.png"; do
  if [[ -f "$f" ]] && [[ "$(wc -c <"$f")" -lt 20000 ]]; then
    rm -f "$f"
    echo "Removed invalid render output: $f (install grafana-image-renderer or screenshot in browser)"
  fi
done

if [[ -f "$ROOT/craft-demo/results/dashboard/grafana-ramp-annotated.png" ]]; then
  cp "$ROOT/craft-demo/results/dashboard/grafana-ramp-annotated.png" \
    "$OUT/grafana-ramp-annotated.png"
fi
if [[ -f "$ROOT/craft-demo/results/dashboard/grafana-ramp-raw.png" ]]; then
  cp "$ROOT/craft-demo/results/dashboard/grafana-ramp-raw.png" \
    "$OUT/grafana-ramp-raw.png"
fi

python3 "$ROOT/scripts/build_pagination_grafana_story.py" || true

cat >"$OUT/README.md" <<'EOF'
# Grafana screenshot results

**Do not use** `grafana-dashboard-full.png` from `/render` unless you installed [Grafana Image Renderer](https://grafana.com/grafana/plugins/grafana-image-renderer/). Default Docker Grafana returns an error page saved as a tiny PNG.

| File | Use in talk |
|------|-------------|
| **`grafana-ramp-annotated.png`** | Primary — Tomcat busy + per-API completed counts (baseline ramp) |
| **`grafana-pagination-side-by-side.png`** | Main vs branch jar (pagination) |
| **`grafana-pagination-compare-annotated.png`** | Live pagination compare dashboard |
| **`grafana-dashboard-live-annotated.png`** | Live availability dashboard |
| `grafana-players-pagination-story.png` | Legacy single-pane summary |
| `grafana-ramp-raw.png` | Unannotated ramp window |

## Pagination before/after

HTTP + ramp table: [`../../demo-capture/pagination-before-after.md`](../../demo-capture/pagination-before-after.md)

Numbers: [`../presenter-scorecard.md`](../presenter-scorecard.md) (per player API).

## Refresh workflow

```bash
python3 scripts/ramp_load_test.py baseline    # optional, for new data
python3 scripts/annotate_ramp_screenshot.py # update annotated PNG
sh scripts/capture_grafana_screenshots.sh
BUILD_MAIN=1 sh scripts/capture_pagination_before_after.sh
python3 scripts/render_ramp_scorecard.py
```

## Browser screenshot (manual)

1. `sh craft-demo/observability/up.sh`
2. Open http://localhost:3000/d/availability/availability
3. Time range: last 15m after a ramp
4. Save full window as `grafana-browser-capture.png` in this folder
EOF

echo "Done. Valid PNGs in $OUT"
