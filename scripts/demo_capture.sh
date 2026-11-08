#!/usr/bin/env bash
# Smoke capture for craft-demo (run with app up on 8080/8081).
# Writes craft-demo/results/demo-capture/<timestamp>-after/summary.md
# WARNING: includes DROP TABLE PLAYERS — restart the JVM after running.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CAP="$ROOT/craft-demo/results/demo-capture/$(date +%Y%m%d-%H%M%S)-after"
mkdir -p "$CAP"

{
  echo "# Demo capture (branch: $(git -C "$ROOT" branch --show-current 2>/dev/null || echo unknown))"
  echo "Captured: $(date -Iseconds)"
  echo ""
} >"$CAP/summary.md"

record() {
  local title="$1"
  shift
  {
    echo "## $title"
    echo '```'
    "$@" 2>&1 | head -c 6000
    echo '```'
    echo ""
  } >>"$CAP/summary.md"
}

record "3.2 missing id → 404" curl -si localhost:8080/v1/players/no-such-player
record "3.3 page metadata" bash -c "curl -s 'localhost:8080/v1/players?page=0&size=10' | python3 -c \"import sys,json;d=json.load(sys.stdin); print(json.dumps({k:d[k] for k in ('page','size','totalElements','totalPages')}, indent=2)); print('players', len(d['players']))\""
record "3.3 size 101 → 400" curl -si 'localhost:8080/v1/players?size=101'
record "3.3 payload size default vs page10" bash -c 'curl -s -o /dev/null -w "default_page bytes=%{size_download} time=%{time_total}s\n" localhost:8080/v1/players; curl -s -o /dev/null -w "page0_size10 bytes=%{size_download} time=%{time_total}s\n" "localhost:8080/v1/players?page=0&size=10"'
record "3.1 readiness 8081" curl -s localhost:8081/actuator/health/readiness
record "3.1 mode" curl -s localhost:8080/v1/reliability/mode
record "3.1 SLI" bash -c 'curl -s -X POST localhost:8080/v1/reliability/sli/reset >/dev/null; curl -s -o /dev/null localhost:8080/v1/players/aardsda01; curl -s localhost:8080/v1/reliability/sli'

record "3.2 DROP TABLE → 500 (restart app after)" bash -c '
  jsession=$(curl -s http://localhost:8080/h2-console/ | sed -n "s/.*jsessionid=\([a-f0-9]*\).*/\1/p")
  curl -s -o /dev/null "http://localhost:8080/h2-console/login.jsp?jsessionid=$jsession"
  curl -s -o /dev/null \
    --data-urlencode "language=en" \
    --data-urlencode "setting=Generic H2 (Embedded)" \
    --data-urlencode "name=Generic H2 (Embedded)" \
    --data-urlencode "driver=org.h2.Driver" \
    --data-urlencode "url=jdbc:h2:mem:playerdb" \
    --data-urlencode "user=sa" \
    --data-urlencode "password=" \
    "http://localhost:8080/h2-console/login.do?jsessionid=$jsession"
  curl -s -o /dev/null --data-urlencode "sql=DROP TABLE PLAYERS" \
    "http://localhost:8080/h2-console/query.do?jsessionid=$jsession"
  curl -si localhost:8080/v1/players/aardsda01 | head -n 20
'

echo "$CAP" >"$ROOT/craft-demo/results/demo-capture/LATEST_AFTER.txt"
echo "Wrote $CAP/summary.md"
echo "If DROP TABLE ran, restart: mvn spring-boot:run (or your jar)"
