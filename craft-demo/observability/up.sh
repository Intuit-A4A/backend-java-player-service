#!/bin/sh
set -eu
cd "$(dirname "$0")"
docker network create player-obs >/dev/null 2>&1 || true
docker rm -f player-prometheus player-grafana >/dev/null 2>&1 || true
docker run -d --name player-prometheus --network player-obs \
  -p 9090:9090 \
  --add-host host.docker.internal:host-gateway \
  -v "$PWD/prometheus.yml:/etc/prometheus/prometheus.yml:ro" \
  prom/prometheus:v2.55.1 \
  --config.file=/etc/prometheus/prometheus.yml
docker run -d --name player-grafana --network player-obs \
  -p 3000:3000 \
  -e GF_AUTH_ANONYMOUS_ENABLED=true \
  -e GF_AUTH_ANONYMOUS_ORG_ROLE=Admin \
  -e GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH=/var/lib/grafana/dashboards/availability.json \
  -v "$PWD/grafana/provisioning:/etc/grafana/provisioning:ro" \
  -v "$PWD/grafana/dashboards:/var/lib/grafana/dashboards:ro" \
  grafana/grafana:11.4.0
echo "Grafana: http://localhost:3000/d/availability/availability"
