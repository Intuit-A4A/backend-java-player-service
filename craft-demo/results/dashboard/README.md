# Dashboard + ramp load

## Hang simulation (chat never returns 200)

1. `docker stop ollama` so nothing real listens on 11434.
2. `scripts/ramp_load_test.py` starts **`hang_server`**: bind `127.0.0.1:11434`, **accept TCP**, read once, then **sleep forever** (no HTTP response).
3. The app still calls `http://127.0.0.1:11434` via ollama4j. The socket is open, so this is **not** a fast connect failure. Baseline uses a **120s** request timeout. The **timeouts** profile uses **2s**.

Chat **HTTP 200** only when Ollama returns JSON. During the hang, chat either:

- **Never finishes** before the load-generator client timeout → recorded as **`client_timeout`** in ramp JSON (not an HTTP status).
- **`http_503`** when the async chat pool is full, or Ollama connect/read timeout maps to 503 in `ChatController`.

Player **HTTP 200** is independent when chat is async (timeouts profile): Tomcat serves H2 while chat workers are stuck on the hang peer.

## Grafana

```bash
sh craft-demo/observability/up.sh
```

Open http://localhost:3000/d/availability/availability

- **Counts**, not req/s: `increase(http_server_requests_seconds_count{...}[$__rate_interval])` stacked by **200 / 503 / 500**.
- **No latency panels** (503 pool-reject is ms; hung chat does not appear until it completes).
- **Tomcat busy threads** only (workers actively handling a request). **Current** includes idle parked threads; for saturation use **busy → 40** (`server.tomcat.mbeanregistry.enabled: true`). When busy is at the max, baseline player calls become **`client_timeout`** in the ramp log.

**Why Grafana missed busy ≈ 39:** the JVM did not exit. With chat on the Tomcat thread, all **40** workers were stuck on hung calls. Prometheus scraped **`/actuator/prometheus` on port 8080**, the same connector as the API, so the scrape **could not get a worker** and the series went blank (see `tomcatThreadsBusy: null` from step 4 onward in `ramp-baseline.json`). Metrics are now on **`management.server.port: 8081`**; Prometheus uses **8081** so Tomcat busy stays visible under saturation.

Hung chat on **baseline** (chat on Tomcat): chat calls **do not complete** within the 12s client timeout → **no chat bar on Grafana** for that period; use **Tomcat busy** + ramp **`client_timeout`** for chat.

## Ramp load (0 → saturation)

Every 5s, add 6 chat calls (`list-models` + `POST /v1/chat`) and 2 player calls (list + by-id).

```bash
export JAVA_HOME="/opt/homebrew/opt/openjdk@17"
export PATH="$JAVA_HOME/bin:$PATH"
mvn -DskipTests package
python3 scripts/ramp_load_test.py baseline
python3 scripts/ramp_load_test.py timeouts
```

Results: `ramp-baseline.json`, `ramp-timeouts.json`, `ramp-comparison.md`.

| Outcome (ramp JSON) | Meaning |
|---------------------|---------|
| `http_200` | App returned 200 |
| `http_503` | App returned 503 (chat pool full, Ollama connect/read timeout, …) |
| `client_timeout` | Load script gave up waiting (no status line from app) |
| `http` field | Raw status when present; prefer **`outcome`** in JSON |
