#!/usr/bin/env bash
# Craft Demo helper: capture SLI + readiness while Ollama is down/up.
#
# Usage:
#   ./scripts/availability-demo.sh baseline   # app on :8080 with legacy profile
#   ./scripts/availability-demo.sh after      # app on :8080 with hardened profile
#
# Traffic mix (default = production-like ~99% -> ~99.9% story):
#   PLAYER_REQUESTS=1000  CHAT_REQUESTS=9
#   demo-player-error-every=1000 + header X-Demo-Fault-Injection:1
#   → 1 player 5xx / 1000 (99.90% core); injection off without the header
#   Legacy blend: 999/(1000+9) = 99.01% perceived
#
# Optional teaching mode (extreme 50% blend):
#   MIX=equal ./scripts/availability-demo.sh baseline
set -euo pipefail

PHASE="${1:-after}"
BASE_URL="${BASE_URL:-http://localhost:8080}"
OUT_DIR="${OUT_DIR:-craft-demo/results}"
MIX="${MIX:-realistic}"   # realistic | equal
PLAYER_ID="${PLAYER_ID:-aardsda01}"
DEMO_FAULT_HEADER="X-Demo-Fault-Injection: 1"
mkdir -p "$OUT_DIR"

if [[ "$MIX" == "equal" ]]; then
  PLAYER_REQUESTS="${PLAYER_REQUESTS:-10}"
  CHAT_REQUESTS="${CHAT_REQUESTS:-10}"
else
  PLAYER_REQUESTS="${PLAYER_REQUESTS:-1000}"
  CHAT_REQUESTS="${CHAT_REQUESTS:-9}"
fi

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

drive_traffic() {
  local label="$1"
  echo "==> Driving traffic ($label): players=$PLAYER_REQUESTS chat=$CHAT_REQUESTS mix=$MIX"
  local i
  for i in $(seq 1 "$PLAYER_REQUESTS"); do
    curl -s --max-time 15 -H "$DEMO_FAULT_HEADER" -o /dev/null "$BASE_URL/v1/players/$PLAYER_ID" || true
    if (( i % 100 == 0 )); then
      echo "    players progress: $i/$PLAYER_REQUESTS"
    fi
  done
  for i in $(seq 1 "$CHAT_REQUESTS"); do
    curl -s --max-time 15 -o /dev/null "$BASE_URL/v1/chat/list-models" || true
  done
}

echo "==> Phase: $PHASE @ $(ts)"
echo "==> Checking service mode"
curl -sf "$BASE_URL/v1/reliability/mode" | tee "$OUT_DIR/${PHASE}-mode.json"
echo

echo "==> Reset SLI window"
curl -sf -X POST "$BASE_URL/v1/reliability/sli/reset" > /dev/null

echo "==> Stopping Ollama container (simulating dependency outage)"
docker stop ollama >/dev/null 2>&1 || true
sleep 2

drive_traffic "Ollama DOWN"

echo "==> Readiness while Ollama DOWN"
code=$(curl -s -o "$OUT_DIR/${PHASE}-readiness-ollama-down.json" -w "%{http_code}" \
  "$BASE_URL/actuator/health/readiness" || true)
echo "HTTP $code"
python3 - <<PY
import json
p="$OUT_DIR/${PHASE}-readiness-ollama-down.json"
body=open(p).read()
try:
  data=json.loads(body)
except Exception:
  data={"raw": body[:300]}
data["_httpStatus"]= int("$code") if "$code".isdigit() else "$code"
print(json.dumps(data, indent=2))
open(p,"w").write(json.dumps(data, indent=2))
PY
echo "==> Overall /actuator/health while Ollama DOWN"
curl -s -o "$OUT_DIR/${PHASE}-health-ollama-down.json" -w "HTTP %{http_code}\n" \
  "$BASE_URL/actuator/health" || true

echo "==> SLI while Ollama DOWN"
curl -sf "$BASE_URL/v1/reliability/sli" | tee "$OUT_DIR/${PHASE}-sli-ollama-down.json"
echo
python3 - <<PY
import json
s=json.load(open("$OUT_DIR/${PHASE}-sli-ollama-down.json"))
print(
    f"    perceived={s.get('perceivedAvailabilityPct')}  core={s.get('coreAvailabilityPct')}  "
    f"serviceMeetsSLO={s.get('serviceMeetsSlo')}  (judgedBy={s.get('sloJudgedBy')})"
)
print(f"    players={s['players']} chat={s['chat']}")
PY

echo "==> Starting Ollama container"
docker start ollama >/dev/null 2>&1 || true
for i in $(seq 1 30); do
  if curl -sf http://localhost:11434/api/tags >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "==> Optional healthy-path sample (smaller)"
curl -sf -X POST "$BASE_URL/v1/reliability/sli/reset" > /dev/null
PLAYER_REQUESTS=50 CHAT_REQUESTS=5
# inline small healthy sample without clobbering env for summary
for i in $(seq 1 50); do
  # healthy sample: no fault-injection header
  curl -s --max-time 15 -o /dev/null "$BASE_URL/v1/players/$PLAYER_ID" || true
done
for i in $(seq 1 5); do
  curl -s --max-time 30 -o /dev/null "$BASE_URL/v1/chat/list-models" || true
done

echo "==> Readiness while Ollama UP"
curl -s "$BASE_URL/actuator/health/readiness" | tee "$OUT_DIR/${PHASE}-readiness-ollama-up.json"
echo
echo "==> SLI while Ollama UP (small sample)"
curl -sf "$BASE_URL/v1/reliability/sli" | tee "$OUT_DIR/${PHASE}-sli-ollama-up.json"
echo
echo "==> Wrote results under $OUT_DIR/${PHASE}-*.json"
echo "==> Primary story numbers are in ${PHASE}-sli-ollama-down.json"
if [[ -f "$OUT_DIR/baseline-sli-ollama-down.json" && -f "$OUT_DIR/after-sli-ollama-down.json" ]]; then
  python3 - <<PY
import json, pathlib
root = pathlib.Path("$OUT_DIR")
b = json.loads((root/"baseline-sli-ollama-down.json").read_text())
a = json.loads((root/"after-sli-ollama-down.json").read_text())
br = json.loads((root/"baseline-readiness-ollama-down.json").read_text())
ar = json.loads((root/"after-readiness-ollama-down.json").read_text())
summary = {
  "headline": {
    "perceivedAvailabilityPct": {"baseline": b.get("perceivedAvailabilityPct"), "after": a.get("perceivedAvailabilityPct")},
    "coreAvailabilityPct": {"baseline": b.get("coreAvailabilityPct"), "after": a.get("coreAvailabilityPct")},
    "serviceMeetsSlo": {"baseline": b.get("serviceMeetsSlo"), "after": a.get("serviceMeetsSlo")},
    "readinessHttp": {"baseline": br.get("_httpStatus"), "after": ar.get("_httpStatus")},
    "sloTargetPct": "99.90%",
  },
  "baseline_sli": b,
  "after_sli": a,
}
(root/"comparison-summary.json").write_text(json.dumps(summary, indent=2))
print("==> Updated comparison-summary.json")
print(json.dumps(summary["headline"], indent=2))
PY
fi
