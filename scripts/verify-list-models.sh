#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
APP_URL="${APP_URL:-http://localhost:8080}"

echo "== Ollama /api/tags =="
TAGS_CODE="$(curl -s -o /tmp/ollama-tags.json -w '%{http_code}' "${OLLAMA_URL}/api/tags")"
echo "HTTP ${TAGS_CODE}"
if [[ "${TAGS_CODE}" != "200" ]]; then
  echo "Ollama is not reachable at ${OLLAMA_URL}" >&2
  exit 1
fi
if grep -q '"capabilities"' /tmp/ollama-tags.json; then
  echo "Ollama response includes capabilities (exercises the fixed deserialization path)."
else
  echo "Note: capabilities not present in tags JSON; test still valid but less representative."
fi

echo
echo "== Maven regression test =="
if [[ -x ./mvnw ]]; then
  ./mvnw -B -Dtest=OllamaListModelsDeserializationTest test
else
  mvn -B -Dtest=OllamaListModelsDeserializationTest test
fi

echo
echo "== Player service /v1/chat/list-models =="
LIST_CODE="$(curl -s -o /tmp/list-models.json -w '%{http_code}' "${APP_URL}/v1/chat/list-models")"
echo "HTTP ${LIST_CODE}"
if [[ "${LIST_CODE}" != "200" ]]; then
  echo "Response body:" >&2
  cat /tmp/list-models.json >&2 || true
  exit 1
fi
head -c 400 /tmp/list-models.json
echo
echo "OK"
