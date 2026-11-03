# Player service demo

**One-line pitch:** A Spring Boot service with a core player API and a secondary chat API over Ollama. On `main` you cannot see whether the player API is healthy, you misread database outages as 404, and hung chat can starve Tomcat so player calls never start. The branch adds observability first, then a minimal chat change so player traffic stays up under the same load.

---

## 1. Architecture

One JVM. Player and chat share Tomcat on **8080**. H2 is in memory. Ollama is out of process.

```text
PlayerController  -> PlayerService -> PlayerRepository -> H2
ChatController    -> ChatClientService -> OllamaAPI -> Ollama
```

| API | Role |
|-----|------|
| `GET /v1/players`, `GET /v1/players/{id}` | Core. By-id sleeps 0–2s on purpose |
| `GET /v1/chat/list-models`, `POST /v1/chat` | Secondary. LLM via Ollama |

**Success criterion for this talk:** player endpoints return **200 within the client deadline** while chat is stuck on a model that accepts TCP and never responds. Chat 503 is acceptable; player **client timeout** is not.

---

## 2. Problems

### 2.1 No observability for the system

On **`main`**, the service has **no operational picture**:

- No Prometheus scrape, no Grafana, no dashboard checked into the repo
- No Actuator metrics or `/actuator/prometheus` wired into a stack
- No in-app SLI or `/v1/reliability/*` endpoints
- No documented split between liveness and readiness (what “healthy” means for player vs chat)
- Under load or outage, you rely on **logs and ad-hoc curls**, not time series or a single availability number

That gap is **always** true, even when Tomcat is idle. You cannot answer: *How many player calls completed? What status codes? Is the pool filling? Is the player API meeting SLO?*

**Pool saturation makes it worse:** if metrics were scraped on **8080**, the scrape needs a worker like any other request. When all workers are busy, series go blank exactly when you need them. The demo pins max threads to **40** so that failure mode shows on a laptop.

### 2.2 A database failure is returned as 404

`PlayerService.getPlayerById` on `main` catches every exception and returns empty. The controller maps empty to **404**. A real id with a missing `PLAYERS` table looks like “player not found,” not “data store failed.”

### 2.3 A stuck chat call holds a Tomcat worker

On `main`, chat runs on the **request thread** with one **120s** ollama4j timeout. Refused TCP fails fast; a hang peer that already accepted holds the worker until timeout. Enough concurrent chat calls and **player work never gets a thread**. H2 and the JVM can still be fine.

---

## 3. Approach, challenges, solutions

### Approach

**First:** make the system observable on a path the API pool cannot block. **Second:** compare **baseline** vs **`timeouts`** profile—async chat plus a **2s** Ollama timeout—under the same ramp and hang peer.

```text
Clients ---------> :8080 (Tomcat, max 40) -----> PlayerController / ChatController
                         |
                         | HTTP response completed
                         v
              Micrometer: http_server_requests_seconds_count{uri,status}
              Tomcat MBean (mbeanregistry on): tomcat_threads_busy_threads
              SliRecordingFilter -> SliTracker (player-only availability ratio)

:8081 (management) <----- Prometheus (1s scrape) <----- Grafana "Availability"
         health / info / prometheus
```

| Layer | What you watch |
|-------|----------------|
| **Saturation** | `tomcat_threads_busy_threads` → configured max (40) |
| **Completed work** | Per-API `increase(...)` stacked **200 / 503 / 500** (finished requests only) |
| **SLI** | Player successes ÷ player requests that reached the app (HTTP below 500); chat excluded |
| **Ramp JSON** | `client_timeout` when the load generator gives up—**not** in Grafana |

Two profiles, same hang simulation:

| Profile | Chat | Ollama timeout | Player under hang |
|---------|------|----------------|-------------------|
| **Baseline** | Tomcat thread | 120s | **client_timeout** after pool fills |
| **Timeouts** | 8× `chat-exec`, queue 0 | 2s | **200**; chat **503** |

### Challenges

- **Blind by default:** no stack on `main`; no single place to see player vs chat behavior.
- **Wrong port for scrape:** 8080 metrics disappear when the pool is saturated.
- **Missing Tomcat gauge:** without `server.tomcat.mbeanregistry.enabled`, busy-thread metrics are not exported.
- **Metrics vs user experience:** Grafana counts **completed** responses; hung calls and client timeouts need the ramp log.
- **Probe design:** Ollama on readiness would drain player traffic during a model outage; liveness on “stuck thread” would restart a JVM that can still serve players.
- **One timeout knob:** ollama4j uses one request timeout; the hang peer is a long **read** wait, not a connect failure.

### Solutions

| Area | What we did |
|------|-------------|
| **Metrics & probes** | `management.server.port: 8081`; expose health, info, prometheus; liveness = process, readiness = **db** only |
| **Tomcat visibility** | `server.tomcat.mbeanregistry.enabled: true`; Tomcat max **40** for demo saturation |
| **SLI & stage** | Filter + tracker + `/v1/reliability/mode` and `/sli`; `/actuator/info` documents the split |
| **Dashboard** | Prometheus + Grafana; busy threads + status counts (no latency panels) |
| **Correct errors** | DB exceptions → **500** via `PlayerExceptionHandler`; missing id stays **404** |
| **Availability fix** | `async-enabled` + bounded pool; `read-timeout-ms: 2000` on **`timeouts`** profile |

### Key files (what changed)

**Monitoring & reliability**

| File | Role |
|------|------|
| `src/main/resources/application.yml` | 8080/8081 split, Tomcat 40, MBean registry, health groups, histogram |
| `src/main/java/.../reliability/SliRecordingFilter.java` | Records finished `/v1/players` and `/v1/chat` |
| `src/main/java/.../reliability/SliTracker.java` | Player availability ratio; chat tracked but excluded |
| `src/main/java/.../reliability/ReliabilityController.java` | `/v1/reliability/mode`, `/sli`, `/sli/reset` |
| `src/main/java/.../reliability/ServiceInfoContributor.java` | `/actuator/info` service block |
| `craft-demo/observability/prometheus.yml` | Scrape `host.docker.internal:8081` |
| `craft-demo/observability/up.sh` | Start Prometheus + Grafana |
| `craft-demo/observability/grafana/dashboards/availability.json` | Busy threads + per-API status counts |
| `scripts/ramp_load_test.py` | Hang peer + ramp; writes `ramp-baseline.json`, `ramp-timeouts.json` |

**Player correctness**

| File | Role |
|------|------|
| `src/main/java/.../service/PlayerService.java` | Propagate DB errors; keep 0–2s latency simulation |
| `src/main/java/.../controller/PlayerExceptionHandler.java` | Map `DataAccessException` → **500** |

**Chat / availability (baseline vs timeouts)**

| File | Role |
|------|------|
| `src/main/java/.../chat/ChatResilienceProperties.java` | `app.chat.*`: stage, async, pool size, read timeout |
| `src/main/java/.../config/ReliabilityConfiguration.java` | Binds `ChatResilienceProperties` |
| `src/main/java/.../chat/ChatAsyncConfig.java` | `chat-exec` pool; MVC async support |
| `src/main/java/.../controller/chat/ChatController.java` | `Callable` when async; 503 on timeout / pool full |
| `src/main/java/.../config/ChatClientConfiguration.java` | `OllamaAPI.setRequestTimeoutSeconds` from properties |
| `src/main/resources/application-timeouts.yml` | Profile: async + **2s** timeout |

### Test

Same ramp for both profiles (hang on **11434**, traffic stepped every 5s). Checked-in result:

| Signal | Baseline | Timeouts |
|--------|----------|----------|
| Peak Tomcat busy | **40** | **~2** |
| Player calls | early **200**, then **client_timeout** | **28/28** **200** |
| Chat calls | **client_timeout** | **503** |

![Grafana ramp](results/dashboard/grafana-ramp-annotated.png)

---

## 4. Impact

- **Observability:** You can see saturation and completed status codes while the failure is happening, and separate “client gave up” from “app returned 503.”
- **Player API:** Under the same hung model, player calls stay **200** instead of timing out at the client—on **one JVM**, with monitoring that still scrapes.
- **Operability:** DB outage is **500**, not a fake 404. Readiness stays **UP** when only Ollama is down, so this instance can keep taking player traffic.

Fleet effects (replicas, second JVM) are in **section 6**.

---

## 5. Learnings

- Define availability for the **player API**, not “any route” and not “process up.”
- **Observability is a product feature:** metrics port, MBean registry, SLI, and dashboards are part of the fix—not only something you add after an incident.
- **Busy threads** = capacity; **status counts** = completed outcomes; **ramp outcomes** = what the user felt when nothing finished.
- **More Tomcat threads** do not fix a 120s chat call on the request thread; **decouple + shorter timeout** does.
- **Probes and replicas** are the next step: readiness routes traffic; a second JVM shows why that matters. Splitting player and chat deployments is the same isolation at larger scale.

---

## 6. Beyond this process

Section 3 is **one JVM**. Probes describe this process; they do not by themselves raise availability.

**Liveness** — restart only when the process is dead, not when a chat thread is stuck.

**Readiness** — send player traffic when **H2** is good; omit Ollama so a model outage does not drain this instance. Readiness helps only with **another replica** to take work; on a single instance, failing readiness removes the only copy.

| Change | What it improves |
|--------|------------------|
| Readiness is H2, not Ollama | A dead model does not remove player traffic from this instance |
| Second JVM | One process can fail while the other still serves players |
| Graceful shutdown | In-flight player calls can finish instead of being cut off on deploy or SIGTERM |
| Player and chat as two deployments | Chat load cannot saturate the player process |
| Durable database | Restart does not imply losing the only copy of player data |
