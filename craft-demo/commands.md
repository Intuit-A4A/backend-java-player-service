# Commands

Copy-paste for the talk and the night-before rebuild. Slide numbers are [`Player-Service-Availability_v3.pptx`](file:///Users/jidongchai/Downloads/Player-Service-Availability_v3.pptx) (21 slides). Slides 1–10 are pitch only. Live curls start at slide 11. Do not run the ramp or `DROP TABLE` live unless you have rehearsed the restart.

The bar (slide 8): a player call is available when it returns **200**, **400**, or **404** before the client gives up. A client timeout is a miss. Chat **503** is fine.

```bash
export JAVA_HOME="/opt/homebrew/opt/openjdk@17"
export PATH="$JAVA_HOME/bin:$PATH"
cd ~/git/player-service-java
```

---

## Start

Branch app, baseline profile (chat on the Tomcat thread, 120s read):

```bash
mvn -DskipTests package
java -jar target/player-service-java-0.0.1-SNAPSHOT.jar
```

Same jar, `timeouts` profile (async chat, 2s read):

```bash
java -jar target/player-service-java-0.0.1-SNAPSHOT.jar --spring.profiles.active=timeouts
```

Prometheus + Grafana:

```bash
sh craft-demo/observability/up.sh
# http://localhost:3000/d/availability/availability
# http://localhost:3000/d/pagination-compare/pagination-e28094-same-list-load
```

Ollama, when you want a real model instead of the hang peer:

```bash
colima start
docker start ollama
until curl -sf http://127.0.0.1:11434/api/tags >/dev/null; do sleep 2; done
```

Smoke:

```bash
curl -s -o /dev/null -w "list %{http_code}\n" localhost:8080/v1/players
curl -s -o /dev/null -w "by-id %{http_code}\n" localhost:8080/v1/players/aardsda01
curl -si localhost:8080/v1/players/no-such-player | head -n 1
```

---

## Talk order

### Slide 11 — 3.1 observability

8081 is a second Tomcat. Readiness is the database, not Ollama. `client_timeout` is only in the ramp JSON.

```bash
curl -s localhost:8081/actuator/health/liveness | python3 -m json.tool
curl -s localhost:8081/actuator/health/readiness | python3 -m json.tool
curl -s localhost:8081/actuator/prometheus | grep -E 'tomcat_threads_busy_threads|tomcat_threads_config_max_threads'
curl -s localhost:8080/v1/reliability/mode | python3 -m json.tool
curl -s -X POST localhost:8080/v1/reliability/sli/reset >/dev/null
curl -s -o /dev/null localhost:8080/v1/players/aardsda01
curl -s localhost:8080/v1/reliability/sli | python3 -m json.tool
```

### Slide 12 — 3.2, 404 vs 500

Unknown id stays 404:

```bash
curl -si localhost:8080/v1/players/no-such-player | head -n 1
```

Dropped table is 500 on this branch. This destroys in-memory `PLAYERS`. Restart the JVM afterward so the CSV reloads.

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
curl -si localhost:8080/v1/players/aardsda01 | head -n 20
```

### Slides 13–15 — 3.3 pagination

```bash
curl -s 'localhost:8080/v1/players?page=0&size=10' | python3 -c 'import sys,json; d=json.load(sys.stdin); print({k:d[k] for k in ("page","size","totalElements","totalPages")}, "rows", len(d["players"]))'
curl -s -o /dev/null -w "default %{http_code} %{size_download}B %{time_total}s\n" localhost:8080/v1/players
curl -s -o /dev/null -w "size10 %{http_code} %{size_download}B %{time_total}s\n" 'localhost:8080/v1/players?page=0&size=10'
curl -si 'localhost:8080/v1/players?size=101' | head -n 1
```

Slide 14 expects size=10 → **10** rows, `totalElements` **19370**, **4,691** bytes; the default page is **23,332** bytes against a **~9 MB** full roster; `size=101` is **400**.

Slide 15 is the same 30 calls, both jars `-Xmx128m`. Not a live step. Main: **10×500**, **19×200**, **1** incomplete. Branch: **30×200**, **0×5xx**.

```bash
sh scripts/build_demo_main_jar.sh
sh scripts/start_dual_jars.sh
python3 scripts/pagination_load_compare.py
```

### Slide 16 — 3.4 chat

Refused TCP fails fast. The ramp uses a hang peer instead (accepts, never replies).

```bash
docker stop ollama
curl -s -m 5 -w "models %{http_code} in %{time_total}s\n" localhost:8080/v1/chat/list-models
curl -s -o /dev/null -w "player %{http_code}\n" localhost:8080/v1/players/aardsda01
docker start ollama
```

On the `timeouts` profile the same chat call returns **503** in about 2s while the player call stays **200**. Readiness stays **UP** with Ollama down, because readiness is the database only. Skip `docker stop` unless that profile is already the running process.

### Slides 17–18 — proof, read only

Do not run the ramp in the room. Slide 17, same hang peer on **11434**:

| | Baseline | timeouts |
|--|----------|----------|
| `GET /v1/players` | 6×200, 22×client timeout | 28×200 |
| `GET /v1/players/{id}` | 6×200, 22×client timeout | 28×200 |
| Player totals | 12×200, 44×client timeout of 56 | 56×200, 0 client timeouts |
| Chat | client timeout, no HTTP status | 84×503 per route, about 2s |
| Tomcat busy, peak | 40/40 | 2/40 |

---

## Ramp (night before, not live)

Stop the jar first. The script starts its own JVM and a hang peer on **11434**.

```bash
python3 scripts/ramp_load_test.py baseline
python3 scripts/ramp_load_test.py timeouts
python3 scripts/render_ramp_scorecard.py
```

Checked-in result matches slide 17: each player route **6×200 + 22×client_timeout** → **28×200**; player totals **12×200 + 44×client_timeout** of 56 → **56×200**; chat **84×503** per route; Tomcat busy **40/40** → **2/40**.

---

## Rebuild slides and screenshots

```bash
python3 scripts/build_google_slides.py
sh scripts/capture_grafana_screenshots.sh
```

That script writes `craft-demo/Player-Service-Availability.pptx`. The talk deck is the v3 file in Downloads, not that generated pptx.

`sh scripts/demo_capture.sh` rewrites curl evidence and **drops `PLAYERS`**. Restart the app after it.

---

## Optional, if asked (slide 21)

Second JVM. Terminal 1 stays on **8080**. Terminal 2:

```bash
java -jar target/player-service-java-0.0.1-SNAPSHOT.jar \
  --server.port=8082 --management.server.port=8083 --spring.profiles.active=timeouts
curl -s -o /dev/null -w "8080 %{http_code}\n" localhost:8080/v1/players/aardsda01
curl -s -o /dev/null -w "8082 %{http_code}\n" localhost:8082/v1/players/aardsda01
```
