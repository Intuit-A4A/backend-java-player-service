# Player service demo notes

Companion to [`demo.md`](demo.md) — same section numbers; commands and monitoring detail live here.

Run once:

```bash
export JAVA_HOME="/opt/homebrew/opt/openjdk@17"
export PATH="$JAVA_HOME/bin:$PATH"
cd ~/git/player-service-java
```

Terminal 1 stays on the app unless a step says otherwise.

---

## 1. Architecture

One JVM. Player and chat share Tomcat on **8080**. H2 in memory. Ollama on **11434**.

```text
PlayerController  -> PlayerService -> PlayerRepository -> H2
ChatController    -> ChatClientService -> OllamaAPI -> Ollama
```

**Success criterion:** player endpoints return **200 within the client deadline** while chat is stuck on a hang peer (accepts TCP, never replies). Chat **503** is OK; player **client_timeout** is not.

On **`main`** for sections 2.2–2.3:

```bash
git checkout main
git branch --show-current
mvn spring-boot:run
```

Ollama:

```bash
colima start
docker start ollama
until curl -sf http://127.0.0.1:11434/api/tags >/dev/null; do sleep 2; done
curl -s http://127.0.0.1:11434/api/tags | grep -i tinyllama || docker exec ollama ollama pull tinyllama
```

Smoke:

```bash
find src/main/java -name '*.java' | sort
curl -s -o /dev/null -w "players %{http_code}\n" localhost:8080/v1/players
curl -s -o /dev/null -w "player %{http_code}\n" localhost:8080/v1/players/aardsda01
curl -si localhost:8080/v1/players/no-such-player | head -n 1
curl -s -w "\nmodels %{http_code}\n" localhost:8080/v1/chat/list-models
```

---

## 2. Problems

### 2.1 No observability for the system

On **`main`**: no Prometheus/Grafana stack, no wired `/actuator/prometheus`, no in-app SLI, no `/v1/reliability/*`, no liveness/readiness story for player vs chat. You only have logs and ad-hoc curls—even when Tomcat is idle.

If metrics were on **8080**, saturation would blank the scrape (needs a worker). Branch pins max threads **40** to reproduce on a laptop.

(No commands on `main` for metrics—they are not there.)

### 2.2 A database failure is returned as 404

```bash
sed -n '27,39p' src/main/java/com/app/playerservicejava/service/PlayerService.java
sed -n '28,36p' src/main/java/com/app/playerservicejava/controller/PlayerController.java
```

Drop `PLAYERS`, request real id `aardsda01`:

```bash
jsession=$(curl -s http://localhost:8080/h2-console/ | sed -n 's/.*jsessionid=\([a-f0-9]*\).*/\1/p')
curl -s -o /dev/null "http://localhost:8080/h2-console/login.jsp?jsessionid=$jsession"
curl -s -o /dev/null \
  --data-urlencode 'language=en' \
  --data-urlencode 'setting=Generic H2 (Embedded)' \
  --data-urlencode 'name=Generic H2 (Embedded)' \
  --data-urlencode 'driver=org.h2.Driver' \
  --data-urlencode 'url=jdbc:h2:mem:playerdb' \
  --data-urlencode 'user=sa' \
  --data-urlencode 'password=' \
  "http://localhost:8080/h2-console/login.do?jsessionid=$jsession"
curl -s -o /dev/null \
  --data-urlencode 'sql=DROP TABLE PLAYERS' \
  "http://localhost:8080/h2-console/query.do?jsessionid=$jsession"
curl -si localhost:8080/v1/players/aardsda01 | head -n 1
```

Restart app so H2 reloads (`Ctrl-C`, then `mvn spring-boot:run`).

### 2.3 A stuck chat call holds a Tomcat worker

```bash
git show main:src/main/java/com/app/playerservicejava/config/ChatClientConfiguration.java | sed -n '25,28p'
docker stop ollama
curl -s -m 5 -w "refused %{http_code} in %{time_total}s\n" localhost:8080/v1/chat/list-models
docker start ollama
```

Ramp uses a **hang peer** on **11434** (accept, never reply)—see section 3 Test.

---

## 3. Approach, challenges, solutions

Branch and build:

```bash
git checkout craft-demo/availability
git log --oneline main..HEAD
mvn -DskipTests package
```

### Approach

Observable on **8081**, then **baseline** vs **`timeouts`** (async chat + **2s** ollama4j timeout), same ramp.

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
| Saturation | `tomcat_threads_busy_threads` → max **40** |
| Completed work | Per-API `increase(...)` stacked **200 / 503 / 500** |
| SLI | Player successes ÷ player requests (HTTP below 500); chat excluded |
| Ramp JSON | `client_timeout` — not in Grafana |

| Profile | Chat | Ollama timeout | Player under hang |
|---------|------|----------------|-------------------|
| Baseline | Tomcat thread | 120s | `client_timeout` after pool fills |
| Timeouts | 8× `chat-exec`, queue 0 | 2s | **200**; chat **503** |

### Challenges

Same as presentation: blind on `main`; wrong scrape port under saturation; MBean registry off → no busy gauge; Grafana = completed HTTP only; probe design (H2 vs Ollama); one ollama4j timeout knob.

### Solutions

| Area | What we did |
|------|-------------|
| Metrics & probes | `management.server.port: 8081`; liveness = process; readiness = **db** |
| Tomcat visibility | `server.tomcat.mbeanregistry.enabled: true`; max **40** |
| SLI & stage | Filter, tracker, `/v1/reliability/*`, `/actuator/info` |
| Dashboard | Prometheus + Grafana; busy + status counts |
| Correct errors | DB → **500**; missing id → **404** |
| Availability fix | `application-timeouts.yml`: async + **2s** read timeout |

### Monitoring design (detail)

| Port | Serves | Why separate |
|------|--------|--------------|
| 8080 | Player + chat API | Pool the hang fills |
| 8081 | health, info, prometheus, metrics | Scrapes without an 8080 worker |

**MBean registry:** `server.tomcat.mbeanregistry.enabled: true` registers Tomcat’s thread-pool JMX beans so Micrometer exports `tomcat_threads_busy_threads` and `tomcat_threads_config_max_threads`. Without it the top Grafana panel is empty when the pool is full.

**HTTP metrics:** `http_server_requests_seconds_count` increments only when the response completes. Client timeouts while workers are stuck do not appear.

#### Methods

- **`SliRecordingFilter`** — `shouldNotFilter` skips non-player/chat paths; `doFilterInternal` → `recordPlayers` / `recordChat` (success = status below 500).
- **`SliTracker`** — `recordPlayers`, `recordChat`, `snapshot`, `reset`.
- **`ReliabilityController`** — `mode`, `sli`, `reset`.
- **`ServiceInfoContributor.contribute`** — `/actuator/info` service block.

| Probe | Includes | Excludes |
|-------|----------|----------|
| Liveness | `livenessState` | DB, Ollama, pool fullness |
| Readiness | `readinessState`, `db` | Ollama |

#### Dashboard

http://localhost:3000/d/availability/availability

| Panel | Read |
|-------|------|
| Tomcat busy vs max | Busy **40** = saturation |
| Per-API completed counts | Stacked 200/503/500; no bar = not finished yet |

#### Ramp outcomes

| `outcome` | Meaning |
|-----------|---------|
| `http_200` / `http_503` / `http_500` | App returned status |
| `client_timeout` | Load script gave up |
| `no_http_response` | Other client failure |

### Key files (what changed)

**Monitoring & reliability**

| File | Role |
|------|------|
| `src/main/resources/application.yml` | 8080/8081, Tomcat 40, MBean registry, health groups |
| `src/main/java/.../reliability/SliRecordingFilter.java` | Finished player/chat calls |
| `src/main/java/.../reliability/SliTracker.java` | Player availability ratio |
| `src/main/java/.../reliability/ReliabilityController.java` | mode / sli / reset |
| `src/main/java/.../reliability/ServiceInfoContributor.java` | `/actuator/info` |
| `craft-demo/observability/prometheus.yml` | Scrape **8081** |
| `craft-demo/observability/up.sh` | Start stack |
| `craft-demo/observability/grafana/dashboards/availability.json` | Panels |
| `scripts/ramp_load_test.py` | Ramp + JSON |

**Player correctness**

| File | Role |
|------|------|
| `src/main/java/.../service/PlayerService.java` | Propagate DB errors |
| `src/main/java/.../controller/PlayerExceptionHandler.java` | **500** on `DataAccessException` |

**Chat / availability**

| File | Role |
|------|------|
| `src/main/java/.../chat/ChatResilienceProperties.java` | `app.chat.*` |
| `src/main/java/.../config/ReliabilityConfiguration.java` | Binds properties |
| `src/main/java/.../chat/ChatAsyncConfig.java` | `chat-exec` pool |
| `src/main/java/.../controller/chat/ChatController.java` | Async `Callable`; 503 paths |
| `src/main/java/.../config/ChatClientConfiguration.java` | ollama4j timeout |
| `src/main/resources/application-timeouts.yml` | Profile |

Walk code:

```bash
sed -n '26,39p' src/main/java/com/app/playerservicejava/service/PlayerService.java
sed -n '19,26p' src/main/java/com/app/playerservicejava/controller/PlayerExceptionHandler.java
mvn -Dtest=PlayerErrorStatusTest test
sed -n '50,56p' src/main/java/com/app/playerservicejava/controller/chat/ChatController.java
sed -n '20,36p' src/main/java/com/app/playerservicejava/chat/ChatAsyncConfig.java
sed -n '11,20p' src/main/java/com/app/playerservicejava/config/ChatClientConfiguration.java
cat src/main/resources/application-timeouts.yml
```

### Stack and probes

```bash
sh craft-demo/observability/up.sh
java -jar target/player-service-java-0.0.1-SNAPSHOT.jar --spring.profiles.active=timeouts
```

```bash
curl -s localhost:8081/actuator/health/liveness | python3 -m json.tool
curl -s localhost:8081/actuator/health/readiness | python3 -m json.tool
curl -s localhost:8081/actuator/info | python3 -m json.tool
curl -s localhost:8081/actuator/prometheus | grep -E 'tomcat_threads_busy|tomcat_threads_config_max'
curl -s localhost:8080/v1/reliability/mode | python3 -m json.tool
curl -s -X POST localhost:8080/v1/reliability/sli/reset >/dev/null
curl -s -o /dev/null localhost:8080/v1/players/aardsda01
curl -s localhost:8080/v1/reliability/sli | python3 -m json.tool
```

Stop the jar before ramp (script starts its own JVM).

### Test

```bash
python3 scripts/ramp_load_test.py baseline
python3 scripts/ramp_load_test.py timeouts
```

| Signal | Baseline | Timeouts |
|--------|----------|----------|
| Peak Tomcat busy | **40** | **~2** |
| Player calls | early **200**, then **client_timeout** | **28/28** **200** |
| Chat calls | **client_timeout** | **503** |

Grafana: last **15 minutes**. Screenshot → `craft-demo/results/dashboard/grafana-ramp-raw.png`, then:

```bash
python3 scripts/annotate_ramp_screenshot.py
```

Also: `craft-demo/results/dashboard/ramp-comparison.md`, `ramp-*.json`.

---

## 4. Impact

Same bullets as `demo.md` §4: observability during failure; player **200** under hung model on one JVM; DB **500** and readiness **UP** when Ollama is down. Fleet effects → section 6.

---

## 5. Learnings

Match `demo.md` §5 (player API SLO, observability as part of the fix, busy vs completed vs ramp outcomes, decouple + timeout, probes/replicas/deployments).

---

## 6. Beyond this process

One JVM; probes do not raise availability by themselves.

**Liveness** — process up, not “chat stuck.” **Readiness** — **H2** only; Ollama out so model outage does not drain player traffic. Needs another replica to matter.

| Change | What it improves |
|--------|------------------|
| Readiness is H2, not Ollama | Dead model does not remove player traffic from this instance |
| Second JVM | One process can fail while the other serves players |
| Graceful shutdown | In-flight player calls can finish on deploy/SIGTERM |
| Player and chat as two deployments | Chat load cannot saturate the player process |
| Durable database | Restart does not imply losing the only data copy |

Readiness demo:

```bash
java -jar target/player-service-java-0.0.1-SNAPSHOT.jar --spring.profiles.active=timeouts
docker stop ollama
curl -s localhost:8081/actuator/health/readiness | python3 -m json.tool
curl -s -m 5 -o /dev/null -w "models %{http_code}\n" localhost:8080/v1/chat/list-models
curl -s -o /dev/null -w "player %{http_code}\n" localhost:8080/v1/players/aardsda01
docker start ollama
```

### Graceful shutdown

1. Not ready → LB stops **new** requests.
2. **SIGTERM** (K8s `terminationGracePeriodSeconds`).
3. **`server.shutdown=graceful`** — Tomcat finishes active requests.
4. **`spring.lifecycle.timeout-per-shutdown-phase`** — cap wait (stuck chat on baseline can block).

Not on branch yet; optional `application.yml`:

```yaml
server:
  shutdown: graceful
spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s
```

K8s: `terminationGracePeriodSeconds` ≥ phase; optional **preStop** delay.

```bash
curl -s -o /dev/null -w "player %{http_code}\n" localhost:8080/v1/players/aardsda01 &
sleep 0.5
lsof -tiTCP:8080 -sTCP:LISTEN | xargs kill -TERM
wait
```

### Second JVM

Terminal 1: **8080** / management **8081**. Terminal 2:

```bash
java -jar target/player-service-java-0.0.1-SNAPSHOT.jar --server.port=8082 --management.server.port=8083 --spring.profiles.active=timeouts
curl -s -o /dev/null -w "8080 %{http_code}\n" localhost:8080/v1/players/aardsda01
curl -s -o /dev/null -w "8082 %{http_code}\n" localhost:8082/v1/players/aardsda01
lsof -tiTCP:8080 -sTCP:LISTEN | xargs kill
curl -s -m 5 -o /dev/null -w "8080 after stop %{http_code}\n" localhost:8080/v1/players/aardsda01
curl -s -o /dev/null -w "8082 %{http_code}\n" localhost:8082/v1/players/aardsda01
```
