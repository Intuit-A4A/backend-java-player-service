#!/usr/bin/env bash
# Live Grafana: refresh stack, dual jars, browser screenshots + annotations + side-by-side.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SHOT="$ROOT/craft-demo/results/dashboard/screenshots"
DASH="$ROOT/craft-demo/results/dashboard"
mkdir -p "$SHOT" "$DASH"

echo "== Observability stack =="
sh "$ROOT/craft-demo/observability/up.sh"
sleep 4

echo "== JVMs (branch + main) =="
sh "$ROOT/scripts/start_dual_jars.sh"

echo "== Reload Prometheus (dual scrape) =="
curl -sf -X POST http://localhost:9090/-/reload >/dev/null 2>&1 || docker restart player-prometheus >/dev/null 2>&1 || true
sleep 5

# Extra list traffic for compare dashboard
for _ in 1 2 3; do
  curl -sf -o /dev/null http://127.0.0.1:18080/v1/players || true
  curl -sf -o /dev/null 'http://127.0.0.1:8080/v1/players?page=0&size=10' || true
  sleep 1
done

if [[ -x "$ROOT/scripts/capture_grafana_browser.py" ]]; then
  python3 "$ROOT/scripts/capture_grafana_browser.py"
else
  echo "Browser automation: use scripts/capture_grafana_browser.py or Cursor browser MCP"
fi

# Annotate availability if raw exists
if [[ -f "$DASH/grafana-ramp-raw.png" ]]; then
  python3 "$ROOT/scripts/annotate_ramp_screenshot.py" \
    "$DASH/grafana-ramp-raw.png" "$SHOT/grafana-ramp-annotated.png"
  cp "$SHOT/grafana-ramp-annotated.png" "$DASH/grafana-ramp-annotated.png"
fi

python3 "$ROOT/scripts/build_pagination_side_by_side.py"
python3 "$ROOT/scripts/build_pagination_grafana_story.py" || true

sh "$ROOT/scripts/capture_grafana_screenshots.sh"

echo "Open:"
echo "  http://localhost:3000/d/availability/availability"
echo "  http://localhost:3000/d/pagination-compare/pagination-compare"
echo "Screenshots: $SHOT"
