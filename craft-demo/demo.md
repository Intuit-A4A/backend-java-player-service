# Player service demo

Design write-up. The live set is [`presenter-45min.md`](presenter-45min.md), [`Player-Service-Availability.pptx`](Player-Service-Availability.pptx), and [`commands.md`](commands.md).

**One-line pitch:** A Spring Boot service with a core player API and a secondary chat API over Ollama. On `main` you cannot see whether the player API is healthy, you misread database outages as 404, `GET /v1/players` loads the whole roster into one response, and hung chat can starve Tomcat so player calls never start. The branch adds observability first, correct errors and bounded list reads, then a minimal chat change so player traffic stays up under the same load.

---

## 1. Architecture

**Java player service (this repo):** one JVM. Player and chat share Tomcat on **8080**. H2 is in memory. **Ollama** is out of process on **11434**.

**Related (not wired to 8080 today):** [`player-service-model/`](../player-service-model/) — a small **Flask** container (`a4a_model`) that serves a **k-NN team recommender** (`team_model.joblib`, `features_db.csv`). Run with Docker (on macOS map host **5001→5000** if **5000** is AirPlay). Endpoints: `POST /team/generate` (seed player or features + `team_size`), `POST /team/feedback`. It shares the same *baseball player* theme as the CSV/H2 data but is a **separate process**; integration with `8080` would be a new REST client + `v1/team/*` routes (optional stretch, not part of the availability ramp).

```text
:8080  PlayerController  -> PlayerService -> PlayerRepository -> H2
       ChatController    -> ChatClientService -> OllamaAPI -> Ollama :11434

:8081  management — health, prometheus (does not compete with API pool)

:5001  player-service-model (optional) — POST /team/generate, /team/feedback
```

| API on **8080** | Role |
|-----------------|------|
| `GET /v1/players`, `GET /v1/players/{id}` | Core player API. List returns the roster (unbounded on **`main`** — see §2.3); by-id sleeps **0–2s** on purpose. **This branch** adds offset paging in §3.3 — not the starting shape in §1. |
| `GET /v1/chat/list-models`, `POST /v1/chat` | Secondary. LLM via Ollama |

**Success criterion for this talk:** player endpoints return **200 within the client deadline** while chat is stuck on a model that accepts TCP and never responds. Chat 503 is acceptable; player **client timeout** is not.

**45 min presenter:** [`presenter-45min.md`](presenter-45min.md) · **Slides:** [`Player-Service-Availability.pptx`](Player-Service-Availability.pptx). **Commands:** [`commands.md`](commands.md). **Before/after evidence:** [`results/demo-capture/demo-evidence.md`](results/demo-capture/demo-evidence.md). **Scorecard + Grafana PNGs:** [`presenter-scorecard.md`](results/dashboard/presenter-scorecard.md), [`screenshots/`](results/dashboard/screenshots/).

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

### 2.3 `GET /v1/players` does not scale — availability risk as data grows

On **`main`**, `PlayerService` calls **`findAll()`** and returns every row in one JSON payload (~19k players from `Player.csv` on a laptop). That works for the assignment dataset but **does not stay safe as the table grows toward millions**:

- **Tomcat worker time** — one list call holds a thread for the full DB read, entity mapping, and JSON serialization. Response bytes and GC pressure grow with row count; slow lists compete with `GET /v1/players/{id}` on the same **40**-thread pool.
- **SLI and client deadlines** — `SliRecordingFilter` treats any `/v1/players` completion below **500** as success. A list that finishes in **90s** with **200** still counts as “available” even when clients already timed out.
- **Failure blast radius** — under chat saturation (§2.4), a few concurrent “download the whole roster” calls make pool exhaustion more likely; player **by-id** traffic is what the demo must protect.

Pagination is required so list traffic is **bounded per request**, not so every caller pulls the full table.

### 2.4 A stuck chat call holds a Tomcat worker

On `main`, chat runs on the **same Tomcat thread** as player traffic. `ChatController` invokes ollama4j on that thread; **`mvc.async` is off**, so the worker is not released until the generate call completes or throws.

**Hang vs refuse.** Refused TCP (`connection refused` on **11434**) fails in milliseconds. The craft-demo **hang peer** accepts TCP and then never sends a response body. ollama4j keeps reading until **`read-timeout-ms` (120s on baseline)**. That is a **120s worker lease** per stuck chat call, not a database problem—H2 and `GET /v1/players/{id}` can still be fast if a thread is free.

**Pool math (demo pin: 40 threads).** With baseline sync chat, **40 concurrent hung chats saturate the pool**. Request 41 for a player never **starts** servlet handling in time; the client sees **timeout**, while Grafana may still show nothing finished yet. Chat **503** after **2s** on the **`timeouts`** profile is acceptable for this talk; player **client_timeout** is not.

**Coupling with §2.3.** Unbounded or slow list calls are not the same failure mode as a hung LLM read, but both **extend thread hold time**. A full-roster download plus several 120s chats makes it easier to reproduce starvation on a laptop without misattributing the root cause in metrics (busy threads = **40**, player SLI still only counts **completed** responses).

**What “healthy” must not mean.** Process up, H2 up, and an empty Prometheus scrape on **8080** during saturation do **not** imply player work is completing. Observability (§3.1) must show **busy threads** and **finished status codes** while chat is decoupled (§3.4).

---

## 3. Approach, challenges, solutions

Each subsection answers one problem from **§2**.

### 3.1 Observability (problem 2.1)

**Approach:** Make the system observable on a path the API pool cannot block, then compare **baseline** vs **`timeouts`** under the same ramp and hang peer.

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

**Challenges**

- **Blind by default:** no stack on `main`; no single place to see player vs chat behavior.
- **Wrong port for scrape:** 8080 metrics disappear when the pool is saturated.
- **Missing Tomcat gauge:** without `server.tomcat.mbeanregistry.enabled`, busy-thread metrics are not exported.
- **Metrics vs user experience:** Grafana counts **completed** responses; hung calls and client timeouts need the ramp log.
- **Probe design:** Ollama on readiness would drain player traffic during a model outage; liveness on “stuck thread” would restart a JVM that can still serve players.

**What we did**

| Area | Change |
|------|--------|
| **Metrics & probes** | `management.server.port: 8081`; expose health, info, prometheus; liveness = process, readiness = **db** only |
| **Tomcat visibility** | `server.tomcat.mbeanregistry.enabled: true`; Tomcat max **40** for demo saturation |
| **SLI & stage** | Filter + tracker + `/v1/reliability/mode` and `/sli`; `/actuator/info` documents the split |
| **Dashboard** | Prometheus + Grafana; busy threads + status counts (no latency panels) |

**Demo / test (best signal)**

| What to run | What proves it |
|-------------|----------------|
| `sh craft-demo/observability/up.sh` + app on this branch | Stack is up; Grafana **Availability** dashboard |
| `curl` **8081** `/actuator/prometheus` → `tomcat_threads_busy`, `tomcat_threads_config_max` | Busy-thread gauge exists (needs MBean registry) |
| `curl` **8081** `/actuator/health/liveness` vs `readiness` | Liveness = process; readiness includes **db**, not Ollama |
| `curl` **8080** `/v1/reliability/mode`, `/v1/reliability/sli` | In-app stage + player SLI |
| **`python3 scripts/ramp_load_test.py baseline`** then **`timeouts`** | **Capstone:** baseline → busy **40**, player **`client_timeout`** in JSON; timeouts → player **28/28 `http_200`**, chat **503**, busy **~2** (see [`ramp-comparison.md`](results/dashboard/ramp-comparison.md)) |
| Grafana during ramp | Busy panel hits max on baseline; per-API **completed** 200/503 stacks; **client timeouts** only in ramp JSON, not as HTTP |

**Best live story:** run **timeouts** profile under hang peer while showing **8081** still scrapes and player curls return **200** — observability stays honest while the fix works.

### 3.2 Correct errors on player reads (problem 2.2)

**Challenge:** Treating every data-layer failure as “not found” hides outages from clients and from the SLI.

**What we did**

- `PlayerService.getPlayerById` lets **`DataAccessException`** propagate (no catch-and-empty).
- `PlayerExceptionHandler` maps those to **500** `"player data unavailable"`; a genuinely missing id stays **404**.

**Demo / test (best signal)**

| What to run | Expected on **this branch** | Contrast on **`main`** (optional) |
|-------------|----------------------------|-------------------------------------|
| `curl -si localhost:8080/v1/players/no-such-player` | **HTTP/1.1 404** | Same |
| H2 console: `DROP TABLE PLAYERS`, then `curl -si .../v1/players/aardsda01` | **500** + `"player data unavailable"` | **404** (outage looks like “not found”) |
| `curl` `/v1/reliability/sli` after a few player calls | SLI reflects **500** as failure | On main, fake **404** can inflate “success” |

**Best live story:** drop table → **500** with JSON error — operable outage, not a silent wrong semantics. Restart JVM to reload CSV.

### 3.3 Pagination for list availability (problem 2.3)

**Challenge:** Unbounded `findAll()` ties list latency, heap use, and JSON size to table cardinality. At millions of rows that is an **availability** problem: one **200** can hold a Tomcat thread long enough that other player clients miss their deadline, even though the SLI still counts the slow call as success.

**Offset vs cursor (keyset)**

| | **Offset** (`page` + `size`) | **Cursor** (keyset, e.g. `after=playerId`) |
|---|------------------------------|--------------------------------------------|
| API shape | Familiar; maps to Spring `Pageable` and `LIMIT`/`OFFSET` | Stable when rows are inserted/deleted between pages |
| Deep pages | Large `OFFSET` gets expensive in SQL | Scales for deep walks when the sort key is indexed |
| Availability story | **Caps bytes and thread time per call** with a max `size` | Same cap; avoids duplicate/skip under concurrent writes |
| Fit for this demo | **Implemented** — fixes “whole table in one response” now | Defer until export or live-catalog churn needs it |

**Choice:** **Offset pagination** first. The win for player availability is bounding **each** list response, not optimizing page 20,000. Cursor/keyset stays a later option when deep sequential scans or high churn matter more than time-to-ship.

**What we did**

| Piece | Behavior |
|-------|----------|
| **API** | `GET /v1/players?page=&size=&sort=` — Spring `Pageable`; default **size=50**, sort **`playerId`**. |
| **Cap** | `size` > **100** → **400** `{"error":"size must not exceed 100"}`. |
| **Persistence** | `playerRepository.findAll(pageable)` — no unbounded list in `PlayerService`. |
| **JSON** | Existing `players` array plus **`page`**, **`size`**, **`totalElements`**, **`totalPages`** on `Players`. |

**Try it**

```shell
curl -s 'http://localhost:8080/v1/players?page=0&size=10'
curl -s 'http://localhost:8080/v1/players?page=1&size=10&sort=playerId,asc'
```

Clients walk pages until `page + 1 >= totalPages`. The ~19k-row demo CSV becomes many small responses instead of one multi‑MB payload.

**Demo / test (best signal)**

| What to run | Expected |
|-------------|----------|
| `curl -s 'http://localhost:8080/v1/players?page=0&size=10'` | **200**; `players` length **10**; `totalElements` ≈ **19370**; `totalPages` present |
| `curl -s 'http://localhost:8080/v1/players?size=101'` | **400** `size must not exceed 100` |
| `curl -s -o /dev/null -w 'bytes=%{size_download} time=%{time_total}s\n' '.../v1/players?page=0&size=50'` | Bounded payload and predictable time vs one huge list on **`main`** |
| Under load (ramp uses list + by-id) | Paged list reduces bytes/thread per call so pool contention with chat is harder to trigger from list alone |

**Best live story:** show one small JSON page + metadata next to the §2.3 narrative (“millions of rows” → cap **size**, not one response). Optional: `wc -c` on **`main`** full list vs branch `size=50` page.

### 3.4 Chat decoupling under pool pressure (problem 2.4)

**Challenge:** Baseline chat blocks the Tomcat worker for the full ollama4j read (up to **120s**). The hang peer is a **read stall**, not a connect failure, so failure looks like “slow” or “client gave up,” not an immediate **503**.

**What we did**

| Area | Change |
|------|--------|
| **Availability fix** | `async-enabled` + bounded **`chat-exec`** pool (queue **0**); `read-timeout-ms: 2000` on **`timeouts`** profile |
| **Controller** | Return **`Callable`** when async so Tomcat releases the request thread; **503** on timeout, connect failure, or **pool full** |
| **Config** | `OllamaAPI.setRequestTimeoutSeconds` aligned with `app.chat.read-timeout-ms`; stage in `/v1/reliability/mode` and `/actuator/info` |

Under **`timeouts`**, chat fails fast (**503**) while the ramp shows player **200** with peak busy threads near idle—see **§3.1 ramp** and **Demo summary** below. That is the paired fix with §3.3: shorter per-request work on **both** list and chat paths where we control them.

**Demo / test (best signal)**

| What to run | Expected |
|-------------|----------|
| `docker stop ollama`; `curl -m 5 -w '%{http_code}\n' localhost:8080/v1/chat/list-models` | Fast failure (**503** / unavailable JSON), not a **120s** hang |
| App **default** profile + hang peer + concurrent `POST /v1/chat` + `GET /v1/players/{id}` | Pool fills; player **`client_timeout`** (manual or ramp) |
| `java -jar ... --spring.profiles.active=timeouts` + same hang | Chat **503** within **~2s**; player **200** |
| `/v1/reliability/mode` | Shows `asyncEnabled`, `readTimeoutMs`, `stage` |

**Best live story:** same hang, two profiles — **baseline** vs **timeouts** table in §3.1; that is the audience takeaway for §2.4.

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

**Player correctness & list bounds (§3.2, §3.3)**

| File | Role |
|------|------|
| `src/main/java/.../model/Players.java` | List payload + offset metadata (`page`, `size`, `totals`) |
| `src/main/java/.../service/PlayerService.java` | `getPlayers(Pageable)`; propagate DB errors; 0–2s latency on by-id only |
| `src/main/java/.../controller/PlayerController.java` | `PageableDefault(50)`; **400** when `size` > 100 |
| `src/main/java/.../repository/PlayerRepository.java` | `JpaRepository` `findAll(Pageable)` |
| `src/main/java/.../controller/PlayerExceptionHandler.java` | Map `DataAccessException` → **500** |

**Chat / availability (§3.4 — baseline vs timeouts)**

| File | Role |
|------|------|
| `src/main/java/.../chat/ChatResilienceProperties.java` | `app.chat.*`: stage, async, pool size, read timeout |
| `src/main/java/.../config/ReliabilityConfiguration.java` | Binds `ChatResilienceProperties` |
| `src/main/java/.../chat/ChatAsyncConfig.java` | `chat-exec` pool; MVC async support |
| `src/main/java/.../controller/chat/ChatController.java` | `Callable` when async; 503 on timeout / pool full |
| `src/main/java/.../config/ChatClientConfiguration.java` | `OllamaAPI.setRequestTimeoutSeconds` from properties |
| `src/main/resources/application-timeouts.yml` | Profile: async + **2s** timeout |

### Demo summary — what to run, in order

Use this as the presenter spine. Details and copy-paste curls: [`demo-note.md`](demo-note.md).

| Order | Maps to | Audience sees |
|-------|---------|----------------|
| 1 | §2.2 / §3.2 | Missing id **404**; dropped `PLAYERS` → **500** (not fake **404**) |
| 2 | §2.3 / §3.3 | `GET /v1/players?page=0&size=10` — small body + `totalElements` (after-change); contrast **`main`** unbounded list if you have time |
| 3 | §2.1 / §3.1 | **8081** health + Prometheus; Grafana busy + status panels; `/v1/reliability/sli` |
| 4 | §2.4 / §3.4 | **Ramp** baseline → pool saturation + `client_timeout`; **timeouts** profile → player **200**, chat **503** |
| — | `player-service-model` (optional) | `curl` **5001** `/team/generate` — separate ML toy; not on 8080 |

**Ramp (primary quantitative proof for §2.1 + §2.4):** `python3 scripts/ramp_load_test.py baseline` then `timeouts` with hang peer on **11434**. Checked-in result:

| Signal | Baseline | Timeouts |
|--------|----------|----------|
| Peak Tomcat busy | **40** | **~2** |
| Player calls | early **200**, then **client_timeout** | **28/28** **200** |
| Chat calls | **client_timeout** | **503** |

**On screen:** [`presenter-scorecard.md`](results/dashboard/presenter-scorecard.md) (one table: baseline vs `timeouts`) + optional Grafana Tomcat panel only. Annotated screenshot: [`grafana-ramp-annotated.png`](results/dashboard/grafana-ramp-annotated.png) (backup if live stack fails).

Re-run evidence: `sh scripts/demo_capture.sh` (curls; **drops H2 table** — restart app) and `python3 scripts/ramp_load_test.py` ×2 + `python3 scripts/render_ramp_scorecard.py`.

**What not to lean on in the talk:** reading four stacked HTTP status charts without the scorecard; raw p99 latency; LLM stubs in `player-service-model` `/llm/*`.

---

## 4. Impact

- **Observability:** You can see saturation and completed status codes while the failure is happening, and separate “client gave up” from “app returned 503.”
- **Player API:** Under the same hung model, player calls stay **200** instead of timing out at the client—on **one JVM**, with monitoring that still scrapes.
- **Operability:** DB outage is **500**, not a fake 404. Readiness stays **UP** when only Ollama is down, so this instance can keep taking player traffic.
- **List traffic:** Offset pagination keeps each list call bounded so roster growth does not turn `GET /v1/players` into a multi‑minute Tomcat hog; by-id and paged list can coexist in the same pool.

Fleet effects (replicas, second JVM) are in **section 6**.

---

## 5. Learnings

- Define availability for the **player API**, not “any route” and not “process up.”
- **Observability is a product feature:** metrics port, MBean registry, SLI, and dashboards are part of the fix—not only something you add after an incident.
- **Busy threads** = capacity; **status counts** = completed outcomes; **ramp outcomes** = what the user felt when nothing finished.
- **More Tomcat threads** do not fix a 120s chat call on the request thread; **decouple + shorter timeout** does.
- **Unbounded `findAll()`** is a player-availability bug at scale; **offset pages + max `size`** fix the common case before you need cursor/keyset paging.
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
