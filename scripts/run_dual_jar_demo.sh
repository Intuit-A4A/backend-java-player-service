#!/usr/bin/env bash
# Run branch jar (8080) + main-style jar (18080) for pagination / Grafana compare.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
JAVA="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17}/bin/java"
BRANCH_JAR="$ROOT/target/player-service-java-0.0.1-SNAPSHOT.jar"
MAIN_JAR="${MAIN_JAR:-$ROOT/target/player-service-java-main-demo.jar}"

stop_one() {
  local port=$1
  local pid
  pid=$(lsof -ti :"$port" 2>/dev/null || true)
  [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
}

cleanup() {
  stop_one 8080
  stop_one 8081
  stop_one 18080
  stop_one 18081
}
trap cleanup EXIT

if [[ ! -f "$BRANCH_JAR" ]]; then
  (cd "$ROOT" && mvn -q -DskipTests package)
fi
if [[ ! -f "$MAIN_JAR" ]]; then
  sh "$ROOT/scripts/build_demo_main_jar.sh"
  MAIN_JAR="$ROOT/.worktrees/main-jar/target/player-service-java-0.0.1-SNAPSHOT.jar"
fi

cleanup
sleep 1

nohup "$JAVA" -jar "$BRANCH_JAR" >>/tmp/player-branch.log 2>&1 &
nohup "$JAVA" -jar "$MAIN_JAR" --server.port=18080 --management.server.port=18081 >>/tmp/player-main.log 2>&1 &

for _ in $(seq 1 60); do
  if curl -sf -o /dev/null http://127.0.0.1:8080/v1/players/aardsda01 \
    && curl -sf -o /dev/null http://127.0.0.1:18080/v1/players/aardsda01; then
  then_ready=true
  break
  fi
  sleep 1
done
[[ "${then_ready:-}" == true ]] || { echo "JVMs not ready; see /tmp/player-*.log" >&2; exit 1; }

# Warm list endpoints so Prometheus histograms populate both jars.
curl -sf -o /dev/null http://127.0.0.1:18080/v1/players
curl -sf -o /dev/null 'http://127.0.0.1:8080/v1/players?page=0&size=10'
curl -sf -o /dev/null 'http://127.0.0.1:8080/v1/players'

python3 "$ROOT/scripts/measure_pagination_jars.py" \
  >"$ROOT/craft-demo/results/dashboard/pagination-jar-metrics.json"

echo "Dual jars up: branch :8080  main :18080"
echo "Metrics: :8081 (branch) :18081 (main)"
echo "Wrote craft-demo/results/dashboard/pagination-jar-metrics.json"
echo "Leave running; Ctrl+C to stop both."
wait
