#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
JAVA="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17}/bin/java"
BRANCH_JAR="$ROOT/target/player-service-java-0.0.1-SNAPSHOT.jar"
MAIN_JAR="${MAIN_JAR:-$ROOT/target/player-service-java-main-demo.jar}"

stop_port() {
  local pid
  pid=$(lsof -ti :"$1" 2>/dev/null || true)
  [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
}

if [[ ! -f "$BRANCH_JAR" ]]; then
  (cd "$ROOT" && mvn -q -DskipTests package)
fi
if [[ ! -f "$MAIN_JAR" ]]; then
  sh "$ROOT/scripts/build_demo_main_jar.sh"
fi

for p in 8080 8081 18080 18081; do stop_port "$p"; done
sleep 1

nohup "$JAVA" -jar "$BRANCH_JAR" >>/tmp/player-branch.log 2>&1 &
nohup "$JAVA" -jar "$MAIN_JAR" --server.port=18080 --management.server.port=18081 >>/tmp/player-main.log 2>&1 &

for _ in $(seq 1 90); do
  if curl -sf -o /dev/null http://127.0.0.1:8080/v1/players/aardsda01 \
    && curl -sf -o /dev/null http://127.0.0.1:18080/v1/players/aardsda01; then
    break
  fi
  sleep 1
done

curl -sf -o /dev/null http://127.0.0.1:18080/v1/players || true
curl -sf -o /dev/null 'http://127.0.0.1:8080/v1/players?page=0&size=10' || true

mkdir -p "$ROOT/craft-demo/results/dashboard"
python3 "$ROOT/scripts/measure_pagination_jars.py" \
  >"$ROOT/craft-demo/results/dashboard/pagination-jar-metrics.json"

echo "Dual jars: branch :8080/:8081  main :18080/:18081"
