#!/usr/bin/env bash
# Pagination before (main: unbounded list) vs after (branch: paged).
# Writes craft-demo/results/demo-capture/pagination-before-after.md
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/craft-demo/results/demo-capture/pagination-before-after.md"
WORKTREE="$ROOT/.worktrees/pagination-main"
JAVA="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17}/bin/java"
MAIN_PORT=18080
BRANCH_URL="${BRANCH_URL:-http://localhost:8080}"

probe_ok() {
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' "$BRANCH_URL/v1/players/aardsda01" || true)
  [[ "$code" == "200" ]]
}

measure() {
  local url="$1"
  curl -s -o /tmp/pagination-body.json -w '%{http_code} %{size_download} %{time_total}' "$url"
}

cleanup_main() {
  if [[ -n "${MAIN_PID:-}" ]] && kill -0 "$MAIN_PID" 2>/dev/null; then
    kill "$MAIN_PID" 2>/dev/null || true
    wait "$MAIN_PID" 2>/dev/null || true
  fi
}
trap cleanup_main EXIT

if ! probe_ok; then
  echo "ERROR: $BRANCH_URL not healthy (GET /v1/players/{id} != 200). Restart Spring Boot after DROP TABLE demo." >&2
  exit 1
fi

echo "Measuring branch (after) at $BRANCH_URL ..."
AFTER_DEFAULT=$(measure "$BRANCH_URL/v1/players")
AFTER_PAGE10=$(measure "$BRANCH_URL/v1/players?page=0&size=10")
AFTER_META=$(curl -s "$BRANCH_URL/v1/players?page=0&size=10" | python3 -c "import sys,json;d=json.load(sys.stdin); print(d.get('totalElements'), d.get('totalPages'), len(d.get('players',[])))")

BEFORE_LINE="(not run — start main on $MAIN_PORT or run script with BUILD_MAIN=1)"
BEFORE_BYTES=""
BEFORE_TIME=""

if [[ "${BUILD_MAIN:-0}" == "1" ]]; then
  echo "Building main in worktree ..."
  git worktree add -f "$WORKTREE" main 2>/dev/null || true
  (cd "$WORKTREE" && mvn -q -DskipTests package)
  JAR="$WORKTREE/target/player-service-java-0.0.1-SNAPSHOT.jar"
  "$JAVA" -jar "$JAR" --server.port="$MAIN_PORT" >/tmp/pagination-main.log 2>&1 &
  MAIN_PID=$!
  for _ in $(seq 1 60); do
    if curl -sf -o /dev/null "$MAIN_PORT/v1/players" 2>/dev/null || curl -sf -o /dev/null "http://127.0.0.1:$MAIN_PORT/v1/players"; then
      break
    fi
    sleep 1
  done
  BEFORE=$(measure "http://127.0.0.1:$MAIN_PORT/v1/players")
  BEFORE_LINE="$BEFORE"
  read -r _ BEFORE_BYTES BEFORE_TIME <<<"$BEFORE"
fi

read -r AFTER_DEFAULT_CODE AFTER_DEFAULT_BYTES AFTER_DEFAULT_TIME <<<"$AFTER_DEFAULT"
read -r AFTER_PAGE10_CODE AFTER_PAGE10_BYTES AFTER_PAGE10_TIME <<<"$AFTER_PAGE10"

RATIO=$(python3 - <<PY
b=int("$AFTER_DEFAULT_BYTES") or 1
s=int("$AFTER_PAGE10_BYTES") or 1
print(f"{b/s:.1f}x")
PY
)

cat >"$OUT" <<EOF
# Pagination — before vs after (captured test)

Generated: $(date -Iseconds)

## HTTP comparison

| Scenario | URL | HTTP | Bytes | Time (s) |
|----------|-----|------|-------|----------|
| **Before (main)** unbounded list | \`GET /v1/players\` | ${BEFORE_LINE:-see §2.3 — full roster in one response} |
| **After (branch)** default page (50) | \`GET /v1/players\` | $AFTER_DEFAULT_CODE | $AFTER_DEFAULT_BYTES | $AFTER_DEFAULT_TIME |
| **After (branch)** small page | \`GET /v1/players?page=0&size=10\` | $AFTER_PAGE10_CODE | $AFTER_PAGE10_BYTES | $AFTER_PAGE10_TIME |

**After metadata (size=10):** totalElements, totalPages, row count = \`$AFTER_META\`

**Payload ratio (default page vs size=10):** ~${RATIO}× smaller body on size=10.

### Dual jars (recommended)

\`\`\`bash
sh scripts/build_demo_main_jar.sh
sh scripts/start_dual_jars.sh
# metrics in craft-demo/results/dashboard/pagination-jar-metrics.json
\`\`\`

## Grafana — player list behavior under load

Pagination bounds **per-request** size; ramp JSON shows **whether** \`GET /v1/players\` completes during chat saturation:

| Profile | \`GET /v1/players\` outcomes (totals) |
|---------|---------------------------------------|
| **Before fix (baseline chat)** | 6× \`http_200\`, 22× \`client_timeout\` |
| **After fix (timeouts profile)** | 28× \`http_200\` |

See [\`../dashboard/presenter-scorecard.md\`](../dashboard/presenter-scorecard.md).

**Screenshots (use these, not live render API):**

| File | What it shows |
|------|----------------|
| [\`../dashboard/screenshots/grafana-ramp-annotated.png\`](../dashboard/screenshots/grafana-ramp-annotated.png) | Tomcat + **GET /v1/players** completed counts during baseline ramp |
| [\`../dashboard/screenshots/grafana-players-pagination-story.png\`](../dashboard/screenshots/grafana-players-pagination-story.png) | Presenter composite (scorecard + curl + still) |

**Do not open** \`grafana-dashboard-full.png\` from \`/render\` (no image-renderer plugin — tiny error PNG). Use the story + annotated files above.

## Regenerate Grafana stills

\`\`\`bash
sh craft-demo/observability/up.sh
# open http://localhost:3000/d/availability/availability after dashboard loads
# screenshot manually, or: python3 scripts/build_pagination_grafana_story.py
\`\`\`
EOF

echo "Wrote $OUT"
