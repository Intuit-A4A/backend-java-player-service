# Craft Demo — Keeping Player Requests Available When LLM Calls Stall

Branch: `craft-demo/availability`

The service has two APIs on one process:

- `GET /v1/players` and `GET /v1/players/{id}` — player data in H2. Lookup sleeps 0–2s on purpose.
- `GET /v1/chat/list-models` and `POST /v1/chat` — calls to Ollama.

Availability in this demo is the player API only: a player lookup returns **HTTP 200 within 5 seconds**. Chat has its own status codes. Those codes stay out of the availability number.

Tomcat's normal max is 200 workers. This demo pins `server.tomcat.threads.max` to **40** so a laptop can fill the pool. Each in-flight LLM call on a Tomcat thread still consumes one worker.

Every block below is a full paste. Run them from the repo root.

---

## 1. Database errors return 500

`PlayerService.getPlayerById` used to catch every exception and return "not found". The controller then answered **404**. A missing id is still **404**. A database failure now reaches `PlayerExceptionHandler` and returns **500**:

```json
{"error":"player data unavailable","detail":"DataAccessResourceFailureException"}
```

The 0–2s sleep is unchanged.

```bash
export JAVA_HOME="/opt/homebrew/opt/openjdk@17"
export PATH="$JAVA_HOME/bin:$PATH"
cd ~/git/player-service-java
mvn -Dtest=PlayerErrorStatusTest test
```

---

## 2. What we expose, and which codes chat returns

Availability is computed from player requests that reached the process:

`player successes / player requests`, success = player HTTP status below 500.

A missing player is 404, so it stays a success. A database failure is 500, so it counts against availability. The load test in later sections is stricter: it requires HTTP 200 within 5s, and it also counts player calls that never got a thread. Chat is recorded on `/v1/reliability/sli` with `includedInAvailability: false`.

Chat status codes after the later stages:

| Situation | HTTP | Body |
|-----------|------|------|
| Ollama answered | 200 | model JSON, or the generated text |
| Connect timeout, read timeout, or Ollama HTTP 5xx | 503 | `{"error":"Ollama call failed","detail":"..."}` |
| Chat pool is full (8 workers, no queue) | 503 | `{"error":"Chat worker pool is full","detail":"rejected"}` |
| Circuit breaker is open | 503 | `{"error":"Ollama circuit is open","detail":"no call was sent to Ollama"}` |

Infra probes, for the platform side of the same story:

- `GET /actuator/health/liveness` — process is up. A database or model outage does not fail this, so the platform does not restart the process for those.
- `GET /actuator/health/readiness` — H2 accepts connections. Ollama is left out, so a dead model does not remove the player API from the load balancer. Chat reports that itself, with 503.
- `GET /actuator/info` — Java, OS, the running stage, and the sentence above about what each probe means.
- `GET /actuator/metrics` — Micrometer HTTP timers.
- `GET /actuator/prometheus` — the same timers in Prometheus text format.

Terminal 1, leave it running:

```bash
export JAVA_HOME="/opt/homebrew/opt/openjdk@17"
export PATH="$JAVA_HOME/bin:$PATH"
cd ~/git/player-service-java
mvn -DskipTests package
java -jar target/player-service-java-0.0.1-SNAPSHOT.jar
```

Terminal 2:

```bash
curl -s localhost:8080/actuator/health/liveness | python3 -m json.tool
curl -s localhost:8080/actuator/health/readiness | python3 -m json.tool
curl -s localhost:8080/actuator/info | python3 -m json.tool
curl -s localhost:8080/actuator/prometheus | head
curl -s localhost:8080/v1/reliability/mode | python3 -m json.tool
curl -s -X POST localhost:8080/v1/reliability/sli/reset | python3 -m json.tool
curl -s -o /dev/null -w "player %{http_code}\n" localhost:8080/v1/players/aardsda01
curl -s -o /dev/null -w "missing %{http_code}\n" localhost:8080/v1/players/no-such-player
curl -s localhost:8080/v1/reliability/sli | python3 -m json.tool
```

Stop the process in terminal 1 before the load tests (`Ctrl-C`). Each load test also frees port 8080 itself.

---

## 3. Baseline — many LLM calls, stock timeouts

Stock settings, written down in `application.yml`:

- LLM call runs on the request thread
- No connect timeout
- 120s read timeout
- No retry, no circuit breaker

The test accepts TCP on port 11434 and never sends a response. Fifty chat calls stay open. Six player lookups must return within 5s.

This command stops the process on port 8080, stops the `ollama` container, runs the stage, and starts `ollama` again when it finishes.

```bash
export JAVA_HOME="/opt/homebrew/opt/openjdk@17"
export PATH="$JAVA_HOME/bin:$PATH"
cd ~/git/player-service-java
python3 scripts/availability_stages.py baseline
```

| | Baseline |
|--|----------|
| Player availability (200 within 5s) | **0%** (0/6) |
| One admitted chat call | still running at **8s** |
| Unreachable host `192.0.2.1` | still running at **6s** |

Player lookups failed because chat calls held the worker pool. H2 was up.

---

## 4. Changes, each retested the same way

### 4.1 Chat runs on its own threads

`async-enabled: true`. Chat returns a `Callable` and runs on `chat-exec-*` (8 threads, no queue). Extra chat calls get **503** `Chat worker pool is full`. Player requests stay on Tomcat threads.

```bash
export JAVA_HOME="/opt/homebrew/opt/openjdk@17"
export PATH="$JAVA_HOME/bin:$PATH"
cd ~/git/player-service-java
python3 scripts/availability_stages.py decouple
```

| | Baseline | After 4.1 |
|--|----------|-----------|
| Player availability | 0% | **100%** (6/6) |
| Admitted chat against a hung read | still open at 8s | still open at 8s |
| Unreachable host | still open at 6s | still open at 6s |

Player availability is restored here. A hung read still occupies a chat worker for the full 120s, and an unreachable host still has no connect timeout. About 86% of the 50 chat calls returned within 2s; those are the ones the pool rejected. That percentage is a chat observation. It is not the availability number.

### 4.2 Connect timeout and read timeout

Connect **2s**. Read stays **120s**.

```bash
export JAVA_HOME="/opt/homebrew/opt/openjdk@17"
export PATH="$JAVA_HOME/bin:$PATH"
cd ~/git/player-service-java
python3 scripts/availability_stages.py timeouts
```

| | After 4.1 | After 4.2 |
|--|-----------|-----------|
| Player availability | 100% | **100%** |
| Hung read (accepts, sends nothing) | still open at 8s | still open at 8s |
| Unreachable host | still open at 6s | **503 in 2.03s** |

The unreachable call returns:

```json
{"error":"Ollama call failed","detail":"Ollama connect timed out after 2000ms"}
```

The hung read is unchanged because the read timeout is still 120s. Connect timeout and read timeout are different waits.

### 4.3 Retry inside one budget, with backoff

Per attempt: connect **500ms**, read **2s**. Up to **2** extra attempts. The whole sequence, including backoff, must finish inside **5s**. Backoff starts at **200ms** and doubles (200ms, then 400ms). An attempt is not started when the time left is shorter than the connect timeout, because a black-hole connect would spend that full connect timeout.

```bash
export JAVA_HOME="/opt/homebrew/opt/openjdk@17"
export PATH="$JAVA_HOME/bin:$PATH"
cd ~/git/player-service-java
python3 scripts/availability_stages.py retry
```

| | After 4.2 | After 4.3 |
|--|-----------|-----------|
| Player availability | 100% | **100%** |
| One admitted call against a hung server | still open at 8s | **503 in 4.24s** |
| Unreachable host | 2.03s | **503 in 2.16s** |

Hung server (the connection succeeds, then nothing comes back). Each attempt uses the read cap:

`2.0s + 200ms + 2.0s = 4.2s` (measured **4.24s**).

About 0.8s is left. The next backoff is 400ms, and the time after that pause would be shorter than the 500ms connect timeout, so the third attempt is not started. Body:

```json
{"error":"Ollama call failed","detail":"Ollama read timed out after 2000ms"}
```

Unreachable host. The connection never completes, so the **read** cap is not the wait. Each attempt stops at the **connect** cap of 500ms:

`500ms + 200ms + 500ms + 400ms + 500ms = 2.1s` (measured **2.16s**).

```json
{"error":"Ollama call failed","detail":"Ollama connect timed out after 500ms"}
```

The earlier measurement of **1.66s** was this same three-attempt connect failure with a flat 50ms gap: `500×3 + 50×2 = 1.60s`. It was never a 2s read timeout that returned early. The 2s value is only the per-attempt read cap, and an unreachable address does not reach it.

### 4.4 Circuit breaker

After **3** failed calls the breaker opens for **15s**. The next call fails inside the process. Retries stay inside one call, so one HTTP request counts as one failure.

```bash
export JAVA_HOME="/opt/homebrew/opt/openjdk@17"
export PATH="$JAVA_HOME/bin:$PATH"
cd ~/git/player-service-java
python3 scripts/availability_stages.py breaker
python3 -c 'import json; print(json.dumps(json.load(open("craft-demo/results/stages/breaker.json"))["breakerFollowup"], indent=2))'
```

| | After 4.3 | After 4.4 |
|--|-----------|-----------|
| Player availability | 100% | **100%** |
| First admitted call (breaker still closed) | 4.24s | **4.25s**, HTTP 503, read timeout |
| Fourth call, after three failures | would pay the budget again | **503 in 0.01s** |

That fourth call returns HTTP **503**:

```json
{"error":"Ollama circuit is open","detail":"no call was sent to Ollama"}
```

While the breaker is open, the chat burst all returns within 2s. Player availability stays 100%.

---

## 5. Impact

Same hung-LLM overload. Six player lookups. 5 second deadline. Availability is the player column.

| Stage | Player availability | What changed for chat |
|-------|---------------------|------------------------|
| Baseline | **0%** (0/6) | Chat holds every Tomcat worker for up to 120s |
| 4.1 Decouple | **100%** (6/6) | Spare chat calls return 503 immediately |
| 4.2 Timeouts | **100%** | Unreachable host returns 503 in **2.03s** |
| 4.3 Retry | **100%** | Hung read returns 503 in **4.24s**, inside the 5s budget |
| 4.4 Breaker | **100%** | The call after the breaker opens returns 503 in **0.01s** |

All five stages in one run (rewrites `craft-demo/results/stages/summary.json`):

```bash
export JAVA_HOME="/opt/homebrew/opt/openjdk@17"
export PATH="$JAVA_HOME/bin:$PATH"
cd ~/git/player-service-java
python3 scripts/availability_stages.py
```

One stage writes `craft-demo/results/stages/<stage>.json` and leaves `summary.json` as the last full run.

---

## 6. Learnings

1. The availability number is player HTTP 200 within 5 seconds. Chat 503s are dependency signals and stay out of that ratio.
2. A 120s call on the request thread fills the worker pool while the database is healthy.
3. Moving chat onto its own pool is what brought player availability from 0% to 100%.
4. Connect timeout and read timeout fail different calls. An unreachable host waits on connect (500ms here). A hung response waits on read (2s here).
5. Retries and backoff have to share one budget. Three full read timeouts would be 6s. This stage stops at 4.24s for a hung read and 2.16s for an unreachable host, both under 5s.
6. After the breaker opens, the response is HTTP 503 `Ollama circuit is open` and no socket is opened.
7. Liveness means the process is up. Readiness means the player database is up. Ollama stays out of readiness so a dead model does not drain player traffic.

---

## Files

| File | Role |
|------|------|
| `PlayerService.java` | Sleep stays. Database exceptions propagate. |
| `PlayerExceptionHandler.java` | Database failure → 500. Chat pool rejection → 503. |
| `OllamaTransport.java` | Separate connect and read timeouts. Retries and backoff stop at `retry-budget-ms`. |
| `ChatAsyncConfig.java` | Bounded `chat-exec` pool when chat is async. |
| `ChatController.java` | Request thread, or `Callable` on the chat pool. Maps chat failures to 503. |
| `ChatCircuitBreaker.java` | Opens after 3 failures. Later calls throw before any socket. |
| `SliRecordingFilter.java` / `SliTracker.java` | Availability is the player ratio. Chat counts are stored beside it. |
| `ServiceInfoContributor.java` | `/actuator/info` stage, availability, liveness, readiness. |
| `application.yml` | Baseline timeouts, Tomcat cap, liveness and readiness groups. |
| `application-decouple.yml` `application-timeouts.yml` `application-retry.yml` `application-breaker.yml` | One stage each. |
| `scripts/availability_stages.py` | Hung peer, player deadline, connect-stall probe. Pass a stage name to run one. |
